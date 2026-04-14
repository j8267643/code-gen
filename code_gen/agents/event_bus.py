"""
Event Bus - 事件总线

基于 GSD-2 的事件总线设计，提供：
1. 发布-订阅模式解耦组件
2. 类型安全的事件传递
3. 异步事件处理
4. 错误隔离（一个处理器失败不影响其他）
5. 支持一次性监听器

使用示例:
    >>> from event_bus import EventBus, get_event_bus
    >>> 
    >>> bus = get_event_bus()
    >>> 
    >>> # 订阅事件
    >>> def on_task_started(data):
    ...     print(f"任务开始: {data['task_id']}")
    >>> 
    >>> unsubscribe = bus.on("task:started", on_task_started)
    >>> 
    >>> # 发布事件
    >>> bus.emit("task:started", {"task_id": "123", "name": "测试任务"})
    >>> 
    >>> # 取消订阅
    >>> unsubscribe()
"""
from typing import Dict, Any, List, Optional, Callable, Union, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import asyncio
import inspect
from collections import defaultdict
import json


class EventPriority(Enum):
    """事件优先级"""
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class Event:
    """事件对象"""
    name: str
    data: Any
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "metadata": self.metadata
        }
    
    def __repr__(self) -> str:
        return f"Event(name='{self.name}', source='{self.source}', timestamp='{self.timestamp.isoformat()}')"


# 事件处理器类型
EventHandler = Callable[[Any], Union[None, asyncio.Future]]


