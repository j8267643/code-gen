"""
Self-Reflection mechanism for Agents
Inspired by PraisonAI's ReflectAgent

自反思机制使 Agent 能够：
1. 评估自己的响应质量
2. 检查完整性和准确性
3. 通过迭代改进输出
4. 确保任务要求得到满足
"""
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import asyncio


class ReflectionStatus(str, Enum):
    """反思状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    NEEDS_IMPROVEMENT = "needs_improvement"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"


@dataclass
class ReflectionResult:
    """反思结果"""
    passed: bool
    score: float  # 0-100
    feedback: str
    suggestions: List[str] = field(default_factory=list)
    missing_aspects: List[str] = field(default_factory=list)
    quality_issues: List[str] = field(default_factory=list)
    iteration: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "feedback": self.feedback,
            "suggestions": self.suggestions,
            "missing_aspects": self.missing_aspects,
            "quality_issues": self.quality_issues,
            "iteration": self.iteration,
            "timestamp": self.timestamp
        }


@dataclass
class ReflectionConfig:
    """反思配置"""
    enabled: bool = True
    max_iterations: int = 3
    min_score: float = 80.0  # 最低通过分数
    reflection_prompt: Optional[str] = None
    auto_improve: bool = True  # 自动改进
    store_history: bool = True  # 存储反思历史
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "max_iterations": self.max_iterations,
            "min_score": self.min_score,
            "auto_improve": self.auto_improve,
            "store_history": self.store_history
        }


class SelfReflection:
    """
    自反思系统
    
    负责：
    1. 评估 Agent 输出质量
    2. 生成改进建议
    3. 管理迭代改进循环
    4. 记录反思历史
    """
    
    def __init__(self, config: ReflectionConfig = None):
        self.config = config or ReflectionConfig()
        self.reflection_history: List[ReflectionResult] = []
        self.current_iteration = 0
    
    async def reflect(
        self,
        original_task: str,
        agent_output: str,
        expected_output: str,
        call_ai_func: Callable,
        iteration: int = 1
    ) -> ReflectionResult:
        """
        对 Agent 输出进行反思评估
        
        Args:
            original_task: 原始任务描述
            agent_output: Agent 的输出
            expected_output: 期望的输出描述
            call_ai_func: 调用 AI 的函数
            iteration: 当前迭代次数
        
        Returns:
            ReflectionResult: 反思结果
        """
        if not self.config.enabled:
            return ReflectionResult(
                passed=True,
                score=100.0,
                feedback="Reflection disabled",
                iteration=iteration
            )
        
        self.current_iteration = iteration
        
        # 构建反思提示词
        reflection_prompt = self._build_reflection_prompt(
            original_task, agent_output, expected_output, iteration
        )
        
        # 调用 AI 进行评估（带超时控制）
        messages = [
            {"role": "system", "content": "You are a quality evaluator. Assess the output objectively."},
            {"role": "user", "content": reflection_prompt}
        ]
        
        try:
            response = await asyncio.wait_for(call_ai_func(messages), timeout=60.0)
        except asyncio.TimeoutError:
            return ReflectionResult(
                passed=False,
                score=0.0,
                feedback="Reflection timed out after 60 seconds",
                iteration=iteration
            )
        
        if not response.get("success"):
            return ReflectionResult(
                passed=False,
                score=0.0,
                feedback=f"Reflection failed: {response.get('error', 'Unknown error')}",
                iteration=iteration
            )
        
        # 解析反思结果
        result = self._parse_reflection_response(response.get("content", ""))
        result.iteration = iteration
        
        # 存储历史
        if self.config.store_history:
            self.reflection_history.append(result)
        
        return result
    
    def _build_reflection_prompt(
        self,
        task: str,
        output: str,
        expected: str,
        iteration: int
    ) -> str:
        """构建反思提示词"""
        custom_prompt = self.config.reflection_prompt or ""
        
        prompt = f"""请对以下 Agent 输出进行质量评估和反思分析。

## 原始任务
{task}

## 期望输出
{expected}

## Agent 实际输出
{output[:3000]}  # 限制长度避免超出上下文

## 评估要求
请从以下维度进行评估（每项 0-100 分）：

