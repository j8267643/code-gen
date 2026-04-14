"""
Tool Tracker - 工具追踪机制

基于 GSD-2 的工具追踪设计，用于：
1. 追踪工具调用历史
2. 分析工具使用模式
3. 检测工具滥用
4. 成本估算
5. 性能监控
"""
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
import json
import hashlib
import asyncio
from collections import defaultdict

from .utils import atomic_write_json


class ToolStatus(str, Enum):
    """工具调用状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ToolCategory(str, Enum):
    """工具类别"""
    FILE_SYSTEM = "file_system"
    CODE_EXECUTION = "code_execution"
    NETWORK = "network"
    DATABASE = "database"
    AI_MODEL = "ai_model"
    EXTERNAL_API = "external_api"
    SYSTEM = "system"
    CUSTOM = "custom"


@dataclass
class ToolCall:
    """工具调用记录"""
    call_id: str
    tool_name: str
    tool_category: str
    agent_id: str
    session_id: str
    input_params: Dict[str, Any] = field(default_factory=dict)
    output_result: Any = None
    error_message: str = ""
    status: str = ToolStatus.PENDING.value
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: float = 0.0
    cost_estimate: float = 0.0  # 预估成本
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolCall":
        return cls(**data)
    
    @property
    def is_successful(self) -> bool:
        """检查调用是否成功"""
        return self.status == ToolStatus.SUCCESS.value
    
    def complete(self, result: Any = None, error: str = ""):
        """标记调用完成"""
        self.end_time = datetime.now().isoformat()
        self.output_result = result
        self.error_message = error
        self.status = ToolStatus.SUCCESS.value if not error else ToolStatus.FAILED.value
        
        # 计算耗时
        if self.start_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.duration_ms = (end - start).total_seconds() * 1000


@dataclass
class ToolStats:
    """工具统计信息"""
    tool_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    total_cost: float = 0.0
    last_called: Optional[str] = None
    error_rate: float = 0.0
    
    def add_call(self, call: ToolCall):
        """添加调用记录"""
        self.total_calls += 1
        self.total_duration_ms += call.duration_ms
        self.total_cost += call.cost_estimate
        self.last_called = call.end_time or call.start_time
        
        if call.is_successful:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
        
        # 更新最大/最小耗时
        if call.duration_ms > self.max_duration_ms:
            self.max_duration_ms = call.duration_ms
        if call.duration_ms < self.min_duration_ms:
            self.min_duration_ms = call.duration_ms
        
        # 计算平均值和错误率
        self.avg_duration_ms = self.total_duration_ms / self.total_calls
        self.error_rate = self.failed_calls / self.total_calls
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "total_duration_ms": self.total_duration_ms,
            "avg_duration_ms": self.avg_duration_ms,
            "max_duration_ms": self.max_duration_ms,
            "min_duration_ms": self.min_duration_ms if self.min_duration_ms != float('inf') else 0,
            "total_cost": self.total_cost,
            "last_called": self.last_called,
            "error_rate": self.error_rate
        }


@dataclass
class SessionToolStats:
    """会话级别的工具统计"""
    session_id: str
    total_calls: int = 0
    tool_breakdown: Dict[str, int] = field(default_factory=dict)
    category_breakdown: Dict[str, int] = field(default_factory=dict)
    total_cost: float = 0.0
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    
    def add_call(self, call: ToolCall):
        """添加调用记录"""
        self.total_calls += 1
        self.total_cost += call.cost_estimate
        
        # 按工具统计
        self.tool_breakdown[call.tool_name] = \
            self.tool_breakdown.get(call.tool_name, 0) + 1
        
        # 按类别统计
        self.category_breakdown[call.tool_category] = \
            self.category_breakdown.get(call.tool_category, 0) + 1
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ToolTracker:
    """
    工具追踪器
    
    追踪所有工具调用，提供分析和报告功能
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        enable_persistence: bool = True,
        max_history: int = 10000
    ):
        self.storage_path = storage_path or Path(".agent/tool_tracking")
        self.enable_persistence = enable_persistence
        self.max_history = max_history
        
        if self.enable_persistence:
            self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 内存存储
        self._calls: Dict[str, ToolCall] = {}
        self._tool_stats: Dict[str, ToolStats] = {}
        self._session_stats: Dict[str, SessionToolStats] = {}
        self._active_calls: Dict[str, ToolCall] = {}
        
        # 回调
        self._on_call_start: List[Callable[[ToolCall], None]] = []
        self._on_call_end: List[Callable[[ToolCall], None]] = []
        self._on_threshold_exceeded: List[Callable[[str, Any], None]] = []
        
        # 阈值设置
        self._thresholds: Dict[str, Any] = {
            "max_calls_per_minute": 100,
            "max_cost_per_session": 10.0,
            "max_errors_per_tool": 10
        }
    
    def _generate_call_id(self) -> str:
        """生成调用ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.md5(
            str(datetime.now().timestamp()).encode()
        ).hexdigest()[:6]
        return f"call_{timestamp}_{hash_suffix}"
    
    def start_call(
        self,
        tool_name: str,
        tool_category: str = ToolCategory.CUSTOM.value,
        agent_id: str = "",
        session_id: str = "",
        input_params: Optional[Dict[str, Any]] = None,
        cost_estimate: float = 0.0
    ) -> ToolCall:
        """
        开始追踪工具调用
        
        Args:
            tool_name: 工具名称
            tool_category: 工具类别
            agent_id: Agent ID
            session_id: 会话ID
            input_params: 输入参数
            cost_estimate: 预估成本
        
        Returns:
            ToolCall 对象
        """
        call_id = self._generate_call_id()
        
        call = ToolCall(
            call_id=call_id,
            tool_name=tool_name,
            tool_category=tool_category,
            agent_id=agent_id,
            session_id=session_id,
            input_params=input_params or {},
            cost_estimate=cost_estimate,
            start_time=datetime.now().isoformat(),
            status=ToolStatus.RUNNING.value
        )
        
        self._active_calls[call_id] = call
        
        # 触发回调
        for callback in self._on_call_start:
            try:
                callback(call)
            except:
                pass
        
        # 检查阈值
        self._check_thresholds(call)
        
        return call
    
    def end_call(
        self,
        call_id: str,
        result: Any = None,
        error: str = ""
    ) -> ToolCall:
        """
        结束工具调用追踪
        
        Args:
            call_id: 调用ID
            result: 调用结果
            error: 错误信息
        
        Returns:
            ToolCall 对象
        """
        call = self._active_calls.pop(call_id, None)
        if not call:
            raise ValueError(f"未找到调用记录: {call_id}")
        
        # 完成调用
        call.complete(result, error)
        
        # 保存到历史
        self._calls[call_id] = call
        
        # 更新工具统计
        if call.tool_name not in self._tool_stats:
            self._tool_stats[call.tool_name] = ToolStats(tool_name=call.tool_name)
        self._tool_stats[call.tool_name].add_call(call)
        
        # 更新会话统计
        if call.session_id:
            if call.session_id not in self._session_stats:
                self._session_stats[call.session_id] = SessionToolStats(
                    session_id=call.session_id
                )
            self._session_stats[call.session_id].add_call(call)
        
        # 触发回调
        for callback in self._on_call_end:
            try:
                callback(call)
            except:
                pass
        
        # 清理旧记录
        self._cleanup_old_records()
        
        # 持久化（如启用）
        if self.enable_persistence:
            self._persist_call(call)
        
        return call
    
    def _check_thresholds(self, call: ToolCall):
        """检查是否超过阈值"""
        # 检查每分钟调用次数
        recent_calls = self._get_recent_calls(minutes=1)
        if len(recent_calls) > self._thresholds["max_calls_per_minute"]:
            self._trigger_threshold_alert("max_calls_per_minute", len(recent_calls))
        
        # 检查会话成本
        if call.session_id:
            session_stats = self._session_stats.get(call.session_id)
            if session_stats and session_stats.total_cost > self._thresholds["max_cost_per_session"]:
                self._trigger_threshold_alert("max_cost_per_session", session_stats.total_cost)
    
    def _get_recent_calls(self, minutes: int = 1) -> List[ToolCall]:
        """获取最近的调用记录"""
        cutoff = datetime.now().timestamp() - (minutes * 60)
        recent = []
        for call in self._calls.values():
            if call.start_time:
                call_time = datetime.fromisoformat(call.start_time).timestamp()
                if call_time > cutoff:
                    recent.append(call)
        return recent
    
    def _trigger_threshold_alert(self, threshold_name: str, value: Any):
        """触发阈值告警"""
        for callback in self._on_threshold_exceeded:
            try:
                callback(threshold_name, value)
            except:
                pass
    
    def _cleanup_old_records(self):
        """清理旧记录"""
        if len(self._calls) > self.max_history:
            # 按时间排序，删除最旧的
            sorted_calls = sorted(
                self._calls.items(),
                key=lambda x: x[1].start_time or ""
            )
            to_remove = len(self._calls) - self.max_history
            for call_id, _ in sorted_calls[:to_remove]:
                del self._calls[call_id]
    
    def _persist_call(self, call: ToolCall):
        """持久化调用记录"""
        file_path = self.storage_path / f"call_{call.call_id}.json"
        atomic_write_json(str(file_path), call.to_dict())
    
    def get_tool_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """获取工具统计"""
        if tool_name:
            stats = self._tool_stats.get(tool_name)
            return stats.to_dict() if stats else {}
        
        return {
            name: stats.to_dict()
            for name, stats in self._tool_stats.items()
        }
    
    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话统计"""
        stats = self._session_stats.get(session_id)
        return stats.to_dict() if stats else None
    
    def get_recent_calls_by_tool(
        self,
        tool_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取工具最近调用记录"""
        calls = [
            call.to_dict()
            for call in self._calls.values()
            if call.tool_name == tool_name
        ]
        calls.sort(key=lambda x: x.get("start_time", ""), reverse=True)
        return calls[:limit]
    
    def get_abnormal_calls(self) -> List[Dict[str, Any]]:
        """获取异常调用（失败或超时）"""
        abnormal = []
        for call in self._calls.values():
            if call.status in [ToolStatus.FAILED.value, ToolStatus.TIMEOUT.value]:
                abnormal.append(call.to_dict())
        return abnormal
    
    def get_cost_report(self) -> Dict[str, Any]:
        """获取成本报告"""
        total_cost = sum(stats.total_cost for stats in self._tool_stats.values())
        cost_by_tool = {
            name: stats.total_cost
            for name, stats in self._tool_stats.items()
        }
        cost_by_category = defaultdict(float)
        
        for call in self._calls.values():
            cost_by_category[call.tool_category] += call.cost_estimate
        
        return {
            "total_cost": total_cost,
            "cost_by_tool": cost_by_tool,
            "cost_by_category": dict(cost_by_category),
            "session_count": len(self._session_stats),
            "total_calls": len(self._calls)
        }
    
    def on_call_start(self, callback: Callable[[ToolCall], None]):
        """注册调用开始回调"""
        self._on_call_start.append(callback)
    
    def on_call_end(self, callback: Callable[[ToolCall], None]):
        """注册调用结束回调"""
        self._on_call_end.append(callback)
    
    def on_threshold_exceeded(self, callback: Callable[[str, Any], None]):
        """注册阈值告警回调"""
        self._on_threshold_exceeded.append(callback)
    
    def set_threshold(self, name: str, value: Any):
        """设置阈值"""
        self._thresholds[name] = value
    
    def export_report(self, file_path: Optional[str] = None) -> str:
        """导出完整报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_calls": len(self._calls),
                "active_calls": len(self._active_calls),
                "unique_tools": len(self._tool_stats),
                "sessions": len(self._session_stats)
            },
            "tool_stats": self.get_tool_stats(),
            "cost_report": self.get_cost_report(),
            "thresholds": self._thresholds
        }
        
        if file_path:
            atomic_write_json(file_path, report)
            return file_path
        
        return json.dumps(report, indent=2, ensure_ascii=False)


