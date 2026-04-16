"""AFLOW - Automated Workflow Generation

自动化工作流生成系统，灵感来源于 MetaGPT 的 AFLOW (ICLR 2025 Oral)。
通过搜索和优化自动生成最优的 Agent 工作流。
"""

from .workflow import WorkflowNode, WorkflowEdge, WorkflowGraph
from .optimizer import WorkflowOptimizer
from .search import WorkflowSearchSpace, WorkflowSearcher
from .evaluator import WorkflowEvaluator

__all__ = [
    "WorkflowNode",
    "WorkflowEdge", 
    "WorkflowGraph",
    "WorkflowOptimizer",
    "WorkflowSearchSpace",
    "WorkflowSearcher",
    "WorkflowEvaluator",
]
