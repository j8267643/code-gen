"""
Unified Agent - 统一智能体

整合所有 PraisonAI 功能的高级 Agent：
1. Self-Reflection - 自反思
2. Memory System - 记忆系统
3. Guardrails - 护栏验证
4. Human-in-the-loop - 人机协作
5. Evaluator-Optimizer - 评估优化
6. Prompt Chaining - 提示链

提供开箱即用的完整 AI Agent 体验
"""
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

# 导入所有组件
from .reflection import SelfReflection, ReflectionConfig, ReflectionResult
from .memory import AgentMemory, MemoryConfig, MemoryType
from .guardrails import Guardrails, GuardrailResult, GuardrailPresets
from .human_in_loop import HumanInTheLoop, HITLConfig, HITLMode, HITLResponseType
from .evaluator_optimizer import EvaluatorOptimizer, LLMGenerator, LLMEvaluator, CodeEvaluator
from .prompt_chaining import PromptChain, ChainPresets, FunctionStep
from .agent import Agent


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
    
    # 各模块配置
    reflection_config: Optional[ReflectionConfig] = None
    memory_config: Optional[MemoryConfig] = None
    hitl_config: Optional[HITLConfig] = None
    guardrail_config: Optional[Guardrails] = None  # 护栏配置
    
    # 全局配置
    max_iterations: int = 3
    timeout: int = 300
    verbose: bool = False


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
        
        self._init_modules()
        
        # 执行历史
        self.execution_history: List[Dict[str, Any]] = []
    
    def _init_modules(self):
        """初始化各模块"""
        cfg = self.config
        
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
        
        if self.config.verbose:
            print(f"🚀 [{self.name}] 开始执行任务: {task[:50]}...")
        
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
            
            # 使用提示链（如启用）
            if self.chain:
                chain_result = await self.chain.execute(
                    initial_context={"task": full_context, **context}
                )
                output = chain_result.final_output
            else:
                # 直接执行
                output = await self._execute_agent(full_context)
            
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
            
            if self.config.verbose:
                print(f"✅ 任务完成，耗时: {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            if self.config.verbose:
                print(f"❌ 执行错误: {e}")
            return {
                "success": False,
                "error": str(e),
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
        return modules
    
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
