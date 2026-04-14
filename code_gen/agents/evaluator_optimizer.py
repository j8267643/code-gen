"""
Evaluator-Optimizer Pattern - 评估者-优化者模式
Inspired by PraisonAI's Evaluator-Optimizer

通过评估反馈持续优化 Agent 输出，实现自我迭代：
1. 生成器生成初始解决方案
2. 评估器评估质量并提供反馈
3. 根据反馈优化并重新生成
4. 循环直到达标或达到最大迭代次数

适用于：代码生成优化、内容质量提升、方案迭代优化
"""
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from datetime import datetime


class OptimizationStatus(Enum):
    """优化状态"""
    PENDING = "pending"           # 待优化
    OPTIMIZING = "optimizing"     # 优化中
    COMPLETED = "completed"       # 完成
    FAILED = "failed"             # 失败
    MAX_ITERATIONS = "max_iterations"  # 达到最大迭代次数


@dataclass
class EvaluationResult:
    """评估结果"""
    score: float                  # 评分 (0-1)
    passed: bool                  # 是否通过
    feedback: str                 # 反馈内容
    suggestions: List[str] = field(default_factory=list)  # 改进建议
    metrics: Dict[str, float] = field(default_factory=dict)  # 详细指标
    
    def __post_init__(self):
        if not 0 <= self.score <= 1:
            raise ValueError("Score must be between 0 and 1")


@dataclass
class OptimizationIteration:
    """优化迭代记录"""
    iteration: int                # 迭代次数
    solution: str                 # 解决方案
    evaluation: EvaluationResult  # 评估结果
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class OptimizationResult:
    """优化最终结果"""
    success: bool                 # 是否成功
    final_solution: str           # 最终解决方案
    iterations: List[OptimizationIteration]  # 迭代历史
    total_iterations: int         # 总迭代次数
    final_score: float            # 最终评分
    status: OptimizationStatus    # 状态
    execution_time: float         # 执行时间（秒）
    
    def __post_init__(self):
        if self.iterations:
            self.total_iterations = len(self.iterations)
            self.final_score = self.iterations[-1].evaluation.score


class BaseGenerator:
    """生成器基类"""
    
    def __init__(self, name: str = "Generator"):
        self.name = name
    
    async def generate(
        self, 
        task: str, 
        context: Optional[Dict] = None,
        feedback: Optional[str] = None
    ) -> str:
        """
        生成解决方案
        
        Args:
            task: 任务描述
            context: 上下文信息
            feedback: 上一次的反馈（用于优化）
            
        Returns:
            生成的解决方案
        """
        raise NotImplementedError


class BaseEvaluator:
    """评估器基类"""
    
    def __init__(self, name: str = "Evaluator"):
        self.name = name
    
    async def evaluate(
        self, 
        solution: str, 
        task: str,
        criteria: Optional[List[str]] = None
    ) -> EvaluationResult:
        """
        评估解决方案
        
        Args:
            solution: 待评估的解决方案
            task: 原始任务
            criteria: 评估标准
            
        Returns:
            评估结果
        """
        raise NotImplementedError


class LLMGenerator(BaseGenerator):
    """基于 LLM 的生成器"""
    
    def __init__(self, agent=None, name: str = "LLMGenerator"):
        super().__init__(name)
        self.agent = agent
    
    async def generate(
        self, 
        task: str, 
        context: Optional[Dict] = None,
        feedback: Optional[str] = None
    ) -> str:
        """使用 LLM 生成解决方案"""
        # 构建提示词
        prompt = f"任务: {task}\n\n"
        
        if context:
            prompt += f"上下文: {context}\n\n"
        
        if feedback:
            prompt += f"根据以下反馈进行改进:\n{feedback}\n\n"
            prompt += "请生成改进后的解决方案:"
        else:
            prompt += "请生成解决方案:"
        
        # 如果有 agent，使用 agent 执行
        if self.agent:
            # 这里简化处理，实际应该调用 agent
            return f"[Generated solution for: {task}]"
        
        return f"Solution for: {task}"


