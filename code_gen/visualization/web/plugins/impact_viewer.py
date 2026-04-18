"""Impact Viewer Plugin - 影响分析可视化插件

可视化展示代码变更的影响范围
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import logging

from .base import VisualizationPlugin
from code_gen.knowledge_graph import ImpactAnalyzer, RiskLevel

logger = logging.getLogger(__name__)


class ImpactViewerPlugin(VisualizationPlugin):
    """影响分析可视化插件

    展示代码变更的 blast radius
    """

    id = "impact_viewer"
    name = "影响分析"
    description = "分析代码变更的影响范围和风险等级"
    icon = "⚡"
    position = "panel"
    width = 700
    height = 500

    def __init__(self):
        super().__init__()
        self._analyzer: Optional[ImpactAnalyzer] = None
        self._last_result: Optional[Dict[str, Any]] = None

    def on_init(self):
        """初始化"""
        graph = self.get_graph()
        if graph:
            self._analyzer = ImpactAnalyzer(graph)
        logger.info("ImpactViewerPlugin initialized")

    def on_destroy(self):
        """销毁"""
        logger.info("ImpactViewerPlugin destroyed")

    def render(self) -> Dict[str, Any]:
        """渲染影响分析面板"""
        if self._last_result:
            return {
                "type": "impact_view",
                "result": self._last_result,
            }

        return {
            "type": "impact_view",
            "message": "选择一个符号进行分析",
        }

    def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理前端消息"""
        action = message.get("action")

        if action == "analyze":
            return self._handle_analyze(message)
        elif action == "analyze_change":
            return self._handle_analyze_change(message)
        elif action == "get_summary":
            return self._handle_get_summary()

        return None

    def _handle_analyze(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """分析符号影响"""
        symbol_name = message.get("symbol_name")
        max_depth = message.get("max_depth", 3)

        if not self._analyzer:
            return {"error": "Analyzer not initialized"}

        try:
            result = self._analyzer.analyze(
                symbol_name,
                direction="both",
                max_depth=max_depth
            )

            self._last_result = self._format_result(result)

            return {
                "action": "analysis_complete",
                "result": self._last_result,
            }

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return {"error": str(e)}

    def _handle_analyze_change(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """分析代码变更影响"""
        file_path = message.get("file_path")
        line_start = message.get("line_start")
        line_end = message.get("line_end")

        if not self._analyzer:
            return {"error": "Analyzer not initialized"}

        try:
            results = self._analyzer.analyze_change(
                file_path, line_start, line_end
            )

            formatted_results = [self._format_result(r) for r in results]

            return {
                "action": "change_analysis_complete",
                "results": formatted_results,
            }

        except Exception as e:
            logger.error(f"Change analysis error: {e}")
            return {"error": str(e)}

    def _handle_get_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        if not self._last_result:
            return {"message": "No analysis result available"}

        return {
            "action": "summary",
            "summary": self._last_result.get("summary"),
        }

    def _format_result(self, result) -> Dict[str, Any]:
        """格式化分析结果"""
        # 风险等级样式
        risk_styles = {
            RiskLevel.LOW: {"color": "#27AE60", "icon": "✅", "label": "低风险"},
            RiskLevel.MEDIUM: {"color": "#F39C12", "icon": "⚠️", "label": "中风险"},
            RiskLevel.HIGH: {"color": "#E74C3C", "icon": "🔴", "label": "高风险"},
            RiskLevel.CRITICAL: {"color": "#C0392B", "icon": "🚨", "label": "严重风险"},
        }

        risk_style = risk_styles.get(result.risk_level, risk_styles[RiskLevel.LOW])

        return {
            "target": {
                "id": result.target_node.id,
                "name": result.target_node.name,
                "type": result.target_node.node_type.value,
                "file_path": result.target_node.file_path,
                "line": result.target_node.line_start,
            },
            "risk": {
                "level": result.risk_level.value,
                "label": risk_style["label"],
                "icon": risk_style["icon"],
                "color": risk_style["color"],
            },
            "upstream": {
                "count": len(result.upstream_nodes),
                "nodes": [
                    {
                        "id": node.id,
                        "name": node.name,
                        "type": node.node_type.value,
                        "file_path": node.file_path,
                    }
                    for node in result.upstream_nodes[:10]  # 限制数量
                ],
            },
            "downstream": {
                "count": len(result.downstream_nodes),
                "nodes": [
                    {
                        "id": node.id,
                        "name": node.name,
                        "type": node.node_type.value,
                        "file_path": node.file_path,
                    }
                    for node in result.downstream_nodes[:10]
                ],
            },
            "statistics": {
                "total_affected_files": result.total_affected_files,
                "total_affected_functions": result.total_affected_functions,
                "total_affected_classes": result.total_affected_classes,
            },
            "risk_factors": result.risk_factors,
            "recommendations": result.recommendations,
            "summary": self._analyzer.get_quick_summary(result) if self._analyzer else "",
        }
