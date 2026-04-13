"""
Reflective Agent Executor - 支持自反思的执行器
Inspired by PraisonAI's ReflectAgent

在标准执行器基础上添加：
1. 执行后自动反思
2. 质量评估
3. 迭代改进
4. 反思历史记录
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import json

from .executor import AgentExecutor
from .reflection import SelfReflection, ReflectionConfig, ReflectionResult
from .agent import Agent


class ReflectiveAgentExecutor(AgentExecutor):
    """
    支持自反思的 Agent 执行器
    
    特性：
    - 自动评估输出质量
    - 多轮迭代改进
    - 可配置的反思策略
    - 详细的反思报告
    """
    
    def __init__(
        self,
        work_dir: Path,
        model: str = None,
        reflection_config: ReflectionConfig = None
    ):
        super().__init__(work_dir, model)
        self.reflection = SelfReflection(reflection_config or ReflectionConfig())
        self.reflection_enabled = True
    
    async def execute(
        self,
        agent: Agent,
        system_prompt: str,
        user_prompt: str,
        tools: List[Dict] = None,
        expected_output: str = None,
        enable_reflection: bool = None
    ) -> Dict[str, Any]:
        """
        执行 Agent 任务（带自反思）
        
        Args:
            agent: 执行的 Agent
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            tools: 可用工具
            expected_output: 期望的输出描述（用于反思）
            enable_reflection: 是否启用反思（覆盖默认设置）
        
        Returns:
            {
                "success": bool,
                "output": str,
                "error": str,
                "reflections": List[Dict],  # 反思历史
                "iterations": int,  # 迭代次数
                "final_score": float,  # 最终分数
            }
        """
        # 确定是否启用反思
        should_reflect = enable_reflection if enable_reflection is not None else self.reflection_enabled
        
        # 先执行标准任务
        base_result = await super().execute(agent, system_prompt, user_prompt, tools)
        
        if not should_reflect or not base_result.get("success"):
            # 不反思或执行失败，直接返回
            return {
                **base_result,
                "reflections": [],
                "iterations": 1,
                "final_score": 100.0 if base_result.get("success") else 0.0,
                "reflection_enabled": should_reflect
            }
        
        # 准备反思
        original_task = user_prompt
        expected = expected_output or f"高质量完成以下任务: {user_prompt[:100]}"
        initial_output = base_result.get("output", "")
        
        # 执行自反思流程
        reflection_result = await self.reflection.execute_with_reflection(
            original_task=original_task,
            expected_output=expected,
            initial_output=initial_output,
            call_ai_func=self._call_ai
        )
        
        # 构建最终响应
        final_result = {
            "success": reflection_result["success"],
            "output": reflection_result["final_output"],
            "error": base_result.get("error", ""),
            "reflections": reflection_result["reflections"],
            "iterations": reflection_result["iterations"],
            "final_score": reflection_result["reflections"][-1]["score"] if reflection_result["reflections"] else 100.0,
            "reflection_enabled": True,
            "status": reflection_result["status"]
        }
        
        # 记录到执行历史
        self.execution_history.append({
            "agent": agent.name,
            "task": user_prompt[:100],
            "output": final_result["output"][:200],
            "iterations": final_result["iterations"],
            "score": final_result["final_score"],
            "timestamp": datetime.now().isoformat()
        })
        
        return final_result
    
    async def reflect_only(
        self,
        task: str,
        output: str,
        expected_output: str = None
    ) -> ReflectionResult:
        """
        仅对已有输出进行反思（不执行新任务）
        
        Args:
            task: 原始任务
            output: 需要评估的输出
            expected_output: 期望的输出
        
        Returns:
            ReflectionResult: 反思结果
        """
        expected = expected_output or f"高质量完成: {task[:100]}"
        
        return await self.reflection.reflect(
            original_task=task,
            agent_output=output,
            expected_output=expected,
            call_ai_func=self._call_ai,
            iteration=1
        )
    
    def get_reflection_report(self) -> str:
        """获取反思系统报告"""
        return self.reflection.get_reflection_summary()
    
    def configure_reflection(self, config: ReflectionConfig):
        """配置反思参数"""
        self.reflection.config = config
    
    def enable_self_reflection(self) -> None:
        """启用自反思"""
        self.reflection_enabled = True
        self.reflection.config.enabled = True
        return None
    
    def disable_self_reflection(self) -> None:
        """禁用自反思"""
        self.reflection_enabled = False
        self.reflection.config.enabled = False
        return None


class ReflectiveTaskExecutor:
    """
    支持自反思的任务执行器
    
    用于在任务级别进行反思
    """
    
    def __init__(self, base_executor: AgentExecutor, reflection_config: ReflectionConfig = None):
        self.base_executor = base_executor
        self.reflection = SelfReflection(reflection_config or ReflectionConfig())
    
    async def execute_task_with_reflection(
        self,
        task_name: str,
        task_description: str,
        agent: Agent,
        system_prompt: str,
        execute_func: callable
    ) -> Dict[str, Any]:
        """
        执行任务并进行反思
        
        Args:
            task_name: 任务名称
            task_description: 任务描述
            agent: 执行 Agent
            system_prompt: 系统提示词
            execute_func: 执行函数
        
        Returns:
            包含反思结果的字典
        """
        # 执行任务
        try:
            initial_output = await execute_func()
            success = True
            error = ""
        except Exception as e:
            initial_output = ""
            success = False
            error = str(e)
        
        if not success:
            return {
                "success": False,
                "output": "",
                "error": error,
                "reflections": [],
                "iterations": 0
            }
        
        # 进行反思改进
        result = await self.reflection.execute_with_reflection(
            original_task=task_description,
            expected_output=f"完成: {task_description}",
            initial_output=initial_output,
            call_ai_func=self.base_executor._call_ai
        )
        
        return {
            "success": result["success"],
            "output": result["final_output"],
            "error": error,
            "reflections": result["reflections"],
            "iterations": result["iterations"],
            "task_name": task_name
        }


# 便捷的反思配置预设
class ReflectionPresets:
    """反思配置预设"""
    
    @staticmethod
    def strict() -> ReflectionConfig:
        """严格模式 - 高质量要求"""
        return ReflectionConfig(
            enabled=True,
            max_iterations=5,
            min_score=90.0,
            auto_improve=True,
            store_history=True
        )
    
    @staticmethod
    def balanced() -> ReflectionConfig:
        """平衡模式 - 默认配置"""
        return ReflectionConfig(
            enabled=True,
            max_iterations=3,
            min_score=80.0,
            auto_improve=True,
            store_history=True
        )
    
    @staticmethod
    def fast() -> ReflectionConfig:
        """快速模式 - 最少反思"""
        return ReflectionConfig(
            enabled=True,
            max_iterations=2,
            min_score=70.0,
            auto_improve=True,
            store_history=False
        )
    
    @staticmethod
    def disabled() -> ReflectionConfig:
        """禁用反思"""
        return ReflectionConfig(
            enabled=False,
            max_iterations=1,
            min_score=0.0,
            auto_improve=False,
            store_history=False
        )
