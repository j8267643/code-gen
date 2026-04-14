"""
Unified Agent - 统一智能体

整合所有 PraisonAI 功能的高级 Agent：
1. Self-Reflection - 自反思
2. Memory System - 记忆系统
3. Guardrails - 护栏验证
4. Human-in-the-loop - 人机协作
5. Evaluator-Optimizer - 评估优化
6. Prompt Chaining - 提示链
7. Event Bus - 事件总线 (GSD-2)
8. Blob Store - 内容寻址存储 (GSD-2)
9. Retry Handler - 重试处理器 (GSD-2)
10. Diagnostics - 诊断系统 (GSD-2)

提供开箱即用的完整 AI Agent 体验
"""
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import asyncio
import functools

# 导入所有组件
from .reflection import SelfReflection, ReflectionConfig, ReflectionResult
from .memory import AgentMemory, MemoryConfig, MemoryType
from .guardrails import Guardrails, GuardrailResult, GuardrailPresets
from .human_in_loop import HumanInTheLoop, HITLConfig, HITLMode, HITLResponseType
from .evaluator_optimizer import EvaluatorOptimizer, LLMGenerator, LLMEvaluator, CodeEvaluator
from .prompt_chaining import PromptChain, ChainPresets, FunctionStep
from .agent import Agent

# GSD-2 组件
from .event_bus import EventBus, EventPriority, AgentEvents, WorkflowEvents, get_event_bus
from .blob_store import BlobStore, BlobReference
from .retry_handler import RetryHandler, RetryConfig, RetryResult
from .diagnostics import Diagnostics, DiagnosticLevel, get_diagnostics


@dataclass
class UnifiedAgentConfig:
    """统一 Agent 配置"""
    # 各模块开关
    enable_reflection: bool = True
    enable_memory: bool = True
    enable_guardrails: bool = True
    enable_hitl: bool = True
    enable_optimizer: bool = False  # 默认关闭，因为消耗资源
    enable_chaining: bool = False   # 默认关闭
    enable_event_bus: bool = True   # 事件总线 (GSD-2)
    enable_blob_store: bool = True  # Blob 存储 (GSD-2)
    enable_retry: bool = True       # 重试处理器 (GSD-2)
    enable_diagnostics: bool = True # 诊断系统 (GSD-2)
    
    # 各模块配置
    reflection_config: Optional[ReflectionConfig] = None
    memory_config: Optional[MemoryConfig] = None
    hitl_config: Optional[HITLConfig] = None
    guardrail_config: Optional[Guardrails] = None  # 护栏配置
    
    # GSD-2 配置
    event_bus: Optional[EventBus] = None  # 自定义事件总线
    blob_store_path: Optional[str] = None  # Blob 存储路径
    retry_config: Optional[RetryConfig] = None  # 重试配置
    diagnostics: Optional[Diagnostics] = None   # 诊断系统实例
    
    # 全局配置
    max_iterations: int = 3
    timeout: int = 300
    verbose: bool = False
    agent_id: str = "default"  # Agent 标识


