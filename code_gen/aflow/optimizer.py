"""AFLOW Workflow Optimizer"""

import logging
from typing import List, Dict, Any, Optional
import asyncio

from .workflow import WorkflowGraph, WorkflowTemplates
from .evaluator import WorkflowEvaluator, EvaluationResult
from .search import WorkflowSearchSpace, WorkflowSearcher

logger = logging.getLogger(__name__)


class WorkflowOptimizer:
    """工作流优化器
    
    自动优化工作流以达到最佳性能
    """
    
    def __init__(
        self,
        evaluator: Optional[WorkflowEvaluator] = None,
        search_space: Optional[WorkflowSearchSpace] = None,
    ):
        self.evaluator = evaluator or WorkflowEvaluator()
        self.search_space = search_space or WorkflowSearchSpace()
        self.searcher = WorkflowSearcher(self.search_space, self.evaluator)
    
    async def optimize(
        self,
        initial_workflow: Optional[WorkflowGraph] = None,
        optimization_goal: str = "balanced",
        max_iterations: int = 50,
    ) -> WorkflowGraph:
        """优化工作流
        
        Args:
            initial_workflow: 初始工作流（可选）
            optimization_goal: 优化目标 ("speed", "quality", "cost", "balanced")
            max_iterations: 最大迭代次数
        
        Returns:
            优化后的工作流
        """
        # 设置优化目标
        self._set_optimization_goal(optimization_goal)
        
        # 如果没有初始工作流，从模板开始
        if initial_workflow is None:
            initial_workflow = WorkflowTemplates.sequential([
                "analyze_requirements",
                "design_architecture",
                "write_code",
            ])
        
        # 评估初始工作流
        try:
            initial_result = await self.evaluator.evaluate(initial_workflow)
            logger.info(f"Initial workflow score: {initial_result.score:.4f}")
        except Exception as e:
            logger.error(f"Initial workflow evaluation failed: {e}")
            initial_result = None
        
        # 使用搜索算法优化
        try:
            best_workflow = await self.searcher.search([initial_workflow])
        except Exception as e:
            logger.error(f"Workflow search failed: {e}")
            return initial_workflow  # 返回初始工作流作为降级方案
        
        # 最终评估
        try:
            final_result = await self.evaluator.evaluate(best_workflow)
            logger.info(f"Optimized workflow score: {final_result.score:.4f}")
        except Exception as e:
            logger.error(f"Final workflow evaluation failed: {e}")
            return best_workflow  # 返回搜索得到的工作流，即使没有最终评分
        
        # 保存性能指标
        best_workflow.score = final_result.score
        best_workflow.success_rate = final_result.success_rate
        best_workflow.avg_latency = final_result.avg_latency
        best_workflow.cost = final_result.cost
        
        return best_workflow
    
    def _set_optimization_goal(self, goal: str):
        """设置优化目标"""
        weights = {
            "speed": {
                "success_rate": 0.3,
                "latency": 0.5,
                "cost": 0.1,
                "quality": 0.1,
            },
            "quality": {
                "success_rate": 0.5,
                "latency": 0.1,
                "cost": 0.1,
                "quality": 0.3,
            },
            "cost": {
                "success_rate": 0.3,
                "latency": 0.1,
                "cost": 0.5,
                "quality": 0.1,
            },
            "balanced": {
                "success_rate": 0.4,
                "latency": 0.2,
                "cost": 0.2,
                "quality": 0.2,
            },
        }
        
        self.evaluator.weights = weights.get(goal, weights["balanced"])
    
    async def optimize_for_task(
        self,
        task_description: str,
        task_type: str = "code_generation",
    ) -> WorkflowGraph:
        """为特定任务优化工作流"""
        # 根据任务类型选择初始模板
        if task_type == "code_generation":
            initial = WorkflowTemplates.sequential([
                "analyze_requirements",
                "design_architecture",
                "write_code",
                "review_code",
                "write_tests",
            ], name="code_generation")
        
        elif task_type == "bug_fix":
            initial = WorkflowTemplates.sequential([
                "analyze_requirements",
                "debug_error",
                "write_code",
                "run_tests",
            ], name="bug_fix")
        
        elif task_type == "refactoring":
            initial = WorkflowTemplates.sequential([
                "analyze_requirements",
                "refactor_code",
                "review_code",
                "run_tests",
            ], name="refactoring")
        
        else:
            initial = WorkflowTemplates.sequential([
                "analyze_requirements",
                "write_code",
            ], name="default")
        
        return await self.optimize(initial)
    
    def analyze_bottlenecks(self, workflow: WorkflowGraph) -> List[Dict[str, Any]]:
        """分析工作流瓶颈"""
        bottlenecks = []
        
        # 分析节点数量
        num_nodes = len(workflow.nodes)
        if num_nodes > 15:
            bottlenecks.append({
                "type": "complexity",
                "severity": "high",
                "description": f"Workflow has {num_nodes} nodes, which may be too complex",
                "suggestion": "Consider splitting into smaller workflows or removing unnecessary steps",
            })
        elif num_nodes < 3:
            bottlenecks.append({
                "type": "insufficient",
                "severity": "medium",
                "description": f"Workflow has only {num_nodes} nodes, may be insufficient",
                "suggestion": "Consider adding more validation or review steps",
            })
        
        # 分析并行度
        from .workflow import NodeType
        parallel_nodes = [n for n in workflow.nodes if n.node_type == NodeType.PARALLEL]
        if not parallel_nodes and num_nodes > 5:
            bottlenecks.append({
                "type": "parallelism",
                "severity": "medium",
                "description": "No parallel execution detected",
                "suggestion": "Consider adding parallel nodes for independent tasks",
            })
        
        # 分析条件分支
        condition_nodes = [n for n in workflow.nodes if n.node_type == NodeType.CONDITION]
        if len(condition_nodes) > 3:
            bottlenecks.append({
                "type": "branching",
                "severity": "low",
                "description": f"Workflow has {len(condition_nodes)} condition nodes",
                "suggestion": "Consider simplifying conditional logic",
            })
        
        return bottlenecks
    
    def suggest_improvements(self, workflow: WorkflowGraph) -> List[str]:
        """建议改进"""
        suggestions = []
        
        # 结构建议
        bottlenecks = self.analyze_bottlenecks(workflow)
        for b in bottlenecks:
            suggestions.append(f"[{b['severity'].upper()}] {b['suggestion']}")
        
        # 动作建议
        actions = [n.action for n in workflow.nodes if n.action]
        
        if "review_code" not in actions and "write_code" in actions:
            suggestions.append("Consider adding a code review step after writing code")
        
        if "write_tests" not in actions and "write_code" in actions:
            suggestions.append("Consider adding test generation step")
        
        if "run_tests" not in actions and "write_tests" in actions:
            suggestions.append("Consider adding test execution step")
        
        return suggestions


