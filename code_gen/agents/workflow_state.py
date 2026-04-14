"""
Workflow State Manager - 工作流状态管理器

基于 GSD-2 的状态持久化设计，支持：
1. 原子写入（防止状态损坏）
2. 检查点管理（Checkpointing）
3. 状态恢复和重试
4. 并发安全（文件锁）
5. 状态压缩和清理
"""
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
from enum import Enum
import json
import hashlib
import asyncio
from contextlib import contextmanager

# 导入原子写入工具
from .utils import atomic_write_json, file_lock_context


class StepStatus(str, Enum):
    """步骤状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class WorkflowStatus(str, Enum):
    """工作流状态枚举"""
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass
class StepState:
    """步骤执行状态"""
    step_id: str
    name: str
    status: str = "pending"
    agent_role: str = ""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    output: str = ""
    error: str = ""
    retry_count: int = 0
    checkpoint_data: Optional[Dict[str, Any]] = None  # 检查点数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "StepState":
        return cls(**data)
    
    @property
    def duration(self) -> Optional[float]:
        """计算执行时长（秒）"""
        if self.start_time and self.end_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            return (end - start).total_seconds()
        return None
    
    def is_terminal(self) -> bool:
        """检查是否为终止状态"""
        return self.status in [StepStatus.COMPLETED.value, StepStatus.FAILED.value, StepStatus.SKIPPED.value]


@dataclass
class Checkpoint:
    """检查点"""
    checkpoint_id: str
    step_id: str
    data: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Checkpoint":
        return cls(**data)


@dataclass
class WorkflowMetrics:
    """工作流指标"""
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    total_duration: float = 0.0
    retry_count: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @property
    def completion_rate(self) -> float:
        """完成率"""
        if self.total_steps == 0:
            return 0.0
        return self.completed_steps / self.total_steps
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        completed = self.completed_steps
        failed = self.failed_steps
        total = completed + failed
        if total == 0:
            return 0.0
        return completed / total


@dataclass
class WorkflowState:
    """
    工作流状态
    
    增强版状态管理，支持检查点和恢复
    """
    workflow_name: str
    workflow_id: str = field(default_factory=lambda: hashlib.md5(
        datetime.now().isoformat().encode()
    ).hexdigest()[:8])
    goal: str = ""
    status: str = WorkflowStatus.PENDING.value
    current_step_id: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    skipped_steps: List[str] = field(default_factory=list)
    step_states: Dict[str, StepState] = field(default_factory=dict)
    checkpoints: Dict[str, Checkpoint] = field(default_factory=dict)
    plan: Optional[Dict] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: WorkflowMetrics = field(default_factory=WorkflowMetrics)
    version: int = 1  # 状态版本，用于迁移
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "workflow_name": self.workflow_name,
            "workflow_id": self.workflow_id,
            "goal": self.goal,
            "status": self.status,
            "current_step_id": self.current_step_id,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "step_states": {k: v.to_dict() for k, v in self.step_states.items()},
            "checkpoints": {k: v.to_dict() for k, v in self.checkpoints.items()},
            "plan": self.plan,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "metadata": self.metadata,
            "metrics": self.metrics.to_dict(),
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "WorkflowState":
        """从字典恢复"""
        state = cls(
            workflow_name=data["workflow_name"],
            workflow_id=data.get("workflow_id", ""),
            goal=data.get("goal", ""),
            status=data.get("status", WorkflowStatus.PENDING.value),
            current_step_id=data.get("current_step_id"),
            completed_steps=data.get("completed_steps", []),
            failed_steps=data.get("failed_steps", []),
            skipped_steps=data.get("skipped_steps", []),
            plan=data.get("plan"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            metadata=data.get("metadata", {}),
            version=data.get("version", 1)
        )
        
        # 恢复步骤状态
        state.step_states = {
            k: StepState.from_dict(v)
            for k, v in data.get("step_states", {}).items()
        }
        
        # 恢复检查点
        state.checkpoints = {
            k: Checkpoint.from_dict(v)
            for k, v in data.get("checkpoints", {}).items()
        }
        
        # 恢复指标
        if "metrics" in data:
            state.metrics = WorkflowMetrics(**data["metrics"])
        
        return state
    
    def get_pending_steps(self) -> List[str]:
        """获取待执行的步骤"""
        all_steps = list(self.step_states.keys())
        pending = []
        for step_id in all_steps:
            step = self.step_states.get(step_id)
            if step and step.status in [
                StepStatus.PENDING.value,
                StepStatus.FAILED.value,
                StepStatus.RETRYING.value
            ]:
                if step_id not in self.completed_steps:
                    pending.append(step_id)
        return pending
    
    def can_retry(self, step_id: str, max_retries: int = 3) -> bool:
        """检查步骤是否可以重试"""
        step = self.step_states.get(step_id)
        if not step:
            return False
        return step.status == StepStatus.FAILED.value and step.retry_count < max_retries
    
    def save_checkpoint(self, checkpoint_id: str, step_id: str, data: Dict[str, Any], description: str = ""):
        """保存检查点"""
        self.checkpoints[checkpoint_id] = Checkpoint(
            checkpoint_id=checkpoint_id,
            step_id=step_id,
            data=data,
            description=description
        )
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """加载检查点"""
        return self.checkpoints.get(checkpoint_id)
    
    def update_metrics(self):
        """更新指标"""
        self.metrics.total_steps = len(self.step_states)
        self.metrics.completed_steps = len(self.completed_steps)
        self.metrics.failed_steps = len(self.failed_steps)
        self.metrics.skipped_steps = len(self.skipped_steps)


class WorkflowStateManager:
    """
    工作流状态管理器（增强版）
    
    基于 GSD-2 设计，支持原子写入和并发安全
    """
    
    def __init__(
        self,
        work_dir: Path,
        enable_atomic_write: bool = True,
        enable_file_lock: bool = True,
        max_checkpoints: int = 10
    ):
        self.work_dir = Path(work_dir)
        self.state_dir = self.work_dir / ".workflow_states"
        self.checkpoint_dir = self.state_dir / "checkpoints"
        self.state_dir.mkdir(exist_ok=True)
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        self.enable_atomic_write = enable_atomic_write
        self.enable_file_lock = enable_file_lock
        self.max_checkpoints = max_checkpoints
    
    def _get_state_file(self, workflow_name: str) -> Path:
        """获取状态文件路径"""
        name_hash = hashlib.md5(workflow_name.encode()).hexdigest()[:8]
        return self.state_dir / f"{workflow_name}_{name_hash}.json"
    
    def _get_lock_file(self, workflow_name: str) -> Path:
        """获取锁文件路径"""
        return self.state_dir / f"{workflow_name}.lock"
    
    def _get_checkpoint_file(self, workflow_name: str, checkpoint_id: str) -> Path:
        """获取检查点文件路径"""
        return self.checkpoint_dir / f"{workflow_name}_{checkpoint_id}.json"
    
    def save_state(
        self,
        state: WorkflowState,
        create_checkpoint: bool = False,
        checkpoint_description: str = ""
    ):
        """
        保存工作流状态
        
        Args:
            state: 工作流状态
            create_checkpoint: 是否创建检查点
            checkpoint_description: 检查点描述
        """
        state_file = self._get_state_file(state.workflow_name)
        state.end_time = datetime.now().isoformat()
        state.update_metrics()
        
        # 使用文件锁（如启用）
        if self.enable_file_lock:
            lock_file = self._get_lock_file(state.workflow_name)
            with file_lock_context(str(lock_file), timeout=10.0):
                self._do_save_state(state, state_file)
        else:
            self._do_save_state(state, state_file)
        
        # 创建检查点（如需要）
        if create_checkpoint:
            self._save_checkpoint(state, checkpoint_description)
        
        print(f"💾 工作流状态已保存: {state_file}")
    
    def _do_save_state(self, state: WorkflowState, state_file: Path):
        """执行实际的状态保存"""
        data = state.to_dict()
        
        if self.enable_atomic_write:
            # 使用原子写入
            atomic_write_json(str(state_file), data)
        else:
            # 普通写入
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _save_checkpoint(self, state: WorkflowState, description: str = ""):
        """保存检查点到单独文件"""
        checkpoint_id = f"cp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        checkpoint_file = self._get_checkpoint_file(state.workflow_name, checkpoint_id)
        
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "workflow_name": state.workflow_name,
            "workflow_id": state.workflow_id,
            "status": state.status,
            "current_step_id": state.current_step_id,
            "completed_steps": state.completed_steps,
            "created_at": datetime.now().isoformat(),
            "description": description,
            "full_state": state.to_dict()
        }
        
        if self.enable_atomic_write:
            atomic_write_json(str(checkpoint_file), checkpoint_data)
        else:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        
        # 清理旧检查点
        self._cleanup_old_checkpoints(state.workflow_name)
        
        print(f"📍 检查点已创建: {checkpoint_id}")
    
    def _cleanup_old_checkpoints(self, workflow_name: str):
        """清理旧检查点，只保留最近的"""
        pattern = f"{workflow_name}_cp_*.json"
        checkpoints = sorted(
            self.checkpoint_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # 删除多余的检查点
        for checkpoint_file in checkpoints[self.max_checkpoints:]:
            try:
                checkpoint_file.unlink()
                print(f"🗑️ 旧检查点已清理: {checkpoint_file.name}")
            except:
                pass
    
    def load_state(self, workflow_name: str) -> Optional[WorkflowState]:
        """加载工作流状态"""
        state_file = self._get_state_file(workflow_name)
        
        if not state_file.exists():
            return None
        
        try:
            if self.enable_file_lock:
                lock_file = self._get_lock_file(workflow_name)
                with file_lock_context(str(lock_file), timeout=10.0):
                    return self._do_load_state(state_file)
            else:
                return self._do_load_state(state_file)
        except Exception as e:
            print(f"⚠️ 加载状态失败: {e}")
            return None
    
    def _do_load_state(self, state_file: Path) -> Optional[WorkflowState]:
        """执行实际的状态加载"""
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return WorkflowState.from_dict(data)
    
    def restore_from_checkpoint(
        self,
        workflow_name: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[WorkflowState]:
        """
        从检查点恢复
        
        Args:
            workflow_name: 工作流名称
            checkpoint_id: 检查点ID（None则使用最新的）
        
        Returns:
            恢复的工作流状态
        """
        if checkpoint_id:
            checkpoint_file = self._get_checkpoint_file(workflow_name, checkpoint_id)
            if not checkpoint_file.exists():
                print(f"⚠️ 检查点不存在: {checkpoint_id}")
                return None
        else:
            # 找到最新的检查点
            pattern = f"{workflow_name}_cp_*.json"
            checkpoints = sorted(
                self.checkpoint_dir.glob(pattern),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if not checkpoints:
                print("⚠️ 没有找到检查点")
                return None
            checkpoint_file = checkpoints[0]
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            # 恢复完整状态
            state = WorkflowState.from_dict(checkpoint_data["full_state"])
            state.status = WorkflowStatus.RECOVERING.value
            
            print(f"✅ 已从检查点恢复: {checkpoint_data.get('checkpoint_id', 'unknown')}")
            return state
            
        except Exception as e:
            print(f"⚠️ 恢复检查点失败: {e}")
            return None
    
    def has_existing_state(self, workflow_name: str) -> bool:
        """检查是否存在现有状态"""
        state_file = self._get_state_file(workflow_name)
        return state_file.exists()
    
    def delete_state(self, workflow_name: str):
        """删除工作流状态"""
        state_file = self._get_state_file(workflow_name)
        if state_file.exists():
            state_file.unlink()
            print(f"🗑️ 工作流状态已删除: {state_file}")
        
        # 同时删除相关检查点
        pattern = f"{workflow_name}_cp_*.json"
        for checkpoint_file in self.checkpoint_dir.glob(pattern):
            try:
                checkpoint_file.unlink()
            except:
                pass
    
    def list_saved_states(self) -> List[Dict]:
        """列出所有保存的状态"""
        states = []
        for state_file in self.state_dir.glob("*.json"):
            if state_file.parent != self.checkpoint_dir:  # 排除检查点
                try:
                    with open(state_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    states.append({
                        "workflow_name": data.get("workflow_name"),
                        "workflow_id": data.get("workflow_id", ""),
                        "status": data.get("status"),
                        "start_time": data.get("start_time"),
                        "metrics": data.get("metrics", {}),
                        "file": str(state_file)
                    })
                except:
                    pass
        return states
    
    def list_checkpoints(self, workflow_name: str) -> List[Dict]:
        """列出工作流的所有检查点"""
        checkpoints = []
        pattern = f"{workflow_name}_cp_*.json"
        for checkpoint_file in sorted(
            self.checkpoint_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        ):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                checkpoints.append({
                    "checkpoint_id": data.get("checkpoint_id"),
                    "created_at": data.get("created_at"),
                    "description": data.get("description", ""),
                    "status": data.get("status"),
                    "file": str(checkpoint_file)
                })
            except:
                pass
        return checkpoints
    
    async def auto_save(
        self,
        state: WorkflowState,
        interval: float = 30.0,
        create_checkpoint: bool = False
    ):
        """
        自动保存状态（异步）
        
        Args:
            state: 工作流状态
            interval: 保存间隔（秒）
            create_checkpoint: 是否创建检查点
        """
        while state.status not in [
            WorkflowStatus.COMPLETED.value,
            WorkflowStatus.FAILED.value
        ]:
            await asyncio.sleep(interval)
            if state.status not in [WorkflowStatus.COMPLETED.value, WorkflowStatus.FAILED.value]:
                self.save_state(state, create_checkpoint=create_checkpoint)


# 全局状态管理器实例
_state_manager: Optional[WorkflowStateManager] = None


def get_state_manager(
    work_dir: Optional[Path] = None,
    **kwargs
) -> WorkflowStateManager:
    """
    获取或创建全局状态管理器
    
    Args:
        work_dir: 工作目录
        **kwargs: 传递给 WorkflowStateManager 的参数
    
    Returns:
        WorkflowStateManager 实例
    """
    global _state_manager
    
    if work_dir is None:
        work_dir = Path(".")
    
    if _state_manager is None or _state_manager.work_dir != work_dir:
        _state_manager = WorkflowStateManager(work_dir, **kwargs)
    
    return _state_manager