"""
Session Manager - 会话管理器

基于 GSD-2 的 AutoSession 设计模式实现
管理 Agent 会话的所有可变状态，提供一键重置和持久化能力
"""
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json
import asyncio
import random
from pathlib import Path


class SessionStatus(str, Enum):
    """会话状态"""
    IDLE = "idle"           # 空闲
    ACTIVE = "active"       # 活跃
    PAUSED = "paused"       # 暂停
    ERROR = "error"         # 错误
    COMPLETED = "completed" # 完成


@dataclass
class CurrentUnit:
    """当前执行单元"""
    unit_type: str          # 单元类型 (task, slice, milestone)
    unit_id: str           # 单元ID
    started_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DispatchRecord:
    """分发记录"""
    unit_id: str
    dispatch_count: int = 0
    lifetime_dispatches: int = 0
    recovery_count: int = 0
    last_dispatch_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "dispatch_count": self.dispatch_count,
            "lifetime_dispatches": self.lifetime_dispatches,
            "recovery_count": self.recovery_count,
            "last_dispatch_at": self.last_dispatch_at.isoformat() if self.last_dispatch_at else None
        }


@dataclass
class TimerRecord:
    """计时器记录"""
    timer_type: str
    started_at: datetime
    duration_ms: int
    callback: Optional[str] = None


