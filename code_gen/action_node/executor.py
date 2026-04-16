"""Action Executor - 动作执行器"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from .node import ActionNode, NodeOutput, ActionStatus

logger = logging.getLogger(__name__)


class MockResponseGenerator:
    """模拟响应生成器
    
    基于输入参数生成模拟响应，用于测试
    """
    
    def __init__(self):
        self.mock_handlers: Dict[str, Callable] = {}
        self.default_handler = self._default_mock
    
    def register_handler(self, action_name: str, handler: Callable):
        """注册特定动作的模拟处理器"""
        self.mock_handlers[action_name] = handler
    
    def generate(self, action_name: str, inputs: Dict[str, Any], prompt: str) -> str:
        """生成模拟响应"""
        if action_name in self.mock_handlers:
            return self.mock_handlers[action_name](inputs, prompt)
        return self.default_handler(action_name, inputs, prompt)
    
    def _default_mock(self, action_name: str, inputs: Dict[str, Any], prompt: str) -> str:
        """默认模拟响应生成"""
        # 基于输入生成有意义的模拟响应
        input_summary = ", ".join([f"{k}={v}" for k, v in list(inputs.items())[:3]])
        return f"""{{
    "action": "{action_name}",
    "status": "success",
    "inputs": {{{input_summary}}},
    "result": "Simulated execution completed",
    "timestamp": "{datetime.now().isoformat()}"
}}"""


class ActionExecutor:
    """动作执行器
    
    负责执行 ActionNode
    """
    
    def __init__(self, llm_client=None, mock_generator: Optional[MockResponseGenerator] = None):
        # 验证 llm_client 有效性
        if llm_client is not None and not hasattr(llm_client, 'generate'):
            raise TypeError("llm_client must have 'generate' method")

        self.llm_client = llm_client
        self.mock_generator = mock_generator or MockResponseGenerator()
        self.execution_hooks: Dict[str, List[Callable]] = {
            "before": [],
            "after": [],
        }
    
    def register_hook(self, when: str, hook: Callable):
        """注册执行钩子"""
        if when in self.execution_hooks:
            self.execution_hooks[when].append(hook)
    
    async def execute(
        self,
        action: ActionNode,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> NodeOutput:
        """执行动作
        
        Args:
            action: 要执行的动作
            inputs: 输入数据
            context: 可选的上下文
        
        Returns:
            执行结果
        """
        action.status = ActionStatus.RUNNING
        
        # 执行 before 钩子
        for hook in self.execution_hooks["before"]:
            try:
                await hook(action, inputs)
            except Exception as e:
                logger.warning(f"Before hook failed for action '{action.name}': {e}", exc_info=True)
        
        try:
            # 验证输入
            is_valid, errors = action.validate_inputs(inputs)
            if not is_valid:
                action.status = ActionStatus.FAILED
                return NodeOutput(
                    content=None,
                    error=f"Input validation failed: {errors}",
                )
            
            # 预处理
            if action.pre_process:
                try:
                    inputs = action.pre_process(inputs) or inputs
                except Exception as e:
                    logger.warning(f"Pre-process failed for action '{action.name}': {e}", exc_info=True)
            
            # 构建提示
            prompt = action.build_prompt(inputs)
            
            # 执行（带重试）
            result = await self._execute_with_retry(action, prompt)
            
            # 后处理
            if action.post_process and result.is_success():
                try:
                    processed = action.post_process(result.parsed_data or result.content)
                    if processed:
                        result.parsed_data = processed if isinstance(processed, dict) else result.parsed_data
                except Exception as e:
                    logger.warning(f"Post-process failed for action '{action.name}': {e}", exc_info=True)
            
            # 更新状态
            action.status = ActionStatus.COMPLETED if result.is_success() else ActionStatus.FAILED
            
            # 执行 after 钩子
            for hook in self.execution_hooks["after"]:
                try:
                    await hook(action, result)
                except Exception as e:
                    logger.warning(f"After hook failed for action '{action.name}': {e}", exc_info=True)
            
            return result
            
        except Exception as e:
            action.status = ActionStatus.FAILED
            return NodeOutput(
                content=None,
                error=str(e),
            )
    
    async def _execute_with_retry(
        self,
        action: ActionNode,
        prompt: str,
    ) -> NodeOutput:
        """带重试的执行"""
        last_error = None
        
        for attempt in range(action.max_retries):
            try:
                start_time = time.time()
                
                # 调用 LLM
                if self.llm_client:
                    response = await self._call_llm(action, prompt)
                else:
                    # 模拟执行 - 使用模拟响应生成器
                    response = self.mock_generator.generate(action.name, action.input_data or {}, prompt)
                
                execution_time = time.time() - start_time
                
                # 解析输出
                parsed = action.parse_output(response)
                
                # 验证输出
                is_valid, errors = action.validate_outputs(parsed)
                if not is_valid:
                    raise ValueError(f"Output validation failed: {errors}")
                
                return NodeOutput(
                    content=response,
                    parsed_data=parsed,
                    execution_time=execution_time,
                    metadata={
                        "attempt": attempt + 1,
                        "action_name": action.name,
                    },
                )
                
            except Exception as e:
                last_error = str(e)
                action.status = ActionStatus.RETRYING
                
                if attempt < action.max_retries - 1:
                    await asyncio.sleep(action.retry_delay * (attempt + 1))
        
        return NodeOutput(
            content=None,
            error=f"Failed after {action.max_retries} attempts: {last_error}",
        )
    
    async def _call_llm(self, action: ActionNode, prompt: str) -> str:
        """调用 LLM"""
        if not self.llm_client:
            raise ValueError("No LLM client configured")
        
        # 构建消息
        messages = [{"role": "user", "content": prompt}]
        
        # 添加系统提示
        if action.system_prompt:
            messages.insert(0, {"role": "system", "content": action.system_prompt})
        
        # 调用 LLM
        response = await self.llm_client.send_message(
            messages=messages,
            model=action.model,
            temperature=action.temperature,
            max_tokens=action.max_tokens,
        )
        
        return response
    
    async def execute_batch(
        self,
        actions: list,
        inputs_list: list,
        max_concurrent: int = 3,
    ) -> list:
        """批量执行"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_limit(action, inputs):
            async with semaphore:
                return await self.execute(action, inputs)
        
        tasks = [
            execute_with_limit(action, inputs)
            for action, inputs in zip(actions, inputs_list)
        ]
        
        return await asyncio.gather(*tasks)