class LLMEvaluator(BaseEvaluator):
    """基于 LLM 的评估器"""
    
    def __init__(self, agent=None, name: str = "LLMEvaluator"):
        super().__init__(name)
        self.agent = agent
        self.pass_threshold = 0.8
    
    async def evaluate(
        self, 
        solution: str, 
        task: str,
        criteria: Optional[List[str]] = None
    ) -> EvaluationResult:
        """使用 LLM 评估解决方案"""
        # 这里简化处理，实际应该调用 agent 进行评估
        # 模拟评估结果
        
        # 简单的启发式评估
        score = self._heuristic_evaluate(solution, task)
        passed = score >= self.pass_threshold
        
        feedback = self._generate_feedback(solution, task, score, passed)
        suggestions = self._generate_suggestions(solution, task, score)
        
        return EvaluationResult(
            score=score,
            passed=passed,
            feedback=feedback,
            suggestions=suggestions,
            metrics={
                "completeness": min(1.0, len(solution) / 500),
                "relevance": score,
                "quality": score * 0.9
            }
        )
    
    def _heuristic_evaluate(self, solution: str, task: str) -> float:
        """启发式评估（简化版）"""
        # 基于长度和关键词的简单评估
        score = 0.5
        
        # 长度检查
        if len(solution) > 100:
            score += 0.1
        if len(solution) > 300:
            score += 0.1
        
        # 关键词检查
        task_keywords = set(task.lower().split())
        solution_keywords = set(solution.lower().split())
        if task_keywords & solution_keywords:
            score += 0.2
        
        # 结构检查
        if "```" in solution or "#" in solution:
            score += 0.1
        
        return min(1.0, score)
    
    def _generate_feedback(self, solution: str, task: str, score: float, passed: bool) -> str:
        """生成反馈"""
        if passed:
            return f"解决方案质量良好 (评分: {score:.2f})，满足要求。"
        else:
            return f"解决方案需要改进 (评分: {score:.2f})。建议增加更多细节和完整性。"
    
    def _generate_suggestions(self, solution: str, task: str, score: float) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if len(solution) < 200:
            suggestions.append("增加更多详细内容和解释")
        
        if "example" not in solution.lower():
            suggestions.append("添加具体示例说明")
        
        if score < 0.6:
            suggestions.append("重新审视任务要求，确保覆盖所有要点")
        
        return suggestions


