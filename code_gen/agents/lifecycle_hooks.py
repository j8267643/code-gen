"""
Lifecycle Hooks - 生命周期钩子

基于 GSD-2 的 LifecycleHooks 设计，提供：
1. 在关键节点执行自定义逻辑
2. 支持同步和异步钩子
3. 钩子优先级管理
4. 错误隔离（一个钩子失败不影响其他）
5. 钩子链执行

使用场景:
- 在 Agent 执行前后添加日志
- 工作流步骤拦截和修改
- 系统初始化和清理
- 扩展系统行为

使用示例:
    >>> from lifecycle_hooks import LifecycleHooks, HookPoint
    >>> 
    >>> hooks = LifecycleHooks()
    >>> 
    >>> # 注册钩子
    >>> @hooks.on(HookPoint.AGENT_START)
    >>> def log_agent_start(context):
    ...     print(f"Agent starting: {context['agent_name']}")
    >>> 
    >>> # 执行钩子
    >>> await hooks.execute(HookPoint.AGENT_START, {"agent_name": "Coder"})
"""
import asyncio
import inspect
from typing import Dict, Any, List, Optional, Callable, Union, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from functools import wraps


class HookPoint(Enum):
    """钩子点 - 系统关键节点"""
    # 系统级别
    SYSTEM_INIT = "system:init"
    SYSTEM_SHUTDOWN = "system:shutdown"
    CONFIG_LOADED = "config:loaded"
    
    # Agent 级别
    AGENT_START = "agent:start"
    AGENT_END = "agent:end"
    AGENT_ERROR = "agent:error"
    
    # 任务级别
    TASK_START = "task:start"
    TASK_END = "task:end"
    TASK_ERROR = "task:error"
    
    # 工具级别
    TOOL_PRE_EXECUTE = "tool:pre_execute"
    TOOL_POST_EXECUTE = "tool:post_execute"
    TOOL_ERROR = "tool:error"
    
    # 工作流级别
    WORKFLOW_START = "workflow:start"
    WORKFLOW_END = "workflow:end"
    WORKFLOW_STEP_START = "workflow:step:start"
    WORKFLOW_STEP_END = "workflow:step:end"
    
    # 会话级别
    SESSION_CREATE = "session:create"
    SESSION_RESTORE = "session:restore"
    SESSION_SAVE = "session:save"
    SESSION_CLOSE = "session:close"


class HookPriority(Enum):
    """钩子优先级"""
    HIGHEST = 0
    HIGH = 10
    NORMAL = 20
    LOW = 30
    LOWEST = 40


@dataclass
class Hook:
    """钩子定义"""
    name: str
    point: HookPoint
    handler: Callable
    priority: HookPriority
    once: bool = False
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.created_at = datetime.now()


@dataclass
class HookResult:
    """钩子执行结果"""
    hook_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class HookContext:
    """钩子上下文"""
    hook_point: HookPoint
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取数据"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置数据"""
        self.data[key] = value


