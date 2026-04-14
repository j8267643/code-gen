"""
Prompt Chaining - 提示链模式
Inspired by PraisonAI's Prompt Chaining

将复杂任务拆解为顺序执行的子任务链：
1. 每个步骤的输出作为下一步的输入
2. 支持条件分支和错误回滚
3. 上下文在链中传递
4. 支持并行步骤

适用于：多步骤代码生成、文档生成、数据处理流程
"""
from typing import Dict, Any, List, Optional, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime


class ChainStatus(Enum):
    """链执行状态"""
    PENDING = "pending"           # 待执行
    RUNNING = "running"           # 执行中
    COMPLETED = "completed"       # 完成
    FAILED = "failed"             # 失败
    SKIPPED = "skipped"           # 跳过


@dataclass
class ChainContext:
    """链上下文"""
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default=None):
        """获取数据"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置数据"""
        self.data[key] = value
    
    def update(self, other: Dict[str, Any]):
        """批量更新"""
        self.data.update(other)


@dataclass
class StepResult:
    """步骤执行结果"""
    success: bool
    output: Any
    step_name: str
    status: ChainStatus
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ChainResult:
    """链执行结果"""
    success: bool
    final_output: Any
    step_results: List[StepResult]
    context: ChainContext
    total_steps: int
    completed_steps: int
    failed_steps: int
    execution_time: float
    status: ChainStatus


class ChainStep(ABC):
    """链步骤基类"""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        condition: Optional[Callable[[ChainContext], bool]] = None,
        retries: int = 0
    ):
        self.name = name
        self.description = description
        self.condition = condition
        self.retries = retries
        self.next_steps: List['ChainStep'] = []
    
    @abstractmethod
    async def execute(self, context: ChainContext) -> Any:
        """执行步骤"""
        pass
    
    def should_execute(self, context: ChainContext) -> bool:
        """检查是否应该执行"""
        if self.condition:
            return self.condition(context)
        return True
    
    def then(self, step: 'ChainStep') -> 'ChainStep':
        """链式添加下一步"""
        self.next_steps.append(step)
        return step
    
    def __rshift__(self, other: 'ChainStep') -> 'ChainStep':
        """支持 >> 操作符"""
        return self.then(other)


class FunctionStep(ChainStep):
    """函数步骤"""
    
    def __init__(
        self,
        name: str,
        func: Callable[[ChainContext], Any],
        description: str = "",
        condition: Optional[Callable[[ChainContext], bool]] = None,
        retries: int = 0
    ):
        super().__init__(name, description, condition, retries)
        self.func = func
    
    async def execute(self, context: ChainContext) -> Any:
        """执行函数"""
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(context)
        return self.func(context)


class LLMStep(ChainStep):
    """LLM 调用步骤"""
    
    def __init__(
        self,
        name: str,
        prompt_template: str,
        agent=None,
        description: str = "",
        output_key: Optional[str] = None,
        condition: Optional[Callable[[ChainContext], bool]] = None
    ):
        super().__init__(name, description, condition)
        self.prompt_template = prompt_template
        self.agent = agent
        self.output_key = output_key or name
    
    async def execute(self, context: ChainContext) -> Any:
        """执行 LLM 调用"""
        # 格式化提示词
        prompt = self.prompt_template.format(**context.data)
        
        # 如果有 agent，使用 agent 执行
        if self.agent:
            # 简化处理，实际应该调用 agent
            result = f"[LLM Response for: {self.name}]"
        else:
            result = f"Processed: {prompt[:50]}..."
        
        # 存储结果到上下文
        context.set(self.output_key, result)
        
        return result


class ConditionalStep(ChainStep):
    """条件分支步骤"""
    
    def __init__(
        self,
        name: str,
        condition_func: Callable[[ChainContext], bool],
        true_step: ChainStep,
        false_step: Optional[ChainStep] = None,
        description: str = ""
    ):
        super().__init__(name, description, condition_func)
        self.true_step = true_step
        self.false_step = false_step
    
    async def execute(self, context: ChainContext) -> Any:
        """执行条件分支"""
        if self.condition(context):
            return await self.true_step.execute(context)
        elif self.false_step:
            return await self.false_step.execute(context)
        return None


