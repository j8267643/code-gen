"""SOP Executor - SOP 执行器"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import traceback

from .sop import SOP, SOPStep, SOPContext, StepStatus, StepType


class SOPExecutionError(Exception):
    """SOP 执行错误"""
    pass


class StepExecutionError(Exception):
    """步骤执行错误"""
    pass


class SOPExecutor:
    """SOP 执行器
    
    负责执行 SOP 定义的流程
    """
    
    def __init__(self):
        self.action_handlers: Dict[str, Callable] = {}
        self.step_hooks: Dict[str, List[Callable]] = {
            "before": [],
            "after": [],
        }
    
    def register_action(self, name: str, handler: Callable):
        """注册动作处理器"""
        self.action_handlers[name] = handler
    
    def register_step_hook(self, when: str, hook: Callable):
        """注册步骤钩子
        
        Args:
            when: "before" 或 "after"
            hook: 钩子函数
        """
        if when in self.step_hooks:
            self.step_hooks[when].append(hook)
    
    async def execute(
        self,
        sop: SOP,
        context: SOPContext,
        action_handlers: Optional[Dict[str, Callable]] = None,
    ) -> SOPContext:
        """执行 SOP
        
        Args:
            sop: SOP 定义
            context: 执行上下文
            action_handlers: 可选的动作处理器覆盖
        
        Returns:
            执行后的上下文
        """
        handlers = action_handlers or self.action_handlers
        
        # 验证 SOP
        errors = sop.validate()
        if errors:
            raise SOPExecutionError(f"SOP validation failed: {errors}")
        
        # 获取执行顺序
        execution_layers = sop.get_execution_order()
        
        context.started_at = datetime.now()
        
        try:
            for layer in execution_layers:
                # 检查是否需要并行执行
                steps = [sop.get_step(name) for name in layer]
                steps = [s for s in steps if s]
                
                if len(steps) == 1:
                    # 单步骤顺序执行
                    await self._execute_step(steps[0], context, handlers)
                else:
                    # 多步骤并行执行
                    await self._execute_parallel(steps, context, handlers, sop.max_concurrent_steps)
                
                # 检查是否快速失败
                if sop.fail_fast and context.failed_steps:
                    raise SOPExecutionError(
                        f"SOP execution failed at steps: {context.failed_steps}"
                    )
            
            context.completed_at = datetime.now()
            return context
            
        except Exception as e:
            context.completed_at = datetime.now()
            raise SOPExecutionError(f"SOP execution failed: {e}") from e
    
    async def _execute_step(
        self,
        step: SOPStep,
        context: SOPContext,
        handlers: Dict[str, Callable],
    ) -> Any:
        """执行单个步骤"""
        context.current_step = step.name
        step.status = StepStatus.RUNNING
        
        # 执行 before 钩子
        for hook in self.step_hooks["before"]:
            try:
                await hook(step, context)
            except Exception as e:
                print(f"Before hook failed for step {step.name}: {e}")
        
        try:
            # 获取动作处理器
            handler = handlers.get(step.action)
            if not handler:
                raise StepExecutionError(f"No handler registered for action: {step.action}")
            
            # 准备输入
            step_input = self._prepare_step_input(step, context)
            
            # 执行动作（带重试）
            output = await self._execute_with_retry(
                handler,
                step_input,
                step,
                context,
            )
            
            # 保存输出
            context.set_step_output(step.name, output)
            step.status = StepStatus.COMPLETED
            context.add_execution_record(step.name, "completed", output)
            
        except Exception as e:
            step.status = StepStatus.FAILED
            context.failed_steps.append(step.name)
            context.add_execution_record(step.name, "failed", error=str(e))
            
            if step.step_type != StepType.CONDITIONAL:
                raise StepExecutionError(
                    f"Step '{step.name}' failed: {e}"
                ) from e
        
        finally:
            # 执行 after 钩子
            for hook in self.step_hooks["after"]:
                try:
                    await hook(step, context)
                except Exception as e:
                    print(f"After hook failed for step {step.name}: {e}")
        
        return context.get_step_output(step.name)
    
    async def _execute_parallel(
        self,
        steps: List[SOPStep],
        context: SOPContext,
        handlers: Dict[str, Callable],
        max_concurrent: int,
    ):
        """并行执行多个步骤"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(step: SOPStep):
            async with semaphore:
                return await self._execute_step(step, context, handlers)
        
        # 创建任务
        tasks = [execute_with_semaphore(step) for step in steps]
        
        # 等待所有完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查错误
        for step, result in zip(steps, results):
            if isinstance(result, Exception):
                print(f"Parallel step '{step.name}' failed: {result}")
    
    async def _execute_with_retry(
        self,
        handler: Callable,
        input_data: Any,
        step: SOPStep,
        context: SOPContext,
    ) -> Any:
        """带重试的执行"""
        last_error = None
        
        for attempt in range(step.max_retries):
            try:
                # 设置超时
                if step.timeout:
                    return await asyncio.wait_for(
                        handler(input_data, context),
                        timeout=step.timeout,
                    )
                else:
                    return await handler(input_data, context)
                    
            except asyncio.TimeoutError:
                last_error = f"Timeout after {step.timeout}s"
                if attempt < step.max_retries - 1:
                    await asyncio.sleep(step.retry_delay * (attempt + 1))
                    
            except Exception as e:
                last_error = str(e)
                if attempt < step.max_retries - 1:
                    await asyncio.sleep(step.retry_delay * (attempt + 1))
        
        raise StepExecutionError(
            f"Step failed after {step.max_retries} attempts: {last_error}"
        )
    
    def _prepare_step_input(self, step: SOPStep, context: SOPContext) -> Dict[str, Any]:
        """准备步骤输入"""
        input_data = {
            "step_name": step.name,
            "step_description": step.description,
            "role": step.role,
            "context": context.to_dict(),
        }
        
        # 添加依赖步骤的输出
        for dep_name in step.depends_on:
            dep_output = context.get_step_output(dep_name)
            if dep_output is not None:
                input_data[f"dep_{dep_name}"] = dep_output
        
        # 添加全局输入
        input_data.update(context.inputs)
        
        return input_data
    
    def get_execution_report(self, context: SOPContext) -> Dict[str, Any]:
        """生成执行报告"""
        total_steps = len(context.completed_steps) + len(context.failed_steps)
        success_rate = len(context.completed_steps) / total_steps if total_steps > 0 else 0
        
        duration = None
        if context.started_at and context.completed_at:
            duration = (context.completed_at - context.started_at).total_seconds()
        
        return {
            "sop_name": context.sop_name,
            "sop_id": context.sop_id,
            "status": "completed" if not context.failed_steps else "failed",
            "total_steps": total_steps,
            "completed_steps": len(context.completed_steps),
            "failed_steps": len(context.failed_steps),
            "success_rate": success_rate,
            "duration_seconds": duration,
            "started_at": context.started_at.isoformat() if context.started_at else None,
            "completed_at": context.completed_at.isoformat() if context.completed_at else None,
            "execution_history": context.execution_history,
        }
