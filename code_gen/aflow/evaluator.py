"""AFLOW Workflow Evaluator"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import asyncio

from .workflow import WorkflowGraph


@dataclass
class EvaluationResult:
    """评估结果"""
    workflow_id: str
    score: float                    # 综合评分 (0-1)
    success_rate: float             # 成功率
    avg_latency: float              # 平均延迟 (秒)
    cost: float                     # 成本 ($)

    # 详细指标
    metrics: Dict[str, float] = field(default_factory=dict)

    # 错误信息
    errors: List[str] = field(default_factory=list)


class WorkflowEvaluator:
    """工作流评估器
    
    评估工作流的性能和效果
    """
    
    def __init__(
        self,
        test_cases: Optional[List[Dict]] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.test_cases = test_cases or []
        self.weights = weights or {
            "success_rate": 0.4,
            "latency": 0.2,
            "cost": 0.2,
            "quality": 0.2,
        }
    
    async def evaluate(
        self,
        workflow: WorkflowGraph,
        num_runs: int = 3,
    ) -> EvaluationResult:
        """评估工作流
        
        Args:
            workflow: 要评估的工作流
            num_runs: 每个测试用例运行次数
        
        Returns:
            评估结果
        """
        results = []
        errors = []
        
        for test_case in self.test_cases:
            for _ in range(num_runs):
                try:
                    result = await self._run_test(workflow, test_case)
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))
        
        if not results:
            return EvaluationResult(
                workflow_id=workflow.id,
                score=0.0,
                success_rate=0.0,
                avg_latency=0.0,
                cost=0.0,
                errors=errors,
            )
        
        # 计算指标
        success_count = sum(1 for r in results if r.get("success", False))
        success_rate = success_count / len(results)
        avg_latency = sum(r.get("latency", 0) for r in results) / len(results)
        total_cost = sum(r.get("cost", 0) for r in results)
        
        # 质量评分（基于输出质量）
        quality_scores = [r.get("quality", 0.5) for r in results]
        avg_quality = sum(quality_scores) / len(quality_scores)
        
        # 综合评分
        score = self._calculate_score(
            success_rate=success_rate,
            latency=avg_latency,
            cost=total_cost,
            quality=avg_quality,
        )
        
        return EvaluationResult(
            workflow_id=workflow.id,
            score=score,
            success_rate=success_rate,
            avg_latency=avg_latency,
            cost=total_cost,
            metrics={
                "quality": avg_quality,
                "test_cases": len(self.test_cases),
                "total_runs": len(results),
            },
            errors=errors,
        )
    
    async def _run_test(
        self,
        workflow: WorkflowGraph,
        test_case: Dict,
    ) -> Dict[str, Any]:
        """运行单个测试"""
        # 这里应该实际执行工作流
        # 简化实现：模拟执行
        
        import random
        
        # 模拟执行结果
        success = random.random() > 0.2  # 80% 成功率
        latency = random.uniform(1, 10)  # 1-10 秒
        cost = random.uniform(0.01, 0.5)  # $0.01-$0.5
        quality = random.uniform(0.5, 1.0)  # 质量评分
        
        return {
            "success": success,
            "latency": latency,
            "cost": cost,
            "quality": quality,
        }
    
    def _calculate_score(
        self,
        success_rate: float,
        latency: float,
        cost: float,
        quality: float,
    ) -> float:
        """计算综合评分"""
        # 延迟评分（越低越好）
        latency_score = max(0, 1 - latency / 10)  # 假设 10 秒为基准
        
        # 成本评分（越低越好）
        cost_score = max(0, 1 - cost / 1.0)  # 假设 $1 为基准
        
        # 加权综合
        score = (
            success_rate * self.weights["success_rate"] +
            latency_score * self.weights["latency"] +
            cost_score * self.weights["cost"] +
            quality * self.weights["quality"]
        )
        
        return min(max(score, 0.0), 1.0)
    
    def compare_workflows(
        self,
        workflows: List[WorkflowGraph],
        results: List[EvaluationResult],
    ) -> List[tuple]:
        """比较多个工作流
        
        Returns:
            按评分排序的 (workflow, result) 列表
        """
        pairs = list(zip(workflows, results))
        pairs.sort(key=lambda x: x[1].score, reverse=True)
        return pairs
    
    def get_best_workflow(
        self,
        workflows: List[WorkflowGraph],
        results: List[EvaluationResult],
    ) -> Optional[tuple]:
        """获取最佳工作流"""
        if not workflows or not results:
            return None
        
        pairs = self.compare_workflows(workflows, results)
        return pairs[0] if pairs else None


class SimpleEvaluator(WorkflowEvaluator):
    """简单评估器
    
    基于工作流结构的快速评估
    """
    
    def __init__(self):
        super().__init__()
    
    def evaluate_structure(self, workflow: WorkflowGraph) -> Dict[str, float]:
        """评估工作流结构"""
        metrics = {}
        
        # 节点数量
        metrics["num_nodes"] = len(workflow.nodes)
        
        # 边数量
        metrics["num_edges"] = len(workflow.edges)
        
        # 复杂度（边数/节点数）
        if len(workflow.nodes) > 0:
            metrics["complexity"] = len(workflow.edges) / len(workflow.nodes)
        else:
            metrics["complexity"] = 0
        
        # 并行度（并行节点数）
        from .workflow import NodeType
        parallel_nodes = [n for n in workflow.nodes if n.node_type == NodeType.PARALLEL]
        metrics["parallelism"] = len(parallel_nodes)
        
        # 条件分支数
        condition_nodes = [n for n in workflow.nodes if n.node_type == NodeType.CONDITION]
        metrics["branching"] = len(condition_nodes)
        
        # 结构评分
        # 理想：节点数适中（5-15），有一定并行度，条件分支合理
        node_score = 1.0 - abs(metrics["num_nodes"] - 10) / 20
        parallel_score = min(metrics["parallelism"] / 2, 1.0)
        branch_score = min(metrics["branching"] / 3, 1.0)
        
        metrics["structure_score"] = (node_score + parallel_score + branch_score) / 3
        
        return metrics
    
    def quick_evaluate(self, workflow: WorkflowGraph) -> EvaluationResult:
        """快速评估"""
        metrics = self.evaluate_structure(workflow)
        
        # 基于结构估算性能
        num_nodes = metrics["num_nodes"]
        parallelism = metrics["parallelism"]
        
        # 估算延迟（假设每个节点 2 秒，并行减少时间）
        estimated_latency = num_nodes * 2 / (1 + parallelism * 0.5)
        
        # 估算成本（假设每个节点 $0.1）
        estimated_cost = num_nodes * 0.1
        
        # 结构评分作为质量代理
        quality = metrics["structure_score"]
        
        # 假设成功率
        success_rate = 0.8
        
        # 计算综合评分
        score = self._calculate_score(
            success_rate=success_rate,
            latency=estimated_latency,
            cost=estimated_cost,
            quality=quality,
        )
        
        return EvaluationResult(
            workflow_id=workflow.id,
            score=score,
            success_rate=success_rate,
            avg_latency=estimated_latency,
            cost=estimated_cost,
            metrics=metrics,
        )