class ParallelStep(ChainStep):
    """并行步骤"""
    
    def __init__(
        self,
        name: str,
        steps: List[ChainStep],
        description: str = "",
        aggregate_func: Optional[Callable[[List[Any]], Any]] = None
    ):
        super().__init__(name, description)
        self.steps = steps
        self.aggregate_func = aggregate_func
    
    async def execute(self, context: ChainContext) -> Any:
        """并行执行多个步骤"""
        # 创建独立的上下文副本
        tasks = []
        for step in self.steps:
            step_context = ChainContext(
                data=context.data.copy(),
                metadata=context.metadata.copy()
            )
            tasks.append(self._execute_step(step, step_context))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        valid_results = []
        for r in results:
            if isinstance(r, Exception):
                # 记录错误但继续
                continue
            valid_results.append(r)
        
        # 聚合结果
        if self.aggregate_func:
            return self.aggregate_func(valid_results)
        
        return valid_results
    
    async def _execute_step(self, step: ChainStep, context: ChainContext) -> Any:
        """执行单个步骤"""
        return await step.execute(context)


class PromptChain:
    """
    提示链
    
    管理链式任务执行
    """
    
    def __init__(self, name: str = "PromptChain"):
        self.name = name
        self.steps: List[ChainStep] = []
        self.error_handlers: Dict[str, Callable] = {}
        self.step_results: List[StepResult] = []
    
    def add(self, step: ChainStep) -> 'PromptChain':
        """添加步骤"""
        self.steps.append(step)
        return self
    
    def __rshift__(self, step: ChainStep) -> 'PromptChain':
        """支持 >> 操作符"""
        return self.add(step)
    
    async def execute(
        self,
        initial_context: Optional[Dict[str, Any]] = None,
        stop_on_error: bool = True
    ) -> ChainResult:
        """
        执行链
        
        Args:
            initial_context: 初始上下文
            stop_on_error: 出错时是否停止
            
        Returns:
            执行结果
        """
        start_time = asyncio.get_event_loop().time()
        context = ChainContext(data=initial_context or {})
        self.step_results = []
        
        completed = 0
        failed = 0
        
        for step in self.steps:
            step_start = asyncio.get_event_loop().time()
            
            # 检查是否应该执行
            if not step.should_execute(context):
                result = StepResult(
                    success=True,
                    output=None,
                    step_name=step.name,
                    status=ChainStatus.SKIPPED,
                    execution_time=0
                )
                self.step_results.append(result)
                continue
            
            # 执行步骤
            try:
                output = await step.execute(context)
                execution_time = asyncio.get_event_loop().time() - step_start
                
                result = StepResult(
                    success=True,
                    output=output,
                    step_name=step.name,
                    status=ChainStatus.COMPLETED,
                    execution_time=execution_time
                )
                completed += 1
                
                # 存储结果到上下文
                context.set(f"{step.name}_output", output)
                
            except Exception as e:
                execution_time = asyncio.get_event_loop().time() - step_start
                
                result = StepResult(
                    success=False,
                    output=None,
                    step_name=step.name,
                    status=ChainStatus.FAILED,
                    error=str(e),
                    execution_time=execution_time
                )
                failed += 1
                
                # 错误处理
                if step.name in self.error_handlers:
                    handler = self.error_handlers[step.name]
                    await handler(context, e)
                
                if stop_on_error:
                    break
            
            self.step_results.append(result)
        
        execution_time = asyncio.get_event_loop().time() - start_time
        success = failed == 0
        
        # 获取最终输出
        final_output = None
        if self.step_results:
            last_result = self.step_results[-1]
            if last_result.success:
                final_output = last_result.output
        
        return ChainResult(
            success=success,
            final_output=final_output,
            step_results=self.step_results,
            context=context,
            total_steps=len(self.steps),
            completed_steps=completed,
            failed_steps=failed,
            execution_time=execution_time,
            status=ChainStatus.COMPLETED if success else ChainStatus.FAILED
        )
    
    def on_error(self, step_name: str, handler: Callable):
        """设置错误处理器"""
        self.error_handlers[step_name] = handler
        return self
    
    def get_execution_report(self) -> str:
        """获取执行报告"""
        lines = ["="*60, f"Prompt Chain: {self.name}", "="*60, ""]
        
        for i, result in enumerate(self.step_results, 1):
            status_icon = "✅" if result.success else "❌"
            if result.status == ChainStatus.SKIPPED:
                status_icon = "⏭️"
            
            lines.append(f"{i}. {status_icon} {result.step_name}")
            lines.append(f"   状态: {result.status.value}")
            lines.append(f"   耗时: {result.execution_time:.2f}s")
            if result.error:
                lines.append(f"   错误: {result.error}")
            lines.append("")
        
        lines.append("="*60)
        return "\n".join(lines)