1. **完整性 (Completeness)** - 是否涵盖了任务的所有要求？
2. **准确性 (Accuracy)** - 内容是否正确无误？
3. **清晰度 (Clarity)** - 表达是否清晰易懂？
4. **实用性 (Usefulness)** - 输出是否具有实际价值？
5. **格式规范 (Format)** - 格式是否符合要求？

## 输出格式
请以 JSON 格式返回评估结果：

```json
{{
    "passed": true/false,  // 总分是否 >= {self.config.min_score}
    "score": 85,  // 总分 0-100
    "completeness": 90,
    "accuracy": 85,
    "clarity": 80,
    "usefulness": 90,
    "format": 85,
    "feedback": "总体评价...",
    "suggestions": ["改进建议1", "改进建议2"],
    "missing_aspects": ["遗漏点1", "遗漏点2"],
    "quality_issues": ["质量问题1", "质量问题2"]
}}
```

{custom_prompt}

当前是第 {iteration}/{self.config.max_iterations} 次迭代。"""
        
        return prompt
    
    def _parse_reflection_response(self, content: str) -> ReflectionResult:
        """解析 AI 的反思响应"""
        try:
            # 提取 JSON
            json_match = self._extract_json(content)
            if json_match:
                try:
                    data = json.loads(json_match)
                    
                    return ReflectionResult(
                        passed=data.get("passed", False),
                        score=float(data.get("score", 0)),
                        feedback=data.get("feedback", ""),
                        suggestions=data.get("suggestions", []),
                        missing_aspects=data.get("missing_aspects", []),
                        quality_issues=data.get("quality_issues", [])
                    )
                except json.JSONDecodeError as e:
                    # JSON 语法错误
                    return ReflectionResult(
                        passed=False,
                        score=0.0,
                        feedback=f"JSON syntax error: {str(e)[:100]}",
                        suggestions=["Please provide valid JSON with proper syntax"],
                        quality_issues=[f"JSON syntax error: {str(e)[:100]}"]
                    )
                except (ValueError, TypeError) as e:
                    # 数据类型错误
                    return ReflectionResult(
                        passed=False,
                        score=0.0,
                        feedback=f"JSON data error: {str(e)[:100]}",
                        suggestions=["Please check data types in JSON"],
                        quality_issues=[f"Data type error: {str(e)[:100]}"]
                    )
            else:
                # 未找到 JSON
                return ReflectionResult(
                    passed=False,
                    score=0.0,
                    feedback="No JSON found in response",
                    suggestions=["Please wrap your response in ```json ... ``` format"],
                    quality_issues=["Response does not contain valid JSON block"]
                )
        except Exception as e:
            # 其他异常（如 _extract_json 失败）
            return ReflectionResult(
                passed=False,
                score=0.0,
                feedback=f"Failed to extract JSON: {str(e)[:100]}",
                suggestions=["Please check your response format"],
                quality_issues=[f"Extraction error: {str(e)[:100]}"]
            )
    
    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取 JSON"""
        # 尝试找 ```json 代码块
        import re
        
        json_block = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_block:
            return json_block.group(1)
        
        # 尝试找 ``` 代码块
        json_block = re.search(r'```\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_block:
            return json_block.group(1)
        
        # 尝试找 {} 包裹的内容
        json_match = re.search(r'(\{.*\})', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        return None
    
    async def improve(
        self,
        original_task: str,
        current_output: str,
        reflection: ReflectionResult,
        call_ai_func: Callable
    ) -> str:
        """
        基于反思结果改进输出
        
        Args:
            original_task: 原始任务
            current_output: 当前输出
            reflection: 反思结果
            call_ai_func: 调用 AI 的函数
        
        Returns:
            str: 改进后的输出
        """
        if not self.config.auto_improve:
            return current_output
        
        improvement_prompt = f"""请基于以下反思反馈改进你的输出。

## 原始任务
{original_task}

## 当前输出
{current_output[:2000]}

## 反思反馈
- 总分: {reflection.score}/100
- 评价: {reflection.feedback}

## 需要改进的方面
{chr(10).join(f"- {s}" for s in reflection.suggestions)}

## 遗漏的内容
{chr(10).join(f"- {m}" for m in reflection.missing_aspects)}

## 质量问题
{chr(10).join(f"- {q}" for q in reflection.quality_issues)}

请输出改进后的完整内容，确保解决上述所有问题。"""
        
        messages = [
            {"role": "system", "content": "You are improving your previous response based on feedback."},
            {"role": "user", "content": improvement_prompt}
        ]
        
        try:
            response = await asyncio.wait_for(call_ai_func(messages), timeout=120.0)
            if response.get("success"):
                return response.get("content", current_output)
        except asyncio.TimeoutError:
            print("  ⚠️ 改进过程超时，使用原始输出")
        
        return current_output
    
    async def execute_with_reflection(
        self,
        original_task: str,
        expected_output: str,
        initial_output: str,
        call_ai_func: Callable
    ) -> Dict[str, Any]:
        """
        执行带自反思的完整流程
        
        Args:
            original_task: 原始任务
            expected_output: 期望输出
            initial_output: 初始输出
            call_ai_func: 调用 AI 的函数
        
        Returns:
            Dict with final_output, reflection_history, iterations
        """
        current_output = initial_output
        reflections = []
        
        for iteration in range(1, self.config.max_iterations + 1):
            # 进行反思
            reflection = await self.reflect(
                original_task=original_task,
                agent_output=current_output,
                expected_output=expected_output,
                call_ai_func=call_ai_func,
                iteration=iteration
            )
            
            reflections.append(reflection)
            
            # 检查是否通过
            if reflection.passed and reflection.score >= self.config.min_score:
                return {
                    "success": True,
                    "final_output": current_output,
                    "reflections": [r.to_dict() for r in reflections],
                    "iterations": iteration,
                    "status": ReflectionStatus.PASSED
                }
            
            # 如果还有迭代次数，进行改进
            if iteration < self.config.max_iterations:
                current_output = await self.improve(
                    original_task=original_task,
                    current_output=current_output,
                    reflection=reflection,
                    call_ai_func=call_ai_func
                )
        
        # 达到最大迭代次数
        return {
            "success": reflection.passed if reflections else False,
            "final_output": current_output,
            "reflections": [r.to_dict() for r in reflections],
            "iterations": len(reflections),
            "status": ReflectionStatus.MAX_ITERATIONS_REACHED
        }
    
    def get_reflection_summary(self) -> str:
        """获取反思历史摘要"""
        if not self.reflection_history:
            return "No reflection history"
        
        lines = ["## Reflection History", ""]
        
        for r in self.reflection_history:
            status = "✅" if r.passed else "❌"
            lines.append(f"{status} Iteration {r.iteration}: Score {r.score}/100")
            lines.append(f"   Feedback: {r.feedback[:100]}...")
            if r.suggestions:
                lines.append(f"   Suggestions: {', '.join(r.suggestions[:3])}")
            lines.append("")
        
        return "\n".join(lines)


class ReflectAgentMixin:
    """
    自反思 Agent Mixin
    
    可以混入到任何 Agent 类中，添加自反思能力
    """
    
    def __init__(self, *args, reflection_config: ReflectionConfig = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.reflection = SelfReflection(reflection_config or ReflectionConfig())
        self.enable_reflection = True
    
    async def execute_with_self_reflection(
        self,
        task: str,
        expected_output: str,
        execute_func: Callable,
        call_ai_func: Callable
    ) -> Dict[str, Any]:
        """
        执行带自反思的任务
        
        Args:
            task: 任务描述
            expected_output: 期望输出
            execute_func: 执行任务的函数
            call_ai_func: 调用 AI 的函数
        
        Returns:
            包含最终输出和反思历史的字典
        """
        if not self.enable_reflection:
            # 直接执行，不反思
            result = await execute_func()
            return {
                "success": True,
                "final_output": result,
                "reflections": [],
                "iterations": 1,
                "status": "reflection_disabled"
            }
        
        # 执行初始任务
        initial_output = await execute_func()
        
        # 进行自反思改进
        result = await self.reflection.execute_with_reflection(
            original_task=task,
            expected_output=expected_output,
            initial_output=initial_output,
            call_ai_func=call_ai_func
        )
        
        return result