class CodeEvaluator(BaseEvaluator):
    """代码专用评估器"""
    
    def __init__(self, name: str = "CodeEvaluator"):
        super().__init__(name)
        self.pass_threshold = 0.85
    
    async def evaluate(
        self, 
        solution: str, 
        task: str,
        criteria: Optional[List[str]] = None
    ) -> EvaluationResult:
        """评估代码质量"""
        import ast
        
        score = 0.5
        suggestions = []
        
        # 提取代码
        code = self._extract_code(solution)
        
        # 语法检查
        try:
            ast.parse(code)
            score += 0.2
        except SyntaxError as e:
            suggestions.append(f"语法错误: {e.msg}")
            score -= 0.3
        
        # 代码长度
        lines = code.strip().split('\n')
        if len(lines) > 5:
            score += 0.1
        
        # 注释检查
        if '#' in code or '"""' in code:
            score += 0.1
        
        # 函数定义检查
        if 'def ' in code:
            score += 0.1
        
        # 安全检查
        dangerous = ['eval(', 'exec(', 'os.system', 'subprocess']
        for d in dangerous:
            if d in code:
                score -= 0.2
                suggestions.append(f"发现潜在危险函数: {d}")
        
        score = max(0.0, min(1.0, score))
        passed = score >= self.pass_threshold
        
        return EvaluationResult(
            score=score,
            passed=passed,
            feedback=f"代码质量评分: {score:.2f}",
            suggestions=suggestions,
            metrics={
                "syntax_valid": score > 0.3,
                "lines_of_code": len(lines),
                "has_comments": '#' in code or '"""' in code
            }
        )
    
    def _extract_code(self, text: str) -> str:
        """提取代码块"""
        import re
        match = re.search(r'```(?:\w+)?\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return match.group(1)
        return text


class EvaluatorOptimizer:
    """
    评估者-优化器
    
    实现生成-评估-优化的闭环迭代
    """
    
    def __init__(
        self,
        generator: BaseGenerator,
        evaluator: BaseEvaluator,
        max_iterations: int = 5,
        pass_threshold: Optional[float] = None,
        early_stopping: bool = True
    ):
        """
        Args:
            generator: 生成器
            evaluator: 评估器
            max_iterations: 最大迭代次数
            pass_threshold: 通过阈值（覆盖评估器的阈值）
            early_stopping: 是否启用早停（连续两次评分不提升则停止）
        """
        self.generator = generator
        self.evaluator = evaluator
        self.max_iterations = max_iterations
        self.pass_threshold = pass_threshold
        self.early_stopping = early_stopping
        self.iteration_history: List[OptimizationIteration] = []
    
    async def optimize(
        self, 
        task: str,
        context: Optional[Dict] = None,
        initial_solution: Optional[str] = None
    ) -> OptimizationResult:
        """
        执行优化循环
        
        Args:
            task: 任务描述
            context: 上下文信息
            initial_solution: 初始解决方案（可选）
            
        Returns:
            优化结果
        """
        start_time = asyncio.get_event_loop().time()
        self.iteration_history = []
        
        # 生成初始解决方案
        if initial_solution:
            solution = initial_solution
        else:
            solution = await self.generator.generate(task, context)
        
        best_solution = solution
        best_score = 0.0
        no_improvement_count = 0
        
        for iteration in range(1, self.max_iterations + 1):
            # 评估
            evaluation = await self.evaluator.evaluate(solution, task)
            
            # 记录迭代
            iter_record = OptimizationIteration(
                iteration=iteration,
                solution=solution,
                evaluation=evaluation
            )
            self.iteration_history.append(iter_record)
            
            # 更新最佳解决方案
            if evaluation.score > best_score:
                best_solution = solution
                best_score = evaluation.score
                no_improvement_count = 0
            else:
                no_improvement_count += 1
            
            # 检查是否通过
            threshold = self.pass_threshold or 0.8
            if evaluation.passed and evaluation.score >= threshold:
                execution_time = asyncio.get_event_loop().time() - start_time
                return OptimizationResult(
                    success=True,
                    final_solution=best_solution,
                    iterations=self.iteration_history,
                    total_iterations=iteration,
                    final_score=best_score,
                    status=OptimizationStatus.COMPLETED,
                    execution_time=execution_time
                )
            
            # 早停检查
            if self.early_stopping and no_improvement_count >= 2:
                break
            
            # 生成优化版本
            if iteration < self.max_iterations:
                feedback = self._build_feedback(evaluation)
                solution = await self.generator.generate(
                    task, 
                    context, 
                    feedback=feedback
                )
        
        # 达到最大迭代次数
        execution_time = asyncio.get_event_loop().time() - start_time
        return OptimizationResult(
            success=best_score >= threshold,
            final_solution=best_solution,
            iterations=self.iteration_history,
            total_iterations=len(self.iteration_history),
            final_score=best_score,
            status=OptimizationStatus.MAX_ITERATIONS,
            execution_time=execution_time
        )
    
    def _build_feedback(self, evaluation: EvaluationResult) -> str:
        """构建反馈信息"""
        feedback_parts = [
            f"评估分数: {evaluation.score:.2f}",
            f"反馈: {evaluation.feedback}"
        ]
        
        if evaluation.suggestions:
            feedback_parts.append("改进建议:")
            for i, suggestion in enumerate(evaluation.suggestions, 1):
                feedback_parts.append(f"  {i}. {suggestion}")
        
        return "\n".join(feedback_parts)
    
    def get_optimization_report(self) -> str:
        """获取优化报告"""
        if not self.iteration_history:
            return "无优化记录"
        
        lines = ["="*60, "优化报告", "="*60, ""]
        
        for iter_record in self.iteration_history:
            lines.append(f"迭代 {iter_record.iteration}:")
            lines.append(f"  评分: {iter_record.evaluation.score:.2f}")
            lines.append(f"  状态: {'通过' if iter_record.evaluation.passed else '未通过'}")
            lines.append(f"  反馈: {iter_record.evaluation.feedback}")
            lines.append("")
        
        lines.append("="*60)
        return "\n".join(lines)


# ========== 便捷函数 ==========

async def optimize_solution(
    task: str,
    solution_type: str = "general",
    max_iterations: int = 5,
    context: Optional[Dict] = None
) -> OptimizationResult:
    """
    便捷函数：优化解决方案
    
    Args:
        task: 任务描述
        solution_type: 解决方案类型 (general, code)
        max_iterations: 最大迭代次数
        context: 上下文
        
    Returns:
        优化结果
    """
    generator = LLMGenerator()
    
    if solution_type == "code":
        evaluator = CodeEvaluator()
    else:
        evaluator = LLMEvaluator()
    
    optimizer = EvaluatorOptimizer(
        generator=generator,
        evaluator=evaluator,
        max_iterations=max_iterations
    )
    
    return await optimizer.optimize(task, context)


def create_code_optimizer(max_iterations: int = 5) -> EvaluatorOptimizer:
    """创建代码优化器"""
    return EvaluatorOptimizer(
        generator=LLMGenerator(name="CodeGenerator"),
        evaluator=CodeEvaluator(),
        max_iterations=max_iterations
    )


def create_content_optimizer(max_iterations: int = 3) -> EvaluatorOptimizer:
    """创建内容优化器"""
    return EvaluatorOptimizer(
        generator=LLMGenerator(name="ContentGenerator"),
        evaluator=LLMEvaluator(),
        max_iterations=max_iterations
    )