class SessionManager:
    """
    会话管理器
    
    封装所有可变会话状态到单个实例中，替代分散的模块级变量
    
    设计原则（来自 GSD-2 AutoSession）：
    1. 所有可变状态必须在类属性中声明
    2. reset() 方法一键清除所有状态
    3. to_dict() 提供诊断快照
    4. 支持持久化和恢复
    
    Attributes:
        status: 当前会话状态
        current_unit: 当前执行的单元
        dispatch_records: 分发记录映射
        execution_history: 执行历史
        active_timers: 活跃计时器
        metadata: 元数据存储
    """
    
    # 类常量
    MAX_DISPATCH_ATTEMPTS = 3
    MAX_LIFETIME_DISPATCHES = 6
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        persistent: bool = False,
        storage_path: Optional[str] = None
    ):
        """
        初始化会话管理器
        
        Args:
            session_id: 会话ID（自动生成如果不提供）
            persistent: 是否启用持久化
            storage_path: 持久化存储路径
        """
        self.session_id = session_id or self._generate_session_id()
        self.persistent = persistent
        self.storage_path = Path(storage_path) if storage_path else Path(".agent/sessions")
        
        # 初始化所有状态属性
        self._init_state()
        
        # 如果启用持久化，尝试恢复
        if persistent:
            self._restore_if_exists()
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = random.randint(1000, 9999)
        return f"session_{timestamp}_{random_suffix}"
    
    # ─── 状态管理 ─────────────────────────────────────────────────────────
    
    def _init_state(self):
        """初始化所有状态属性（必须在 reset 中同步更新）"""
        # 生命周期状态
        self.status: SessionStatus = SessionStatus.IDLE
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        
        # 当前单元
        self.current_unit: Optional[CurrentUnit] = None
        
        # 分发记录
        self.dispatch_records: Dict[str, DispatchRecord] = {}
        
        # 执行历史
        self.execution_history: List[Dict[str, Any]] = []
        
        # 计时器管理
        self._active_timers: Dict[str, asyncio.Task] = {}
        self._timer_records: Dict[str, TimerRecord] = {}
        
        # 错误追踪
        self.last_error: Optional[str] = None
        self.error_count: int = 0
        
        # 元数据存储（扩展用）
        self.metadata: Dict[str, Any] = {}
        
        # 检查点
        self.checkpoints: Dict[str, Dict[str, Any]] = {}
    
    def reset(self):
        """
        重置所有状态
        
        一键清除所有可变状态，回到初始状态
        """
        # 取消所有活跃计时器
        self.clear_all_timers()
        
        # 重新初始化状态
        self._init_state()
        
        # 更新持久化
        if self.persistent:
            self._persist()
    
    def start(self, unit_type: str, unit_id: str, **metadata) -> CurrentUnit:
        """
        开始新的执行单元
        
        Args:
            unit_type: 单元类型
            unit_id: 单元ID
            **metadata: 额外元数据
        
        Returns:
            CurrentUnit: 创建的当前单元
        """
        self.status = SessionStatus.ACTIVE
        self.current_unit = CurrentUnit(
            unit_type=unit_type,
            unit_id=unit_id,
            metadata=metadata
        )
        self.updated_at = datetime.now()
        
        # 记录分发
        self._record_dispatch(unit_id)
        
        # 持久化
        if self.persistent:
            self._persist()
        
        return self.current_unit
    
    def complete(self, result: Dict[str, Any] = None):
        """
        完成当前单元
        
        Args:
            result: 执行结果
        """
        if self.current_unit:
            record = {
                "unit_type": self.current_unit.unit_type,
                "unit_id": self.current_unit.unit_id,
                "started_at": self.current_unit.started_at.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "result": result or {}
            }
            self.execution_history.append(record)
        
        self.current_unit = None
        self.status = SessionStatus.IDLE
        self.updated_at = datetime.now()
        
        if self.persistent:
            self._persist()
    
    def pause(self):
        """暂停会话"""
        self.status = SessionStatus.PAUSED
        self.updated_at = datetime.now()
        
        if self.persistent:
            self._persist()
    
    def resume(self):
        """恢复会话"""
        self.status = SessionStatus.ACTIVE
        self.updated_at = datetime.now()
        
        if self.persistent:
            self._persist()
    
    def fail(self, error: str):
        """
        标记会话失败
        
        Args:
            error: 错误信息
        """
        self.status = SessionStatus.ERROR
        self.last_error = error
        self.error_count += 1
        self.updated_at = datetime.now()
        
        if self.persistent:
            self._persist()
    
    # ─── 分发记录管理 ─────────────────────────────────────────────────────
    
    def _record_dispatch(self, unit_id: str):
        """记录分发"""
        if unit_id not in self.dispatch_records:
            self.dispatch_records[unit_id] = DispatchRecord(unit_id=unit_id)
        
        record = self.dispatch_records[unit_id]
        record.dispatch_count += 1
        record.lifetime_dispatches += 1
        record.last_dispatch_at = datetime.now()
    
    def get_dispatch_count(self, unit_id: str) -> int:
        """获取单元的分发次数"""
        record = self.dispatch_records.get(unit_id)
        return record.dispatch_count if record else 0
    
    def should_retry(self, unit_id: str) -> bool:
        """
        检查是否应该重试单元
        
        基于分发次数和最大尝试次数判断
        """
        count = self.get_dispatch_count(unit_id)
        return count < self.MAX_DISPATCH_ATTEMPTS
    
    def record_recovery(self, unit_id: str):
        """记录恢复次数"""
        if unit_id not in self.dispatch_records:
            self.dispatch_records[unit_id] = DispatchRecord(unit_id=unit_id)
        
        self.dispatch_records[unit_id].recovery_count += 1
    
    # ─── 计时器管理 ───────────────────────────────────────────────────────
    
    async def start_timer(
        self,
        timer_id: str,
        duration_ms: int,
        callback: Optional[Callable] = None
    ):
        """
        启动计时器
        
        Args:
            timer_id: 计时器ID
            duration_ms: 持续时间（毫秒）
            callback: 超时回调函数
        """
        # 取消已存在的同名计时器
        if timer_id in self._active_timers:
            self._active_timers[timer_id].cancel()
        
        # 记录计时器
        self._timer_records[timer_id] = TimerRecord(
            timer_type=timer_id,
            started_at=datetime.now(),
            duration_ms=duration_ms,
            callback=callback.__name__ if callback else None
        )
        
        # 创建异步任务
        async def timer_task():
            try:
                await asyncio.sleep(duration_ms / 1000)
                if callback:
                    await callback()
            except asyncio.CancelledError:
                pass  # 正常取消
        
        self._active_timers[timer_id] = asyncio.create_task(timer_task())
    
    def cancel_timer(self, timer_id: str):
        """取消计时器"""
        if timer_id in self._active_timers:
            self._active_timers[timer_id].cancel()
            del self._active_timers[timer_id]
            if timer_id in self._timer_records:
                del self._timer_records[timer_id]
    
    def clear_all_timers(self):
        """清除所有计时器"""
        for task in self._active_timers.values():
            task.cancel()
        self._active_timers.clear()
        self._timer_records.clear()
    
    def get_active_timers(self) -> List[str]:
        """获取所有活跃计时器ID"""
        return list(self._active_timers.keys())
    
    # ─── 检查点管理 ───────────────────────────────────────────────────────
    
    def save_checkpoint(self, checkpoint_id: str, data: Dict[str, Any]):
        """
        保存检查点
        
        Args:
            checkpoint_id: 检查点ID
            data: 检查点数据
        """
        self.checkpoints[checkpoint_id] = {
            "data": data,
            "saved_at": datetime.now().isoformat(),
            "unit_id": self.current_unit.unit_id if self.current_unit else None
        }
        
        if self.persistent:
            self._persist()
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        加载检查点
        
        Args:
            checkpoint_id: 检查点ID
        
        Returns:
            检查点数据或 None
        """
        checkpoint = self.checkpoints.get(checkpoint_id)
        return checkpoint["data"] if checkpoint else None
    
    def list_checkpoints(self) -> List[str]:
        """列出所有检查点ID"""
        return list(self.checkpoints.keys())
    
    def delete_checkpoint(self, checkpoint_id: str):
        """删除检查点"""
        if checkpoint_id in self.checkpoints:
            del self.checkpoints[checkpoint_id]
            
            if self.persistent:
                self._persist()
    
    # ─── 序列化和持久化 ───────────────────────────────────────────────────
    
    def to_dict(self) -> Dict[str, Any]:
        """
        导出为字典（诊断快照）
        
        Returns:
            会话状态字典
        """
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "current_unit": {
                "unit_type": self.current_unit.unit_type,
                "unit_id": self.current_unit.unit_id,
                "started_at": self.current_unit.started_at.isoformat(),
                "metadata": self.current_unit.metadata
            } if self.current_unit else None,
            "dispatch_records": {
                k: v.to_dict() for k, v in self.dispatch_records.items()
            },
            "execution_history": self.execution_history,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "active_timers": list(self._active_timers.keys()),
            "checkpoints": self.checkpoints,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionManager":
        """
        从字典恢复会话
        
        Args:
            data: 会话状态字典
        
        Returns:
            SessionManager 实例
        """
        session = cls(
            session_id=data.get("session_id"),
            persistent=False  # 恢复时不立即持久化
        )
        
        # 恢复状态
        session.status = SessionStatus(data.get("status", "idle"))
        
        # 恢复当前单元
        if data.get("current_unit"):
            unit_data = data["current_unit"]
            session.current_unit = CurrentUnit(
                unit_type=unit_data["unit_type"],
                unit_id=unit_data["unit_id"],
                started_at=datetime.fromisoformat(unit_data["started_at"]),
                metadata=unit_data.get("metadata", {})
            )
        
        # 恢复分发记录
        for k, v in data.get("dispatch_records", {}).items():
            session.dispatch_records[k] = DispatchRecord(
                unit_id=v["unit_id"],
                dispatch_count=v.get("dispatch_count", 0),
                lifetime_dispatches=v.get("lifetime_dispatches", 0),
                recovery_count=v.get("recovery_count", 0),
                last_dispatch_at=datetime.fromisoformat(v["last_dispatch_at"]) if v.get("last_dispatch_at") else None
            )
        
        # 恢复执行历史
        session.execution_history = data.get("execution_history", [])
        
        # 恢复错误信息
        session.error_count = data.get("error_count", 0)
        session.last_error = data.get("last_error")
        
        # 恢复检查点
        session.checkpoints = data.get("checkpoints", {})
        
        # 恢复元数据
        session.metadata = data.get("metadata", {})
        
        # 恢复时间戳
        if data.get("created_at"):
            session.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            session.updated_at = datetime.fromisoformat(data["updated_at"])
        
        return session
    
    def _persist(self):
        """持久化到磁盘"""
        if not self.persistent:
            return
        
        # 确保目录存在
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 保存到文件
        file_path = self.storage_path / f"{self.session_id}.json"
        
        # 构建可序列化的数据
        data = self.to_dict()
        
        try:
            # 原子写入：先写临时文件，再重命名
            tmp_path = file_path.with_suffix('.tmp')
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 重命名到目标文件
            tmp_path.replace(file_path)
        except Exception as e:
            # 清理临时文件
            tmp_path = file_path.with_suffix('.tmp')
            if tmp_path.exists():
                tmp_path.unlink()
            raise e
    
    def _restore_if_exists(self):
        """从磁盘恢复会话"""
        if not self.storage_path.exists():
            return
        
        file_path = self.storage_path / f"{self.session_id}.json"
        if not file_path.exists():
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            restored = SessionManager.from_dict(data)
            
            # 复制所有状态
            self.status = restored.status
            self.current_unit = restored.current_unit
            self.dispatch_records = restored.dispatch_records
            self.execution_history = restored.execution_history
            self.error_count = restored.error_count
            self.last_error = restored.last_error
            self.checkpoints = restored.checkpoints
            self.metadata = restored.metadata
            self.created_at = restored.created_at
            self.updated_at = restored.updated_at
            
        except Exception:
            # 恢复失败，忽略
            pass
    
    def list_sessions(self) -> List[str]:
        """列出所有持久化的会话"""
        if not self.storage_path.exists():
            return []
        
        return [
            f.stem for f in self.storage_path.glob("*.json")
        ]
    
    @classmethod
    def load_session(cls, session_id: str, storage_path: Optional[str] = None) -> Optional["SessionManager"]:
        """
        加载指定会话
        
        Args:
            session_id: 会话ID
            storage_path: 存储路径
        
        Returns:
            SessionManager 实例或 None
        """
        path = Path(storage_path) if storage_path else Path(".agent/sessions")
        file_path = path / f"{session_id}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception:
            return None
    
    def delete_session(self):
        """删除当前会话"""
        self.clear_all_timers()
        
        if self.storage_path.exists():
            file_path = self.storage_path / f"{self.session_id}.json"
            if file_path.exists():
                file_path.unlink()
        
        self.reset()
    
    # ─── 统计和诊断 ───────────────────────────────────────────────────────
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取会话统计信息
        
        Returns:
            统计信息字典
        """
        total_units = len(self.dispatch_records)
        total_dispatches = sum(r.dispatch_count for r in self.dispatch_records.values())
        total_recoveries = sum(r.recovery_count for r in self.dispatch_records.values())
        
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "total_units": total_units,
            "total_dispatches": total_dispatches,
            "total_recoveries": total_recoveries,
            "total_executions": len(self.execution_history),
            "error_count": self.error_count,
            "active_timers": len(self._active_timers),
            "checkpoints": len(self.checkpoints),
            "has_current_unit": self.current_unit is not None
        }
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        获取执行摘要
        
        Returns:
            执行摘要字典
        """
        if not self.execution_history:
            return {"message": "暂无执行历史"}
        
        # 按类型分组统计
        by_type: Dict[str, List] = {}
        for record in self.execution_history:
            unit_type = record.get("unit_type", "unknown")
            by_type.setdefault(unit_type, []).append(record)
        
        summary = {
            "total_executions": len(self.execution_history),
            "by_type": {
                ut: len(records) for ut, records in by_type.items()
            }
        }
        
        return summary
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"SessionManager(id={self.session_id}, "
            f"status={self.status.value}, "
            f"units={len(self.dispatch_records)}, "
            f"executions={len(self.execution_history)})"
        )