# ========== 预设链 ==========

class ChainPresets:
    """预设链"""
    
    @staticmethod
    def code_generation() -> PromptChain:
        """代码生成链"""
        chain = PromptChain("CodeGeneration")
        
        # 步骤1: 需求分析
        chain.add(LLMStep(
            name="analyze",
            prompt_template="分析以下需求，提取关键信息:\n{requirements}",
            output_key="analysis"
        ))
        
        # 步骤2: 设计
        chain.add(LLMStep(
            name="design",
            prompt_template="基于分析结果设计解决方案:\n{analysis}",
            output_key="design"
        ))
        
        # 步骤3: 编码
        chain.add(LLMStep(
            name="code",
            prompt_template="根据设计编写代码:\n{design}",
            output_key="code"
        ))
        
        # 步骤4: 测试
        chain.add(LLMStep(
            name="test",
            prompt_template="为以下代码编写测试:\n{code}",
            output_key="tests"
        ))
        
        return chain
    
    @staticmethod
    def document_generation() -> PromptChain:
        """文档生成链"""
        chain = PromptChain("DocumentGeneration")
        
        chain.add(LLMStep(
            name="outline",
            prompt_template="为以下主题创建大纲:\n{topic}",
            output_key="outline"
        ))
        
        chain.add(LLMStep(
            name="draft",
            prompt_template="基于大纲撰写初稿:\n{outline}",
            output_key="draft"
        ))
        
        chain.add(LLMStep(
            name="review",
            prompt_template="审查并改进以下文档:\n{draft}",
            output_key="final_doc"
        ))
        
        return chain
    
    @staticmethod
    def data_processing() -> PromptChain:
        """数据处理链"""
        chain = PromptChain("DataProcessing")
        
        chain.add(FunctionStep(
            name="extract",
            func=lambda ctx: f"Extracted from {ctx.get('source')}",
            description="数据提取"
        ))
        
        chain.add(FunctionStep(
            name="clean",
            func=lambda ctx: f"Cleaned: {ctx.get('extract_output')}",
            description="数据清洗"
        ))
        
        chain.add(FunctionStep(
            name="transform",
            func=lambda ctx: f"Transformed: {ctx.get('clean_output')}",
            description="数据转换"
        ))
        
        chain.add(FunctionStep(
            name="load",
            func=lambda ctx: f"Loaded: {ctx.get('transform_output')}",
            description="数据加载"
        ))
        
        return chain


# ========== 便捷函数 ==========

async def run_chain(
    steps: List[ChainStep],
    initial_context: Optional[Dict[str, Any]] = None,
    name: str = "Chain"
) -> ChainResult:
    """
    便捷函数：运行链
    
    Args:
        steps: 步骤列表
        initial_context: 初始上下文
        name: 链名称
        
    Returns:
        执行结果
    """
    chain = PromptChain(name)
    for step in steps:
        chain.add(step)
    
    return await chain.execute(initial_context)


def create_step(
    name: str,
    func: Callable,
    description: str = ""
) -> FunctionStep:
    """便捷函数：创建函数步骤"""
    return FunctionStep(name, func, description)


def create_llm_step(
    name: str,
    prompt_template: str,
    output_key: Optional[str] = None
) -> LLMStep:
    """便捷函数：创建 LLM 步骤"""
    return LLMStep(name, prompt_template, output_key=output_key)


def create_parallel_step(
    name: str,
    steps: List[ChainStep],
    aggregate_func: Optional[Callable[[List[Any]], Any]] = None
) -> ParallelStep:
    """便捷函数：创建并行步骤"""
    return ParallelStep(name, steps, aggregate_func=aggregate_func)
