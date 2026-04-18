"""Impact Analyzer - 影响分析器

分析代码变更的影响范围，计算 blast radius
灵感来源于 GitNexus 的 impact 分析功能
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any
import logging

from .graph import (
    Node, Edge, NodeType, EdgeType, KnowledgeGraph
)

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"              # 低风险
    MEDIUM = "medium"        # 中风险
    HIGH = "high"            # 高风险
    CRITICAL = "critical"    # 严重风险


@dataclass
class ImpactResult:
    """影响分析结果"""
    target_node: Node                    # 目标节点
    risk_level: RiskLevel                # 风险等级

    # 上游影响（谁调用了目标）
    upstream_nodes: List[Node] = field(default_factory=list)
    upstream_depth: int = 0              # 上游分析深度

    # 下游影响（目标调用了谁）
    downstream_nodes: List[Node] = field(default_factory=list)
    downstream_depth: int = 0            # 下游分析深度

    # 影响统计
    total_affected_files: int = 0
    total_affected_functions: int = 0
    total_affected_classes: int = 0

    # 风险详情
    risk_factors: List[str] = field(default_factory=list)

    # 建议
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "target": self.target_node.to_dict(),
            "risk_level": self.risk_level.value,
            "upstream": {
                "nodes": [n.to_dict() for n in self.upstream_nodes],
                "depth": self.upstream_depth,
                "count": len(self.upstream_nodes),
            },
            "downstream": {
                "nodes": [n.to_dict() for n in self.downstream_nodes],
                "depth": self.downstream_depth,
                "count": len(self.downstream_nodes),
            },
            "statistics": {
                "total_affected_files": self.total_affected_files,
                "total_affected_functions": self.total_affected_functions,
                "total_affected_classes": self.total_affected_classes,
            },
            "risk_factors": self.risk_factors,
            "recommendations": self.recommendations,
        }


class ImpactAnalyzer:
    """影响分析器

    分析代码变更的影响范围，帮助开发者理解修改的潜在风险
    """

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    def analyze(
        self,
        target: str | Node,
        direction: str = "both",          # "upstream", "downstream", "both"
        max_depth: int = 3,
    ) -> ImpactResult:
        """分析影响

        Args:
            target: 目标节点或节点名称
            direction: 分析方向
            max_depth: 最大分析深度

        Returns:
            影响分析结果
        """
        # 获取目标节点
        if isinstance(target, str):
            target_node = self._find_target(target)
        else:
            target_node = target

        if not target_node:
            raise ValueError(f"Target not found: {target}")

        logger.info(f"Analyzing impact of {target_node.name} (type: {target_node.node_type.value})")

        result = ImpactResult(
            target_node=target_node,
            risk_level=RiskLevel.LOW,
        )

        # 分析上游影响
        if direction in ("upstream", "both"):
            result.upstream_nodes = self._analyze_upstream(target_node, max_depth)
            result.upstream_depth = max_depth

        # 分析下游影响
        if direction in ("downstream", "both"):
            result.downstream_nodes = self._analyze_downstream(target_node, max_depth)
            result.downstream_depth = max_depth

        # 计算统计信息
        self._calculate_statistics(result)

        # 评估风险等级
        self._assess_risk(result)

        # 生成建议
        self._generate_recommendations(result)

        return result

    def analyze_change(
        self,
        file_path: str,
        line_start: int,
        line_end: int,
    ) -> List[ImpactResult]:
        """分析特定代码变更的影响

        Args:
            file_path: 文件路径
            line_start: 起始行
            line_end: 结束行

        Returns:
            影响分析结果列表
        """
        # 查找受影响的节点
        affected_nodes = self._find_nodes_in_range(file_path, line_start, line_end)

        if not affected_nodes:
            logger.warning(f"No nodes found in {file_path}:{line_start}-{line_end}")
            return []

        results = []
        for node in affected_nodes:
            result = self.analyze(node)
            results.append(result)

        return results

    def detect_changes(
        self,
        modified_files: List[str],
    ) -> Dict[str, List[ImpactResult]]:
        """检测多个文件变更的影响

        Args:
            modified_files: 修改的文件列表

        Returns:
            文件到影响结果的映射
        """
        results = {}

        for file_path in modified_files:
            # 获取文件中的所有节点
            nodes = self.graph.get_nodes_by_file(file_path)

            if nodes:
                file_results = []
                for node in nodes:
                    if node.node_type in (NodeType.FUNCTION, NodeType.METHOD, NodeType.CLASS):
                        result = self.analyze(node)
                        file_results.append(result)

                if file_results:
                    results[file_path] = file_results

        return results

    def _find_target(self, name: str) -> Optional[Node]:
        """查找目标节点"""
        # 尝试精确匹配
        node = self.graph.find_node_by_name(name)
        if node:
            return node

        # 尝试模糊匹配
        nodes = self.graph.find_nodes_by_pattern(name)
        if nodes:
            return nodes[0]

        return None

    def _find_nodes_in_range(
        self,
        file_path: str,
        line_start: int,
        line_end: int,
    ) -> List[Node]:
        """查找范围内的节点"""
        nodes = self.graph.get_nodes_by_file(file_path)
        affected = []

        for node in nodes:
            if node.line_start and node.line_end:
                # 检查是否有重叠
                if not (node.line_end < line_start or node.line_start > line_end):
                    affected.append(node)

        return affected

    def _analyze_upstream(self, node: Node, max_depth: int) -> List[Node]:
        """分析上游影响（谁调用了这个节点）"""
        visited = set()
        queue = [(node.id, 0)]
        upstream = []

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited or depth >= max_depth:
                continue

            visited.add(current_id)

            # 获取调用当前节点的边
            incoming_calls = self.graph.get_incoming_edges(current_id, EdgeType.CALLS)

            for edge in incoming_calls:
                caller = self.graph.get_node(edge.source_id)
                if caller and caller.id not in visited:
                    upstream.append(caller)
                    queue.append((caller.id, depth + 1))

        return upstream

    def _analyze_downstream(self, node: Node, max_depth: int) -> List[Node]:
        """分析下游影响（这个节点调用了谁）"""
        visited = set()
        queue = [(node.id, 0)]
        downstream = []

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited or depth >= max_depth:
                continue

            visited.add(current_id)

            # 获取当前节点调用的边
            outgoing_calls = self.graph.get_outgoing_edges(current_id, EdgeType.CALLS)

            for edge in outgoing_calls:
                callee = self.graph.get_node(edge.target_id)
                if callee and callee.id not in visited:
                    downstream.append(callee)
                    queue.append((callee.id, depth + 1))

        return downstream

    def _calculate_statistics(self, result: ImpactResult):
        """计算统计信息"""
        affected_files = set()
        affected_functions = 0
        affected_classes = 0

        all_nodes = [result.target_node] + result.upstream_nodes + result.downstream_nodes

        for node in all_nodes:
            if node.file_path:
                affected_files.add(node.file_path)

            if node.node_type == NodeType.FUNCTION:
                affected_functions += 1
            elif node.node_type == NodeType.METHOD:
                affected_functions += 1
            elif node.node_type == NodeType.CLASS:
                affected_classes += 1

        result.total_affected_files = len(affected_files)
        result.total_affected_functions = affected_functions
        result.total_affected_classes = affected_classes

    def _assess_risk(self, result: ImpactResult):
        """评估风险等级"""
        risk_score = 0
        risk_factors = []

        # 基于影响范围评分
        total_affected = len(result.upstream_nodes) + len(result.downstream_nodes)

        if total_affected > 50:
            risk_score += 40
            risk_factors.append(f"大量受影响节点 ({total_affected})")
        elif total_affected > 20:
            risk_score += 25
            risk_factors.append(f"较多受影响节点 ({total_affected})")
        elif total_affected > 5:
            risk_score += 10

        # 基于文件数量评分
        if result.total_affected_files > 10:
            risk_score += 30
            risk_factors.append(f"跨多个文件 ({result.total_affected_files})")
        elif result.total_affected_files > 5:
            risk_score += 15

        # 基于节点类型评分
        if result.target_node.node_type == NodeType.CLASS:
            # 修改类风险较高
            risk_score += 10
            risk_factors.append("修改的是类定义")

        # 检查是否有外部依赖
        external_deps = [n for n in result.downstream_nodes
                        if n.properties.get("is_external")]
        if external_deps:
            risk_score += 15
            risk_factors.append(f"依赖外部库 ({len(external_deps)})")

        # 确定风险等级
        if risk_score >= 70:
            result.risk_level = RiskLevel.CRITICAL
        elif risk_score >= 50:
            result.risk_level = RiskLevel.HIGH
        elif risk_score >= 25:
            result.risk_level = RiskLevel.MEDIUM
        else:
            result.risk_level = RiskLevel.LOW

        result.risk_factors = risk_factors

    def _generate_recommendations(self, result: ImpactResult):
        """生成建议"""
        recommendations = []

        if result.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            recommendations.append("⚠️ 高风险变更！建议进行全面的回归测试")
            recommendations.append("建议分阶段部署，先在小范围验证")

        if result.total_affected_files > 5:
            recommendations.append(f"影响跨 {result.total_affected_files} 个文件，确保所有相关测试通过")

        if len(result.upstream_nodes) > 10:
            recommendations.append(f"被 {len(result.upstream_nodes)} 个调用方使用，注意保持向后兼容")

        if result.target_node.node_type == NodeType.CLASS:
            recommendations.append("修改类定义可能影响继承关系，检查所有子类")

        if result.risk_level == RiskLevel.LOW:
            recommendations.append("✅ 低风险变更，可以安全地进行修改")

        result.recommendations = recommendations

    def get_quick_summary(self, result: ImpactResult) -> str:
        """获取快速摘要"""
        lines = [
            f"🎯 目标: {result.target_node.name} ({result.target_node.node_type.value})",
            f"⚡ 风险等级: {result.risk_level.value.upper()}",
            f"📊 影响范围:",
            f"   - 上游调用方: {len(result.upstream_nodes)} 个",
            f"   - 下游依赖: {len(result.downstream_nodes)} 个",
            f"   - 涉及文件: {result.total_affected_files} 个",
            f"   - 涉及函数: {result.total_affected_functions} 个",
            f"   - 涉及类: {result.total_affected_classes} 个",
        ]

        if result.risk_factors:
            lines.append(f"⚠️ 风险因素:")
            for factor in result.risk_factors:
                lines.append(f"   - {factor}")

        return "\n".join(lines)