class ActionChain:
    """动作链
    
    将多个动作链接在一起执行
    """
    
    def __init__(self, executor: Optional[ActionExecutor] = None):
        self.executor = executor or ActionExecutor()
        self.actions: list = []
        self.transitions: Dict[int, Callable] = {}  # 状态转换函数
    
    def add_action(
        self,
        action: ActionNode,
        transition: Optional[Callable] = None,
    ) -> ActionChain:
        """添加动作"""
        self.actions.append(action)
        if transition:
            self.transitions[len(self.actions) - 1] = transition
        return self
    
    async def execute(
        self,
        initial_inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行动作链"""
        context = initial_inputs.copy()
        results = []
        
        for i, action in enumerate(self.actions):
            # 执行动作
            result = await self.executor.execute(action, context)
            results.append(result)
            
            if not result.is_success():
                return {
                    "success": False,
                    "error": result.error,
                    "step": i,
                    "results": results,
                }
            
            # 更新上下文
            if result.parsed_data:
                context.update(result.parsed_data)
            
            # 状态转换
            if i in self.transitions:
                transition_fn = self.transitions[i]
                try:
                    new_context = transition_fn(context, result)
                    if new_context:
                        context = new_context
                except Exception as e:
                    print(f"Transition failed at step {i}: {e}")
        
        return {
            "success": True,
            "results": results,
            "final_context": context,
        }


class ActionPipeline:
    """动作管道
    
    支持分支、并行、条件等复杂流程
    """
    
    def __init__(self, executor: Optional[ActionExecutor] = None):
        self.executor = executor or ActionExecutor()
        self.steps: List[Dict[str, Any]] = []
    
    def add_step(
        self,
        action: ActionNode,
        name: Optional[str] = None,
        condition: Optional[Callable] = None,
    ) -> ActionPipeline:
        """添加步骤"""
        self.steps.append({
            "action": action,
            "name": name or action.name,
            "condition": condition,
        })
        return self
    
    def add_parallel(
        self,
        actions: list,
        name: str = "parallel",
    ) -> ActionPipeline:
        """添加并行步骤"""
        self.steps.append({
            "type": "parallel",
            "actions": actions,
            "name": name,
        })
        return self
    
    def add_branch(
        self,
        condition: Callable,
        true_action: ActionNode,
        false_action: ActionNode,
        name: str = "branch",
    ) -> ActionPipeline:
        """添加分支"""
        self.steps.append({
            "type": "branch",
            "condition": condition,
            "true_action": true_action,
            "false_action": false_action,
            "name": name,
        })
        return self
    
    async def execute(self, initial_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行管道"""
        context = initial_inputs.copy()
        results = {}
        
        for step in self.steps:
            step_type = step.get("type", "sequential")
            
            if step_type == "sequential":
                # 检查条件
                if step.get("condition"):
                    if not step["condition"](context):
                        continue
                
                # 执行动作
                result = await self.executor.execute(step["action"], context)
                results[step["name"]] = result
                
                if result.is_success() and result.parsed_data:
                    context.update(result.parsed_data)
            
            elif step_type == "parallel":
                # 并行执行
                tasks = [
                    self.executor.execute(action, context)
                    for action in step["actions"]
                ]
                parallel_results = await asyncio.gather(*tasks)
                results[step["name"]] = parallel_results
            
            elif step_type == "branch":
                # 条件分支
                condition_result = step["condition"](context)
                action = step["true_action"] if condition_result else step["false_action"]
                result = await self.executor.execute(action, context)
                results[step["name"]] = result
                
                if result.is_success() and result.parsed_data:
                    context.update(result.parsed_data)
        
        return {
            "success": all(
                r.is_success() if isinstance(r, NodeOutput) else
                all(pr.is_success() for pr in r)
                for r in results.values()
            ),
            "results": results,
            "final_context": context,
        }
