"""
Enhanced Reflective Agent Executor
支持工具调用和自反思的增强版执行器

结合：
1. 工具调用能力（来自 EnhancedAgentExecutor）
2. 自反思机制（来自 ReflectiveAgentExecutor）
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import re
import asyncio

from .enhanced_executor import EnhancedAgentExecutor
from .reflection import SelfReflection, ReflectionConfig
from .reflect_executor import ReflectionPresets
from .agent import Agent
from .tool_registry import get_tool_registry


class EnhancedReflectiveExecutor(EnhancedAgentExecutor):
    """
    增强的反思执行器
    
    特性：
    1. 工具调用支持
    2. 自反思机制
    3. 迭代改进
    4. 质量评估
    """
    
    def __init__(
        self,
        work_dir: Path,
        model: str = None,
        reflection_config: ReflectionConfig = None
    ):
        super().__init__(work_dir, model)
        self.reflection = SelfReflection(
            reflection_config if reflection_config is not None else ReflectionPresets.balanced()
        )
        self.reflection_enabled = True
    
    async def execute(
        self,
        agent: Agent,
        system_prompt: str,
        user_prompt: str,
        tools: List[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行任务（带工具调用和自反思）
        
        Args:
            agent: 执行的 Agent
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            tools: 可用工具
            **kwargs: 额外参数，包括:
                - expected_output: 期望的输出描述
                - enable_reflection: 是否启用反思
        
        Returns:
            包含输出、工具调用和反思结果的字典
        """
        # 从 kwargs 中提取反射相关参数
        expected_output = kwargs.get('expected_output')
        enable_reflection = kwargs.get('enable_reflection')
        
        # 确定是否启用反思
        should_reflect = enable_reflection if enable_reflection is not None else self.reflection_enabled
        
        # 第一步：执行标准任务（带工具调用）
        print(f"📝 [{agent.name}] 开始执行任务...")
        base_result = await super().execute(agent, system_prompt, user_prompt, tools, **kwargs)
        
        if not base_result.get("success"):
            print(f"   ❌ 任务执行失败")
            return {
                **base_result,
                "tool_calls": base_result.get("tool_calls", []),  # 确保工具调用历史被保留
                "reflections": [],
                "iterations": 1,
                "final_score": 0.0,
                "reflection_enabled": should_reflect
            }
        
        print(f"   ✅ 初始执行完成")
        
        # 如果不启用反思，直接返回
        if not should_reflect:
            print(f"   ℹ️ 自反思已禁用")
            return {
                **base_result,
                "reflections": [],
                "iterations": 1,
                "final_score": 100.0,
                "reflection_enabled": False
            }
        
        # 第二步：自反思和迭代改进
        print(f"🔍 [{agent.name}] 开始自反思...")
        
        original_task = user_prompt
        expected = expected_output or f"高质量完成: {user_prompt[:100]}"
        initial_output = base_result.get("output", "")
        
        # 添加超时控制（5分钟）
        try:
            reflection_result = await asyncio.wait_for(
                self.reflection.execute_with_reflection(
                    original_task=original_task,
                    expected_output=expected,
                    initial_output=initial_output,
                    call_ai_func=self._call_ai
                ),
                timeout=300.0  # 5分钟超时
            )
        except asyncio.TimeoutError:
            print(f"   ⚠️ 自反思超时（超过5分钟），使用初始输出")
            reflection_result = {
                "success": True,
                "final_output": initial_output,
                "reflections": [],
                "iterations": 1,
                "status": "timeout"
            }
        
        # 构建最终结果
        final_result = {
            "success": reflection_result["success"],
            "output": reflection_result["final_output"],
            "error": base_result.get("error", ""),
            "tool_calls": base_result.get("tool_calls", []),
            "reflections": reflection_result["reflections"],
            "iterations": reflection_result["iterations"],
            "final_score": reflection_result["reflections"][-1]["score"] if reflection_result["reflections"] else 100.0,
            "reflection_enabled": True,
            "status": reflection_result["status"]
        }
        
        # 输出反思摘要
        self._print_reflection_summary(final_result)
        
        return final_result
    
    def _print_reflection_summary(self, result: Dict[str, Any]):
        """打印反思摘要"""
        reflections = result.get("reflections", [])
        iterations = result.get("iterations", 1)
        score = result.get("final_score", 0)
        
        print(f"\n📊 反思摘要:")
        print(f"   迭代次数: {iterations}")
        print(f"   最终评分: {score:.1f}/100")
        
        if reflections:
            for i, r in enumerate(reflections, 1):
                status = "✅" if r.get("passed") else "❌"
                print(f"   {status} 第{i}轮: {r.get('score', 0):.1f}分 - {r.get('feedback', '')[:50]}...")
        
        if result.get("status") == "max_iterations_reached":
            print(f"   ⚠️ 达到最大迭代次数")
        
        print()
    
    def set_reflection_preset(self, preset: str):
        """
        设置反思预设模式
        
        Args:
            preset: "strict", "balanced", "fast", "disabled"
        """
        presets = {
            "strict": ReflectionPresets.strict(),
            "balanced": ReflectionPresets.balanced(),
            "fast": ReflectionPresets.fast(),
            "disabled": ReflectionPresets.disabled()
        }
        
        config = presets.get(preset, ReflectionPresets.balanced())
        self.reflection.config = config
        self.reflection_enabled = config.enabled
        
        print(f"🔧 反思模式设置为: {preset}")
    
    def enable_reflection(self) -> None:
        """启用自反思"""
        self.reflection_enabled = True
        self.reflection.config.enabled = True
        print("✅ 自反思已启用")
        return None
    
    def disable_reflection(self) -> None:
        """禁用自反思"""
        self.reflection_enabled = False
        self.reflection.config.enabled = False
        print("ℹ️ 自反思已禁用")
        return None
    
    def get_reflection_report(self) -> str:
        """获取反思报告"""
        return self.reflection.get_reflection_summary()


class ReflectiveEnhancedExecutor(EnhancedReflectiveExecutor):
    """
    别名类，与 EnhancedReflectiveExecutor 相同
    为了向后兼容
    """
    pass