# 全局追踪器实例
_tracker: Optional[ToolTracker] = None


def get_tool_tracker(
    storage_path: Optional[Path] = None,
    **kwargs
) -> ToolTracker:
    """
    获取或创建全局工具追踪器
    
    Args:
        storage_path: 存储路径
        **kwargs: 传递给 ToolTracker 的参数
    
    Returns:
        ToolTracker 实例
    """
    global _tracker
    
    if _tracker is None:
        _tracker = ToolTracker(storage_path=storage_path, **kwargs)
    
    return _tracker


# 装饰器用于自动追踪工具调用
def track_tool_call(
    tool_name: Optional[str] = None,
    tool_category: str = ToolCategory.CUSTOM.value,
    cost_estimate: float = 0.0
):
    """
    工具调用追踪装饰器
    
    Example:
        >>> @track_tool_call(tool_name="file_reader", tool_category="file_system")
        ... def read_file(path: str) -> str:
        ...     with open(path) as f:
        ...         return f.read()
    """
    def decorator(func: Callable):
        name = tool_name or func.__name__
        tracker = get_tool_tracker()
        
        def wrapper(*args, **kwargs):
            # 开始追踪
            call = tracker.start_call(
                tool_name=name,
                tool_category=tool_category,
                input_params={"args": args, "kwargs": kwargs},
                cost_estimate=cost_estimate
            )
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                # 结束追踪
                tracker.end_call(call.call_id, result=result)
                return result
            except Exception as e:
                # 记录错误
                tracker.end_call(call.call_id, error=str(e))
                raise
        
        return wrapper
    return decorator