class IncrementalOptimizer(WorkflowOptimizer):
    """增量优化器
    
    基于实际执行反馈持续优化工作流
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execution_history: List[Dict[str, Any]] = []
    
    def record_execution(
        self,
        workflow: WorkflowGraph,
        success: bool,
        latency: float,
        cost: float,
        quality: float,
    ):
        """记录执行结果"""
        self.execution_history.append({
            "workflow_id": workflow.id,
            "success": success,
            "latency": latency,
            "cost": cost,
            "quality": quality,
            "timestamp": asyncio.get_event_loop().time(),
        })
    
    def should_optimize(self, workflow: WorkflowGraph) -> bool:
        """判断是否需要优化"""
        # 获取该工作流的执行记录
        records = [r for r in self.execution_history if r["workflow_id"] == workflow.id]
        
        if len(records) < 5:
            return False
        
        # 计算最近的成功率
        recent = records[-10:]
        success_rate = sum(1 for r in recent if r["success"]) / len(recent)
        
        # 成功率低于阈值，需要优化
        return success_rate < 0.7
    
    async def incremental_optimize(self, workflow: WorkflowGraph) -> WorkflowGraph:
        """增量优化"""
        if not self.should_optimize(workflow):
            print("Workflow performance is acceptable, no optimization needed")
            return workflow
        
        print("Workflow performance degraded, starting incremental optimization...")
        
        # 分析执行历史
        records = [r for r in self.execution_history if r["workflow_id"] == workflow.id]
        
        # 找出问题
        failures = [r for r in records if not r["success"]]
        slow_executions = [r for r in records if r["latency"] > 10]
        
        print(f"  - Total executions: {len(records)}")
        print(f"  - Failures: {len(failures)}")
        print(f"  - Slow executions: {len(slow_executions)}")
        
        # 基于问题优化
        if len(failures) > len(records) * 0.3:
            # 失败率高，增加验证步骤
            return await self._add_validation_steps(workflow)
        
        if len(slow_executions) > len(records) * 0.3:
            # 延迟高，增加并行
            return await self._increase_parallelism(workflow)
        
        # 默认优化
        return await self.optimize(workflow)
    
    async def _add_validation_steps(self, workflow: WorkflowGraph) -> WorkflowGraph:
        """添加验证步骤"""
        optimized = workflow.clone(f"{workflow.name}_validated")
        
        # 在关键节点后添加验证
        from .workflow import NodeType, WorkflowNode, WorkflowEdge
        
        # 找到写代码节点
        code_nodes = [n for n in optimized.nodes if n.action == "write_code"]
        for node in code_nodes:
            # 添加审查节点
            review_node = WorkflowNode(
                name=f"review_{node.name}",
                node_type=NodeType.ACTION,
                action="review_code",
            )
            optimized.add_node(review_node)
            
            # 重定向边
            outgoing = optimized.get_outgoing_edges(node.id)
            for edge in outgoing:
                edge.source = review_node.id
            
            # 添加新边
            optimized.add_edge(WorkflowEdge(
                source=node.id,
                target=review_node.id,
            ))
        
        return optimized
    
    async def _increase_parallelism(self, workflow: WorkflowGraph) -> WorkflowGraph:
        """增加并行度"""
        optimized = workflow.clone(f"{workflow.name}_parallel")
        
        # 分析可并行的节点
        # 简化实现：将顺序节点改为并行
        
        return optimized


# 便捷函数

async def optimize_workflow(
    workflow: Optional[WorkflowGraph] = None,
    goal: str = "balanced",
) -> WorkflowGraph:
    """便捷函数：优化工作流"""
    optimizer = WorkflowOptimizer()
    return await optimizer.optimize(workflow, goal)


async def generate_optimal_workflow(
    task_type: str = "code_generation",
) -> WorkflowGraph:
    """便捷函数：生成最优工作流"""
    optimizer = WorkflowOptimizer()
    return await optimizer.optimize_for_task("", task_type)