class LifecycleHooks:
    """
    生命周期钩子管理器
    
    管理在系统关键节点执行的自定义逻辑
    """
    
    def __init__(self):
        # 钩子存储: {hook_point: [Hook]}
        self._hooks: Dict[HookPoint, List[Hook]] = {}
        
        # 执行统计
        self._stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "hooks_registered": 0
        }
        
        # 全局拦截器（可以修改上下文）
        self._interceptors: List[Callable] = []
    
    def register(
        self,
        point: HookPoint,
        handler: Callable,
        name: Optional[str] = None,
        priority: HookPriority = HookPriority.NORMAL,
        once: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        注册钩子
        
        Args:
            point: 钩子点
            handler: 处理函数
            name: 钩子名称（自动生成如果不提供）
            priority: 优先级
            once: 是否只执行一次
            metadata: 元数据
        
        Returns:
            钩子名称
        """
        hook_name = name or f"{point.value}_{self._stats['hooks_registered']}"
        
        hook = Hook(
            name=hook_name,
            point=point,
            handler=handler,
            priority=priority,
            once=once,
            metadata=metadata or {}
        )
        
        if point not in self._hooks:
            self._hooks[point] = []
        
        self._hooks[point].append(hook)
        
        # 按优先级排序
        self._hooks[point].sort(key=lambda h: h.priority.value)
        
        self._stats["hooks_registered"] += 1
        
        return hook_name
    
    def on(
        self,
        point: HookPoint,
        name: Optional[str] = None,
        priority: HookPriority = HookPriority.NORMAL,
        once: bool = False
    ):
        """
        装饰器：注册钩子
        
        Example:
            >>> @hooks.on(HookPoint.AGENT_START)
            >>> def my_hook(context):
            ...     print("Agent starting")
        """
        def decorator(func: Callable) -> Callable:
            self.register(
                point=point,
                handler=func,
                name=name or func.__name__,
                priority=priority,
                once=once
            )
            return func
        return decorator
    
    def unregister(self, point: HookPoint, name: str) -> bool:
        """
        注销钩子
        
        Args:
            point: 钩子点
            name: 钩子名称
        
        Returns:
            是否成功
        """
        if point not in self._hooks:
            return False
        
        original_count = len(self._hooks[point])
        self._hooks[point] = [h for h in self._hooks[point] if h.name != name]
        
        return len(self._hooks[point]) < original_count
    
    def enable(self, point: HookPoint, name: str) -> bool:
        """启用钩子"""
        hook = self._get_hook(point, name)
        if hook:
            hook.enabled = True
            return True
        return False
    
    def disable(self, point: HookPoint, name: str) -> bool:
        """禁用钩子"""
        hook = self._get_hook(point, name)
        if hook:
            hook.enabled = False
            return True
        return False
    
    def _get_hook(self, point: HookPoint, name: str) -> Optional[Hook]:
        """获取钩子"""
        if point not in self._hooks:
            return None
        
        for hook in self._hooks[point]:
            if hook.name == name:
                return hook
        
        return None
    
    async def execute(
        self,
        point: HookPoint,
        data: Optional[Dict[str, Any]] = None,
        context: Optional[HookContext] = None
    ) -> List[HookResult]:
        """
        执行钩子
        
        Args:
            point: 钩子点
            data: 数据
            context: 上下文（可选）
        
        Returns:
            执行结果列表
        """
        if context is None:
            context = HookContext(hook_point=point, data=data or {})
        
        # 运行拦截器
        for interceptor in self._interceptors:
            try:
                if asyncio.iscoroutinefunction(interceptor):
                    await interceptor(context)
                else:
                    interceptor(context)
            except Exception as e:
                print(f"Interceptor error: {e}")
        
        results = []
        
        if point not in self._hooks:
            return results
        
        hooks_to_remove = []
        
        for hook in self._hooks[point]:
            if not hook.enabled:
                continue
            
            start_time = datetime.now()
            
            try:
                # 执行钩子
                if asyncio.iscoroutinefunction(hook.handler):
                    result_data = await hook.handler(context)
                else:
                    result_data = hook.handler(context)
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                results.append(HookResult(
                    hook_name=hook.name,
                    success=True,
                    data=result_data,
                    execution_time_ms=execution_time
                ))
                
                self._stats["successful_executions"] += 1
                
                # 标记一次性钩子
                if hook.once:
                    hooks_to_remove.append(hook.name)
                    
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                results.append(HookResult(
                    hook_name=hook.name,
                    success=False,
                    error=str(e),
                    execution_time_ms=execution_time
                ))
                
                self._stats["failed_executions"] += 1
                
                # 继续执行其他钩子
        
        # 移除一次性钩子
        for hook_name in hooks_to_remove:
            self.unregister(point, hook_name)
        
        self._stats["total_executions"] += 1
        
        return results
    
    def execute_sync(
        self,
        point: HookPoint,
        data: Optional[Dict[str, Any]] = None
    ) -> List[HookResult]:
        """
        同步执行钩子
        
        只执行同步钩子，忽略异步钩子
        """
        context = HookContext(hook_point=point, data=data or {})
        results = []
        
        if point not in self._hooks:
            return results
        
        hooks_to_remove = []
        
        for hook in self._hooks[point]:
            if not hook.enabled:
                continue
            
            # 跳过异步钩子
            if asyncio.iscoroutinefunction(hook.handler):
                continue
            
            start_time = datetime.now()
            
            try:
                result_data = hook.handler(context)
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                results.append(HookResult(
                    hook_name=hook.name,
                    success=True,
                    data=result_data,
                    execution_time_ms=execution_time
                ))
                
                if hook.once:
                    hooks_to_remove.append(hook.name)
                    
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                results.append(HookResult(
                    hook_name=hook.name,
                    success=False,
                    error=str(e),
                    execution_time_ms=execution_time
                ))
        
        for hook_name in hooks_to_remove:
            self.unregister(point, hook_name)
        
        return results
    
    def add_interceptor(self, interceptor: Callable) -> None:
        """
        添加全局拦截器
        
        拦截器可以在钩子执行前修改上下文
        """
        self._interceptors.append(interceptor)
    
    def list_hooks(self, point: Optional[HookPoint] = None) -> Dict[str, List[Dict]]:
        """
        列出钩子
        
        Args:
            point: 过滤钩子点
        
        Returns:
            钩子列表
        """
        if point:
            hooks = self._hooks.get(point, [])
            return {
                point.value: [
                    {
                        "name": h.name,
                        "priority": h.priority.name,
                        "enabled": h.enabled,
                        "once": h.once
                    }
                    for h in hooks
                ]
            }
        
        return {
            p.value: [
                {
                    "name": h.name,
                    "priority": h.priority.name,
                    "enabled": h.enabled,
                    "once": h.once
                }
                for h in hooks
            ]
            for p, hooks in self._hooks.items()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "hook_points": len(self._hooks),
            "total_hooks": sum(len(hooks) for hooks in self._hooks.values())
        }
    
    def clear(self, point: Optional[HookPoint] = None) -> None:
        """
        清除钩子
        
        Args:
            point: 指定钩子点，None 表示清除所有
        """
        if point:
            if point in self._hooks:
                del self._hooks[point]
        else:
            self._hooks.clear()


# 全局钩子实例
_global_hooks: Optional[LifecycleHooks] = None


def get_lifecycle_hooks() -> LifecycleHooks:
    """获取全局生命周期钩子实例"""
    global _global_hooks
    if _global_hooks is None:
        _global_hooks = LifecycleHooks()
    return _global_hooks


# 便捷函数
def on_hook(point: HookPoint, **kwargs):
    """便捷装饰器"""
    return get_lifecycle_hooks().on(point, **kwargs)


async def execute_hooks(point: HookPoint, data: Optional[Dict[str, Any]] = None):
    """便捷函数：执行钩子"""
    return await get_lifecycle_hooks().execute(point, data)