class EventBus:
    """
    事件总线
    
    轻量级发布-订阅实现，支持同步和异步处理器
    """
    
    def __init__(self, name: str = "default"):
        self.name = name
        # 处理器存储: {event_name: [(handler, priority, once)]}
        self._handlers: Dict[str, List[tuple]] = defaultdict(list)
        # 通配符处理器
        self._wildcard_handlers: List[tuple] = []
        # 事件历史（用于调试）
        self._history: List[Event] = []
        self._max_history = 1000
        # 统计
        self._stats = {
            "total_emitted": 0,
            "total_handled": 0,
            "errors": 0
        }
    
    def on(
        self,
        event_name: str,
        handler: EventHandler,
        priority: EventPriority = EventPriority.NORMAL,
        once: bool = False
    ) -> Callable[[], None]:
        """
        订阅事件
        
        Args:
            event_name: 事件名称（使用通配符 '*' 订阅所有事件）
            handler: 事件处理器函数
            priority: 处理优先级
            once: 是否只处理一次
        
        Returns:
            取消订阅函数
        """
        if event_name == "*":
            # 通配符订阅
            self._wildcard_handlers.append((handler, priority, once))
            # 按优先级排序
            self._wildcard_handlers.sort(key=lambda x: x[1].value)
            
            def unsubscribe():
                self._wildcard_handlers[:] = [
                    h for h in self._wildcard_handlers if h[0] != handler
                ]
        else:
            # 特定事件订阅
            self._handlers[event_name].append((handler, priority, once))
            # 按优先级排序
            self._handlers[event_name].sort(key=lambda x: x[1].value)
            
            def unsubscribe():
                if event_name in self._handlers:
                    self._handlers[event_name][:] = [
                        h for h in self._handlers[event_name] if h[0] != handler
                    ]
        
        return unsubscribe
    
    def once(
        self,
        event_name: str,
        handler: EventHandler,
        priority: EventPriority = EventPriority.NORMAL
    ) -> Callable[[], None]:
        """订阅事件（只处理一次）"""
        return self.on(event_name, handler, priority, once=True)
    
    def emit(
        self,
        event_name: str,
        data: Any = None,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        发布事件（同步）
        
        Returns:
            处理的处理器数量
        """
        event = Event(
            name=event_name,
            data=data,
            source=source,
            metadata=metadata or {}
        )
        
        # 记录历史
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        
        self._stats["total_emitted"] += 1
        
        # 收集所有处理器
        handlers_to_call = []
        
        # 特定事件处理器
        if event_name in self._handlers:
            handlers_to_call.extend(self._handlers[event_name])
        
        # 通配符处理器
        handlers_to_call.extend(self._wildcard_handlers)
        
        # 调用处理器
        handled_count = 0
        handlers_to_remove = []
        
        for handler, priority, once in handlers_to_call:
            try:
                result = handler(data)
                
                # 如果是协程，创建任务
                if inspect.iscoroutine(result):
                    asyncio.create_task(result)
                
                handled_count += 1
                self._stats["total_handled"] += 1
                
                # 标记一次性处理器
                if once:
                    handlers_to_remove.append((event_name if event_name != "*" else "*", handler))
                    
            except Exception as e:
                self._stats["errors"] += 1
                print(f"⚠️ 事件处理器错误 ({event_name}): {e}")
                # 继续处理其他处理器
        
        # 移除一次性处理器
        for event_key, handler in handlers_to_remove:
            if event_key == "*":
                self._wildcard_handlers[:] = [
                    h for h in self._wildcard_handlers if h[0] != handler
                ]
            else:
                self._handlers[event_key][:] = [
                    h for h in self._handlers[event_key] if h[0] != handler
                ]
        
        return handled_count
    
    async def emit_async(
        self,
        event_name: str,
        data: Any = None,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        发布事件（异步）
        
        等待所有异步处理器完成
        """
        event = Event(
            name=event_name,
            data=data,
            source=source,
            metadata=metadata or {}
        )
        
        # 记录历史
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        
        self._stats["total_emitted"] += 1
        
        # 收集所有处理器
        handlers_to_call = []
        
        if event_name in self._handlers:
            handlers_to_call.extend(self._handlers[event_name])
        handlers_to_call.extend(self._wildcard_handlers)
        
        # 调用处理器并等待
        handled_count = 0
        handlers_to_remove = []
        tasks = []
        
        for handler, priority, once in handlers_to_call:
            try:
                result = handler(data)
                
                # 如果是协程，收集任务
                if inspect.iscoroutine(result):
                    tasks.append(result)
                
                handled_count += 1
                self._stats["total_handled"] += 1
                
                if once:
                    handlers_to_remove.append((event_name if event_name != "*" else "*", handler))
                    
            except Exception as e:
                self._stats["errors"] += 1
                print(f"⚠️ 事件处理器错误 ({event_name}): {e}")
        
        # 等待所有异步任务
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # 移除一次性处理器
        for event_key, handler in handlers_to_remove:
            if event_key == "*":
                self._wildcard_handlers[:] = [
                    h for h in self._wildcard_handlers if h[0] != handler
                ]
            else:
                self._handlers[event_key][:] = [
                    h for h in self._handlers[event_key] if h[0] != handler
                ]
        
        return handled_count
    
    def off(self, event_name: str, handler: Optional[EventHandler] = None) -> None:
        """
        取消订阅
        
        Args:
            event_name: 事件名称
            handler: 特定处理器（None则取消所有）
        """
        if event_name == "*":
            if handler:
                self._wildcard_handlers[:] = [
                    h for h in self._wildcard_handlers if h[0] != handler
                ]
            else:
                self._wildcard_handlers.clear()
        else:
            if event_name in self._handlers:
                if handler:
                    self._handlers[event_name][:] = [
                        h for h in self._handlers[event_name] if h[0] != handler
                    ]
                else:
                    del self._handlers[event_name]
    
    def clear(self) -> None:
        """清除所有处理器和历史"""
        self._handlers.clear()
        self._wildcard_handlers.clear()
        self._history.clear()
        self._stats = {
            "total_emitted": 0,
            "total_handled": 0,
            "errors": 0
        }
    
    def get_history(
        self,
        event_name: Optional[str] = None,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[Event]:
        """
        获取事件历史
        
        Args:
            event_name: 过滤特定事件
            limit: 最大返回数量
            since: 从此时间之后的事件
        
        Returns:
            事件列表
        """
        result = self._history
        
        if event_name:
            result = [e for e in result if e.name == event_name]
        
        if since:
            result = [e for e in result if e.timestamp >= since]
        
        return result[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "handlers_count": sum(len(h) for h in self._handlers.values()) + len(self._wildcard_handlers),
            "history_count": len(self._history)
        }
    
    def has_handlers(self, event_name: str) -> bool:
        """检查是否有处理器订阅了该事件"""
        return event_name in self._handlers and len(self._handlers[event_name]) > 0


# 全局事件总线实例
_global_event_bus: Optional[EventBus] = None


def get_event_bus(name: str = "default") -> EventBus:
    """
    获取全局事件总线实例
    
    Args:
        name: 事件总线名称
    
    Returns:
        EventBus 实例
    """
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus(name)
    return _global_event_bus


def create_event_bus(name: str = "custom") -> EventBus:
    """
    创建独立的事件总线实例
    
    用于需要隔离事件的场景
    
    Args:
        name: 事件总线名称
    
    Returns:
        新的 EventBus 实例
    """
    return EventBus(name)


# 预定义的事件名称（用于类型提示和避免拼写错误）
class AgentEvents:
    """Agent 相关事件"""
    TASK_STARTED = "agent:task:started"
    TASK_COMPLETED = "agent:task:completed"
    TASK_FAILED = "agent:task:failed"
    TOOL_CALLED = "agent:tool:called"
    TOOL_COMPLETED = "agent:tool:completed"
    REFLECTION_STARTED = "agent:reflection:started"
    REFLECTION_COMPLETED = "agent:reflection:completed"


class WorkflowEvents:
    """工作流相关事件"""
    WORKFLOW_STARTED = "workflow:started"
    WORKFLOW_COMPLETED = "workflow:completed"
    WORKFLOW_FAILED = "workflow:failed"
    STEP_STARTED = "workflow:step:started"
    STEP_COMPLETED = "workflow:step:completed"
    STEP_FAILED = "workflow:step:failed"


class SystemEvents:
    """系统相关事件"""
    ERROR = "system:error"
    WARNING = "system:warning"
    INFO = "system:info"
    CONFIG_CHANGED = "system:config:changed"
