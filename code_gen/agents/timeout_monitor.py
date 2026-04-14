"""
Timeout Monitor - 单元监督计时器（超时监控）

基于 GSD-2 的超时监控设计，用于：
1. 监控任务执行时间
2. 检测超时并触发处理
3. 支持多级超时策略
4. 提供超时报告
"""
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor


class TimeoutAction(str, Enum):
    """超时处理动作"""
    WARN = "warn"           # 警告
    CANCEL = "cancel"       # 取消
    RESTART = "restart"     # 重启
    ESCALATE = "escalate"   # 升级
    NOTIFY = "notify"       # 通知


class TimeoutLevel(str, Enum):
    """超时级别"""
    SOFT = "soft"       # 软超时（警告）
    HARD = "hard"       # 硬超时（强制终止）
    CRITICAL = "critical"  # 严重超时（升级处理）


@dataclass
class TimeoutConfig:
    """超时配置"""
    soft_timeout: float = 30.0      # 软超时（秒）
    hard_timeout: float = 60.0      # 硬超时（秒）
    critical_timeout: float = 120.0  # 严重超时（秒）
    
    soft_action: str = TimeoutAction.WARN.value
    hard_action: str = TimeoutAction.CANCEL.value
    critical_action: str = TimeoutAction.ESCALATE.value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "soft_timeout": self.soft_timeout,
            "hard_timeout": self.hard_timeout,
            "critical_timeout": self.critical_timeout,
            "soft_action": self.soft_action,
            "hard_action": self.hard_action,
            "critical_action": self.critical_action
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimeoutConfig":
        return cls(**data)


@dataclass
class MonitoredTask:
    """被监控的任务"""
    task_id: str
    task_name: str
    start_time: float
    timeout_config: TimeoutConfig
    status: str = "running"  # running, completed, cancelled, timeout
    soft_triggered: bool = False
    hard_triggered: bool = False
    critical_triggered: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def elapsed_time(self) -> float:
        """获取已执行时间"""
        return time.time() - self.start_time
    
    def check_timeout(self) -> Optional[str]:
        """
        检查是否超时
        
        Returns:
            超时级别或 None
        """
        elapsed = self.elapsed_time
        
        if elapsed >= self.timeout_config.critical_timeout and not self.critical_triggered:
            return TimeoutLevel.CRITICAL.value
        elif elapsed >= self.timeout_config.hard_timeout and not self.hard_triggered:
            return TimeoutLevel.HARD.value
        elif elapsed >= self.timeout_config.soft_timeout and not self.soft_triggered:
            return TimeoutLevel.SOFT.value
        
        return None
    
    def mark_triggered(self, level: str):
        """标记超时已触发"""
        if level == TimeoutLevel.SOFT.value:
            self.soft_triggered = True
        elif level == TimeoutLevel.HARD.value:
            self.hard_triggered = True
        elif level == TimeoutLevel.CRITICAL.value:
            self.critical_triggered = True


@dataclass
class TimeoutEvent:
    """超时事件"""
    event_id: str
    task_id: str
    task_name: str
    timeout_level: str
    action: str
    elapsed_time: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    handled: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "timeout_level": self.timeout_level,
            "action": self.action,
            "elapsed_time": self.elapsed_time,
            "timestamp": self.timestamp,
            "handled": self.handled,
            "metadata": self.metadata
        }