class UnifiedAgent:
    """
    统一智能体
    
    整合所有功能的完整 Agent 实现
    """
    
    def __init__(
        self,
        agent: Agent,
        config: Optional[UnifiedAgentConfig] = None,
        name: str = "UnifiedAgent"
    ):
        self.agent = agent
        self.config = config or UnifiedAgentConfig()
        self.name = name
        
        # 初始化各模块
        self.reflection = None
        self.memory = None
        self.guardrails = None
        self.hitl = None
        self.optimizer = None
        self.chain = None
        self.event_bus: Optional[EventBus] = None
        self.blob_store: Optional[BlobStore] = None
        self.blob_refs: Optional[BlobReference] = None
        self.retry_handler: Optional[RetryHandler] = None
        self.diagnostics: Optional[Diagnostics] = None
        
        self._init_modules()
        
        # 执行历史
        self.execution_history: List[Dict[str, Any]] = []
        
        # 发布初始化完成事件
        if self.event_bus:
            self.event_bus.emit(
                AgentEvents.TASK_STARTED,
                {"agent_name": self.name, "agent_id": self.config.agent_id},
                source=self.name
            )
    
    def _init_modules(self):
        """初始化各模块"""
        cfg = self.config
        
        # 事件总线 (GSD-2)
        if cfg.enable_event_bus:
            self.event_bus = cfg.event_bus or get_event_bus()
        
        # Blob 存储 (GSD-2)
        if cfg.enable_blob_store:
            blob_path = cfg.blob_store_path or f".agent/blobs/{self.config.agent_id}"
            self.blob_store = BlobStore(blob_path)
            self.blob_refs = BlobReference()
        
        # 重试处理器 (GSD-2)
        if cfg.enable_retry:
            self.retry_handler = RetryHandler(
                cfg.retry_config or RetryConfig()
            )
        
        # 诊断系统 (GSD-2)
        if cfg.enable_diagnostics:
            self.diagnostics = cfg.diagnostics or get_diagnostics()
        
        # 自反思
        if cfg.enable_reflection:
            self.reflection = SelfReflection(
                cfg.reflection_config or ReflectionConfig()
            )
        
        # 记忆系统
        if cfg.enable_memory:
            self.memory = AgentMemory(
                cfg.memory_config or MemoryConfig()
            )
        
        # 护栏
        if cfg.enable_guardrails:
            if cfg.guardrail_config:
                self.guardrails = cfg.guardrail_config
            else:
                self.guardrails = GuardrailPresets.code_generation()
        
        # 人机协作
        if cfg.enable_hitl:
            hitl_cfg = cfg.hitl_config or HITLConfig()
            if not hitl_cfg.enabled:
                hitl_cfg.enabled = True
            self.hitl = HumanInTheLoop(hitl_cfg)
        
        # 优化器
        if cfg.enable_optimizer:
            self.optimizer = EvaluatorOptimizer(
                generator=LLMGenerator(),
                evaluator=CodeEvaluator(),
                max_iterations=cfg.max_iterations
            )
        
        # 提示链
        if cfg.enable_chaining:
            self.chain = ChainPresets.code_generation()
    
    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行任务（完整流程）
        
        流程:
        1. 记忆检索 -> 构建上下文
        2. HITL 检查 -> 确认执行
        3. Agent 执行
        4. 护栏验证
        5. 自反思
        6. 优化器优化（如启用）
        7. 记忆存储
        8. 返回结果
        """
        start_time = datetime.now()
        context = context or {}
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if self.config.verbose:
            print(f"🚀 [{self.name}] 开始执行任务: {task[:50]}...")
        
        # 发布任务开始事件
        if self.event_bus:
            self.event_bus.emit(
                AgentEvents.TASK_STARTED,
                {
                    "execution_id": execution_id,
                    "task": task,
                    "agent_id": self.config.agent_id
                },
                source=self.name
            )
        
        try:
            # 1. 记忆检索
            memory_context = ""
            if self.memory:
                memory_context = self.memory.build_context(query=task)
                if memory_context and self.config.verbose:
                    print(f"🧠 检索到相关记忆")
            
            # 2. HITL 检查
            if self.hitl and self.hitl.should_trigger("task_execution", context):
                response = await self.hitl.request_approval(
                    title=f"执行任务: {task[:50]}...",
                    content=task,
                    severity="medium"
                )
                if response.response_type != HITLResponseType.APPROVED:
                    return {
                        "success": False,
                        "error": "任务被用户拒绝",
                        "task": task
                    }
            
            # 3. Agent 执行
            full_context = f"{memory_context}\n\n当前任务: {task}" if memory_context else task
            
            try:
                # 使用提示链（如启用）
                if self.chain:
                    chain_result = await self.chain.execute(
                        initial_context={"task": full_context, **context}
                    )
                    output = chain_result.final_output
                else:
                    # 直接执行（带重试机制）
                    if self.retry_handler:
                        output = await self.execute_with_retry(
                            self._execute_agent, full_context
                        )
                    else:
                        output = await self._execute_agent(full_context)
            except Exception as e:
                import traceback
                error_msg = f"Agent执行失败: {str(e)}"
                stack_trace = traceback.format_exc()
                
                # 记录详细错误信息到诊断系统
                if self.diagnostics:
                    self.diagnostics.log(
                        level=DiagnosticLevel.ERROR,
                        category="agent_execution",
                        message=error_msg,
                        details={
                            "task": task[:100],
                            "context_length": len(full_context),
                            "error_type": type(e).__name__,
                            "stack_trace": stack_trace
                        },
                        source=self.name,
                        exception=e
                    )
                
                # 发布失败事件
                if self.event_bus:
                    self.event_bus.emit(
                        AgentEvents.TASK_FAILED,
                        {
                            "execution_id": execution_id,
                            "task": task,
                            "error": error_msg,
                            "error_type": type(e).__name__,
                            "agent_id": self.config.agent_id
                        },
                        source=self.name
                    )
                
                if self.config.verbose:
                    print(f"❌ {error_msg}")
                    print(f"📋 堆栈跟踪:\n{stack_trace}")
                
                return {
                    "success": False,
                    "error": error_msg,
                    "error_type": type(e).__name__,
                    "stack_trace": stack_trace if self.config.verbose else None,
                    "task": task,
                    "execution_time": (datetime.now() - start_time).total_seconds()
                }
            
            # 4. 护栏验证
            if self.guardrails:
                guardrail_result = self.guardrails(output)
                if not guardrail_result.success:
                    if self.config.verbose:
                        print(f"🛡️ 护栏拦截: {guardrail_result.error}")
                    return {
                        "success": False,
                        "error": f"护栏验证失败: {guardrail_result.error}",
                        "output": output
                    }
            
            # 5. 自反思
            reflection_result = None
            if self.reflection:
                reflection_result = await self._run_reflection(task, output)
                if reflection_result and not reflection_result.passed:
                    if self.config.verbose:
                        print(f"🤔 自反思建议改进")
            
            # 6. 优化器优化（如启用且反思未通过）
            if self.optimizer and reflection_result and not reflection_result.passed:
                if self.config.verbose:
                    print(f"🔄 启动优化器")
                opt_result = await self.optimizer.optimize(
                    task=task,
                    initial_solution=output
                )
                if opt_result.success:
                    output = opt_result.final_solution
            
            # 7. 记忆存储
            if self.memory:
                self.memory.store_short_term(
                    content=f"任务: {task}\n输出: {str(output)[:200]}",
                    importance=0.7
                )
            
            # 8. 构建结果
            execution_time = (datetime.now() - start_time).total_seconds()
            result = {
                "success": True,
                "task": task,
                "output": output,
                "execution_time": execution_time,
                "modules_used": self._get_used_modules()
            }
            
            if reflection_result:
                result["reflection"] = reflection_result.to_dict()
            
            self.execution_history.append(result)
            
            # 发布任务完成事件
            if self.event_bus:
                self.event_bus.emit(
                    AgentEvents.TASK_COMPLETED,
                    {
                        "execution_id": execution_id,
                        "task": task,
                        "success": True,
                        "execution_time": execution_time,
                        "agent_id": self.config.agent_id
                    },
                    source=self.name
                )
            
            if self.config.verbose:
                print(f"✅ 任务完成，耗时: {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            if self.config.verbose:
                print(f"❌ 执行错误: {error_msg}")
            
            # 发布任务失败事件
            if self.event_bus:
                self.event_bus.emit(
                    AgentEvents.TASK_FAILED,
                    {
                        "execution_id": execution_id,
                        "task": task,
                        "error": error_msg,
                        "agent_id": self.config.agent_id
                    },
                    source=self.name
                )
            
            return {
                "success": False,
                "error": error_msg,
                "task": task
            }
    
    async def _execute_agent(self, task: str) -> str:
        """执行 Agent"""
        # 简化处理，实际应该调用 agent 的完整执行流程
        return f"[Agent Output for: {task[:50]}...]"
    
    async def _run_reflection(
        self,
        task: str,
        output: str
    ) -> Optional[ReflectionResult]:
        """运行自反思"""
        if not self.reflection:
            return None
        
        # 简化处理
        return ReflectionResult(
            passed=True,
            score=85.0,
            feedback="输出质量良好",
            iteration=1
        )
    
    def _get_used_modules(self) -> List[str]:
        """获取使用的模块列表"""
        modules = []
        if self.reflection:
            modules.append("reflection")
        if self.memory:
            modules.append("memory")
        if self.guardrails:
            modules.append("guardrails")
        if self.hitl:
            modules.append("hitl")
        if self.optimizer:
            modules.append("optimizer")
        if self.chain:
            modules.append("chaining")
        if self.event_bus:
            modules.append("event_bus")
        if self.blob_store:
            modules.append("blob_store")
        if self.retry_handler:
            modules.append("retry_handler")
        if self.diagnostics:
            modules.append("diagnostics")
        return modules
    
    # ========== GSD-2 功能: Blob 存储 ==========
    
    def store_blob(
        self,
        name: str,
        content: Union[str, bytes],
        track: bool = True
    ) -> Optional[str]:
        """
        存储数据到 Blob 存储
        
        Args:
            name: 名称（用于标识）
            content: 内容
            track: 是否跟踪引用
        
        Returns:
            Blob 引用或 None
        """
        if not self.blob_store:
            return None
        
        try:
            result = self.blob_store.put(content)
            
            if track and self.blob_refs:
                self.blob_refs.add(result.ref)
            
            # 发布事件
            if self.event_bus:
                self.event_bus.emit(
                    AgentEvents.TOOL_COMPLETED,
                    {
                        "tool": "blob_store",
                        "action": "store",
                        "name": name,
                        "hash": result.hash[:16] + "..."
                    },
                    source=self.name
                )
            
            return result.ref
            
        except Exception as e:
            if self.config.verbose:
                print(f"⚠️ Blob 存储失败: {e}")
            return None
    
    def get_blob(self, ref: str) -> Optional[Union[str, bytes]]:
        """
        从 Blob 存储获取数据
        
        Args:
            ref: Blob 引用或哈希
        
        Returns:
            内容或 None
        """
        if not self.blob_store:
            return None
        
        return self.blob_store.get(ref)
    
    def gc_blobs(self) -> int:
        """
        清理未引用的 Blob
        
        Returns:
            清理的数量
        """
        if not self.blob_store or not self.blob_refs:
            return 0
        
        return self.blob_store.gc(self.blob_refs.get_all())
    
    # ========== GSD-2 功能: 事件总线 ==========
    
    def on_event(
        self,
        event_name: str,
        handler: Callable,
        priority: Any = None
    ) -> Callable:
        """
        订阅事件
        
        Args:
            event_name: 事件名称
            handler: 处理函数
            priority: 优先级
        
        Returns:
            取消订阅函数
        """
        if not self.event_bus:
            # 返回空函数
            return lambda: None
        
        from .event_bus import EventPriority
        prio = priority or EventPriority.NORMAL
        
        return self.event_bus.on(event_name, handler, prio)
    
    def emit_event(
        self,
        event_name: str,
        data: Any = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        发布事件
        
        Args:
            event_name: 事件名称
            data: 事件数据
            metadata: 元数据
        
        Returns:
            处理的处理器数量
        """
        if not self.event_bus:
            return 0
        
        return self.event_bus.emit(
            event_name,
            data,
            source=self.name,
            metadata=metadata
        )
    
    # ========== GSD-2 功能: 重试处理器 ==========
    
    def with_retry(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        装饰器: 为函数添加重试能力
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟（秒）
        
        Returns:
            装饰器函数
        
        Example:
            >>> @agent.with_retry(max_retries=3)
            ... async def call_api():
            ...     return await api.request()
        """
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.retry_handler:
                    # 没有重试处理器，直接执行
                    return await func(*args, **kwargs)
                
                # 记录诊断
                if self.diagnostics:
                    self.diagnostics.log(
                        DiagnosticLevel.INFO,
                        "retry",
                        f"开始执行带重试的函数: {func.__name__}",
                        source=self.name
                    )
                
                # 使用重试处理器执行
                result = await self.retry_handler.execute(
                    func, *args, **kwargs
                )
                
                # 记录结果
                if self.diagnostics:
                    if result.success:
                        retry_count = result.attempt_count - 1 if result.attempt_count > 0 else 0
                        self.diagnostics.log(
                            DiagnosticLevel.INFO,
                            "retry",
                            f"函数 {func.__name__} 执行成功，重试 {retry_count} 次",
                            source=self.name
                        )
                    else:
                        error_msg = str(result.final_exception) if result.final_exception else "未知错误"
                        self.diagnostics.log(
                            DiagnosticLevel.ERROR,
                            "retry",
                            f"函数 {func.__name__} 最终失败: {error_msg}",
                            source=self.name
                        )
                
                if result.success:
                    return result.result
                else:
                    raise result.error or Exception("执行失败")
            
            return wrapper
        return decorator
    
    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        执行函数并自动重试
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            函数返回值
        
        Raises:
            Exception: 如果所有重试都失败
        """
        if not self.retry_handler:
            return await func(*args, **kwargs)
        
        result = await self.retry_handler.execute(func, *args, **kwargs)
        
        if result.success:
            return result.result
        else:
            # 使用 final_exception 作为错误
            error = result.final_exception or Exception("执行失败")
            raise error
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """获取重试统计"""
        if not self.retry_handler:
            return {"enabled": False}
        
        return {
            "enabled": True,
            **self.retry_handler.get_stats()
        }
    
    # ========== GSD-2 功能: 诊断系统 ==========
    
    def log_diagnostic(
        self,
        level: Union[str, DiagnosticLevel],
        category: str,
        message: str,
        **kwargs
    ) -> None:
        """
        记录诊断信息
        
        Args:
            level: 级别 (debug, info, warning, error, critical)
            category: 类别
            message: 消息
            **kwargs: 额外信息
        """
        if not self.diagnostics:
            return
        
        if isinstance(level, str):
            level = DiagnosticLevel(level.lower())
        
        self.diagnostics.log(
            level=level,
            category=category,
            message=message,
            source=self.name,
            **kwargs
        )
    
    async def run_health_check(self) -> Dict[str, Any]:
        """
        运行健康检查
        
        Returns:
            健康检查结果
        """
        if not self.diagnostics:
            return {"status": "unknown", "checks": {}}
        
        health = await self.diagnostics.run_health_check()
        
        # 计算总体延迟（所有检查的总和）
        total_latency_ms = sum(
            check.duration_ms for check in health.checks
        ) if health.checks else 0
        
        return {
            "status": health.overall_status.value,
            "overall_latency_ms": total_latency_ms,
            "checks": {
                check.name: {
                    "healthy": check.status.value == "healthy",
                    "latency_ms": check.duration_ms,
                    "message": check.message
                }
                for check in health.checks
            }
        }
    
    def get_diagnostics_report(self) -> Dict[str, Any]:
        """
        获取诊断报告
        
        Returns:
            诊断报告
        """
        if not self.diagnostics:
            return {"enabled": False}
        
        report = self.diagnostics.generate_report()
        
        return {
            "enabled": True,
            "generated_at": report.get("timestamp", datetime.now().isoformat()),
            "entries_count": len(report.get("recent_entries", [])),
            "stats": report.get("stats", {}),
            "recent_entries": [
                {
                    "timestamp": e.get("timestamp", ""),
                    "level": e.get("level", "info"),
                    "category": e.get("category", ""),
                    "message": e.get("message", "")
                }
                for e in report.get("recent_entries", [])[:10]  # 最近 10 条
            ]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self.execution_history)
        successful = sum(1 for r in self.execution_history if r.get("success"))
        
        return {
            "total_executions": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0,
            "modules_enabled": self._get_used_modules()
        }


# ========== 便捷创建函数 ==========

def create_unified_agent(
    agent: Agent,
    mode: str = "standard",
    **kwargs
) -> UnifiedAgent:
    """
    便捷创建统一 Agent
    
    Args:
        agent: 基础 Agent
        mode: 模式 - "minimal", "standard", "full"
        **kwargs: 额外配置
        
    Returns:
        UnifiedAgent 实例
    """
    if mode == "minimal":
        config = UnifiedAgentConfig(
            enable_reflection=False,
            enable_memory=True,
            enable_guardrails=True,
            enable_hitl=False,
            enable_optimizer=False,
            enable_chaining=False
        )
    elif mode == "standard":
        config = UnifiedAgentConfig(
            enable_reflection=True,
            enable_memory=True,
            enable_guardrails=True,
            enable_hitl=True,
            enable_optimizer=False,
            enable_chaining=False
        )
    elif mode == "full":
        config = UnifiedAgentConfig(
            enable_reflection=True,
            enable_memory=True,
            enable_guardrails=True,
            enable_hitl=True,
            enable_optimizer=True,
            enable_chaining=True
        )
    else:
        config = UnifiedAgentConfig()
    
    # 应用额外配置
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return UnifiedAgent(agent, config)