class TimeoutMonitor:
    """
    超时监控器
    
    监控任务执行时间，检测并处理超时
    """
    
    def __init__(
        self,
        check_interval: float = 1.0,
        default_config: Optional[TimeoutConfig] = None
    ):
        self.check_interval = check_interval
        self.default_config = default_config or TimeoutConfig()
        
        # 任务存储
        self._tasks: Dict[str, MonitoredTask] = {}
        self._events: List[TimeoutEvent] = []
        
        # 回调
        self._on_soft_timeout: List[Callable[[MonitoredTask], None]] = []
        self._on_hard_timeout: List[Callable[[MonitoredTask], None]] = []
        self._on_critical_timeout: List[Callable[[MonitoredTask], None]] = []
        self._on_timeout_event: List[Callable[[TimeoutEvent], None]] = []
        
        # 监控任务
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        # 线程池（用于同步回调）
        self._executor = ThreadPoolExecutor(max_workers=2)
    
    async def start(self):
        """启动监控器"""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        print("⏱️ 超时监控器已启动")
    
    async def stop(self):
        """停止监控器"""
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        self._executor.shutdown(wait=False)
        print("⏱️ 超时监控器已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                await self._check_all_tasks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ 监控循环错误: {e}")
    
    async def _check_all_tasks(self):
        """检查所有任务"""
        for task_id, task in list(self._tasks.items()):
            if task.status != "running":
                continue
            
            timeout_level = task.check_timeout()
            if timeout_level:
                await self._handle_timeout(task, timeout_level)
    
    async def _handle_timeout(self, task: MonitoredTask, level: str):
        """处理超时"""
        task.mark_triggered(level)
        
        # 获取对应的动作
        config = task.timeout_config
        if level == TimeoutLevel.SOFT.value:
            action = config.soft_action
            callbacks = self._on_soft_timeout
        elif level == TimeoutLevel.HARD.value:
            action = config.hard_action
            callbacks = self._on_hard_timeout
        else:  # CRITICAL
            action = config.critical_action
            callbacks = self._on_critical_timeout
        
        # 创建事件
        event = TimeoutEvent(
            event_id=self._generate_event_id(),
            task_id=task.task_id,
            task_name=task.task_name,
            timeout_level=level,
            action=action,
            elapsed_time=task.elapsed_time
        )
        self._events.append(event)
        
        # 打印警告
        emoji = {"soft": "⚠️", "hard": "🛑", "critical": "🚨"}.get(level, "⚠️")
        print(f"{emoji} 任务超时 [{level}]: {task.task_name} ({task.elapsed_time:.1f}s)")
        
        # 执行动作
        await self._execute_action(task, action, level)
        
        # 触发回调
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    await asyncio.get_event_loop().run_in_executor(
                        self._executor, callback, task
                    )
            except Exception as e:
                print(f"⚠️ 超时回调错误: {e}")
        
        # 触发通用事件回调
        for callback in self._on_timeout_event:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    await asyncio.get_event_loop().run_in_executor(
                        self._executor, callback, event
                    )
            except Exception as e:
                print(f"⚠️ 事件回调错误: {e}")
    
    async def _execute_action(self, task: MonitoredTask, action: str, level: str):
        """执行超时动作"""
        if action == TimeoutAction.WARN.value:
            # 仅警告，不执行操作
            pass
        
        elif action == TimeoutAction.CANCEL.value:
            # 标记任务为取消
            task.status = "cancelled"
            print(f"🛑 任务已取消: {task.task_id}")
        
        elif action == TimeoutAction.RESTART.value:
            # 标记任务需要重启
            task.status = "restart_needed"
            print(f"🔄 任务需要重启: {task.task_id}")
        
        elif action == TimeoutAction.ESCALATE.value:
            # 升级处理（可以通知管理员等）
            task.status = "escalated"
            print(f"🚨 任务已升级: {task.task_id}")
        
        elif action == TimeoutAction.NOTIFY.value:
            # 发送通知
            print(f"📢 超时通知: {task.task_name} 已超时 {task.elapsed_time:.1f}s")
    
    def _generate_event_id(self) -> str:
        """生成事件ID"""
        import hashlib
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.md5(
            str(time.time()).encode()
        ).hexdigest()[:4]
        return f"timeout_{timestamp}_{hash_suffix}"
    
    def start_monitoring(
        self,
        task_id: str,
        task_name: str,
        timeout_config: Optional[TimeoutConfig] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MonitoredTask:
        """
        开始监控任务
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            timeout_config: 超时配置（None则使用默认）
            metadata: 元数据
        
        Returns:
            MonitoredTask 对象
        """
        if task_id in self._tasks:
            raise ValueError(f"任务已在监控中: {task_id}")
        
        task = MonitoredTask(
            task_id=task_id,
            task_name=task_name,
            start_time=time.time(),
            timeout_config=timeout_config or self.default_config,
            metadata=metadata or {}
        )
        
        self._tasks[task_id] = task
        print(f"⏱️ 开始监控任务: {task_name} (ID: {task_id})")
        
        return task
    
    def stop_monitoring(self, task_id: str, status: str = "completed") -> Optional[MonitoredTask]:
        """
        停止监控任务
        
        Args:
            task_id: 任务ID
            status: 最终状态
        
        Returns:
            MonitoredTask 对象或 None
        """
        task = self._tasks.get(task_id)
        if task:
            task.status = status
            elapsed = task.elapsed_time
            print(f"✅ 停止监控任务: {task.task_name} (耗时: {elapsed:.2f}s)")
        return task
    
    def get_task(self, task_id: str) -> Optional[MonitoredTask]:
        """获取任务信息"""
        return self._tasks.get(task_id)
    
    def get_running_tasks(self) -> List[MonitoredTask]:
        """获取正在运行的任务"""
        return [
            task for task in self._tasks.values()
            if task.status == "running"
        ]
    
    def get_timeout_events(
        self,
        task_id: Optional[str] = None,
        level: Optional[str] = None,
        unhandled_only: bool = False
    ) -> List[TimeoutEvent]:
        """获取超时事件"""
        events = self._events
        
        if task_id:
            events = [e for e in events if e.task_id == task_id]
        
        if level:
            events = [e for e in events if e.timeout_level == level]
        
        if unhandled_only:
            events = [e for e in events if not e.handled]
        
        return events
    
    def acknowledge_event(self, event_id: str):
        """确认处理事件"""
        for event in self._events:
            if event.event_id == event_id:
                event.handled = True
                break
    
    def on_soft_timeout(self, callback: Callable[[MonitoredTask], None]):
        """注册软超时回调"""
        self._on_soft_timeout.append(callback)
    
    def on_hard_timeout(self, callback: Callable[[MonitoredTask], None]):
        """注册硬超时回调"""
        self._on_hard_timeout.append(callback)
    
    def on_critical_timeout(self, callback: Callable[[MonitoredTask], None]):
        """注册严重超时回调"""
        self._on_critical_timeout.append(callback)
    
    def on_timeout_event(self, callback: Callable[[TimeoutEvent], None]):
        """注册超时事件回调"""
        self._on_timeout_event.append(callback)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_tasks = len(self._tasks)
        running_tasks = len(self.get_running_tasks())
        timeout_events = len(self._events)
        unhandled_events = len([e for e in self._events if not e.handled])
        
        # 按级别统计
        level_counts = {}
        for event in self._events:
            level_counts[event.timeout_level] = level_counts.get(event.timeout_level, 0) + 1
        
        return {
            "total_tasks": total_tasks,
            "running_tasks": running_tasks,
            "completed_tasks": total_tasks - running_tasks,
            "timeout_events": timeout_events,
            "unhandled_events": unhandled_events,
            "events_by_level": level_counts,
            "monitor_active": self._running
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """生成报告"""
        stats = self.get_statistics()
        
        # 最近的事件
        recent_events = sorted(
            self._events,
            key=lambda e: e.timestamp,
            reverse=True
        )[:10]
        
        return {
            "generated_at": datetime.now().isoformat(),
            "statistics": stats,
            "recent_events": [e.to_dict() for e in recent_events],
            "running_tasks": [
                {
                    "task_id": t.task_id,
                    "task_name": t.task_name,
                    "elapsed_time": t.elapsed_time,
                    "soft_triggered": t.soft_triggered,
                    "hard_triggered": t.hard_triggered
                }
                for t in self.get_running_tasks()
            ]
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop()


# 装饰器：自动监控函数执行时间
def with_timeout(
    soft_timeout: float = 30.0,
    hard_timeout: float = 60.0,
    critical_timeout: float = 120.0,
    monitor: Optional[TimeoutMonitor] = None
):
    """
    超时监控装饰器
    
    Example:
        >>> @with_timeout(soft_timeout=10, hard_timeout=20)
        ... async def long_running_task():
        ...     await asyncio.sleep(15)
        ...     return "completed"
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 获取或创建监控器
            mon = monitor or _default_monitor
            
            # 生成任务ID
            task_id = f"{func.__name__}_{int(time.time() * 1000)}"
            
            # 创建超时配置
            config = TimeoutConfig(
                soft_timeout=soft_timeout,
                hard_timeout=hard_timeout,
                critical_timeout=critical_timeout
            )
            
            # 开始监控
            task = mon.start_monitoring(
                task_id=task_id,
                task_name=func.__name__,
                timeout_config=config
            )
            
            try:
                # 执行函数
                result = await func(*args, **kwargs)
                mon.stop_monitoring(task_id, status="completed")
                return result
            except asyncio.CancelledError:
                mon.stop_monitoring(task_id, status="cancelled")
                raise
            except Exception as e:
                mon.stop_monitoring(task_id, status="failed")
                raise
        
        return wrapper
    return decorator


# 默认监控器实例
_default_monitor: Optional[TimeoutMonitor] = None


def get_timeout_monitor(**kwargs) -> TimeoutMonitor:
    """
    获取或创建默认超时监控器
    
    Returns:
        TimeoutMonitor 实例
    """
    global _default_monitor
    
    if _default_monitor is None:
        _default_monitor = TimeoutMonitor(**kwargs)
    
    return _default_monitor