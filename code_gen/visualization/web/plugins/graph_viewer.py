"""Graph Viewer Plugin - 代码图谱可视化插件"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import logging

from .base import VisualizationPlugin
from code_gen.knowledge_graph import KnowledgeGraph, Node, Edge, NodeType

logger = logging.getLogger(__name__)


class GraphViewerPlugin(VisualizationPlugin):
    """代码图谱可视化插件

    使用 D3.js 或 Cytoscape.js 展示代码知识图谱
    """

    id = "graph_viewer"
    name = "代码图谱"
    description = "可视化展示代码知识图谱，支持节点拖拽、缩放、搜索"
    icon = "🕸️"
    position = "panel"
    width = 800
    height = 600

    def __init__(self):
        super().__init__()
        self._selected_node: Optional[str] = None
        self._layout = "force"  # force, hierarchical, circular
        self._filters = {
            "show_classes": True,
            "show_functions": True,
            "show_variables": False,
            "show_imports": False,
        }

    def on_init(self):
        """初始化"""
        logger.info("GraphViewerPlugin initialized")

    def on_destroy(self):
        """销毁"""
        logger.info("GraphViewerPlugin destroyed")

    def render(self) -> Dict[str, Any]:
        """渲染图谱数据"""
        graph = self.get_graph()
        if not graph:
            return {"error": "No graph available"}

        # 转换图谱数据为前端格式
        nodes = self._convert_nodes(graph)
        edges = self._convert_edges(graph)

        return {
            "type": "graph",
            "layout": self._layout,
            "filters": self._filters,
            "nodes": nodes,
            "edges": edges,
            "selected": self._selected_node,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
            }
        }

    def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理前端消息"""
        action = message.get("action")

        if action == "select_node":
            return self._handle_select_node(message)
        elif action == "expand_node":
            return self._handle_expand_node(message)
        elif action == "search":
            return self._handle_search(message)
        elif action == "change_layout":
            return self._handle_change_layout(message)
        elif action == "update_filters":
            return self._handle_update_filters(message)
        elif action == "get_node_details":
            return self._handle_get_node_details(message)

        return None

    def _convert_nodes(self, graph: KnowledgeGraph) -> List[Dict[str, Any]]:
        """转换节点数据"""
        nodes = []

        for node in graph:
            # 应用过滤器
            if not self._should_show_node(node):
                continue

            node_data = {
                "id": node.id,
                "name": node.name,
                "type": node.node_type.value,
                "language": node.language.value if hasattr(node, 'language') else "unknown",
                "file_path": node.file_path,
                "line": node.line_start,
                "signature": node.signature,
                # 节点样式
                "style": self._get_node_style(node),
            }
            nodes.append(node_data)

        return nodes

    def _convert_edges(self, graph: KnowledgeGraph) -> List[Dict[str, Any]]:
        """转换边数据"""
        edges = []

        for edge in graph.edges.values():
            edge_data = {
                "id": edge.id,
                "source": edge.source_id,
                "target": edge.target_id,
                "type": edge.edge_type.value,
                "style": self._get_edge_style(edge),
            }
            edges.append(edge_data)

        return edges

    def _should_show_node(self, node: Node) -> bool:
        """检查节点是否应该显示"""
        if node.node_type == NodeType.CLASS and not self._filters["show_classes"]:
            return False
        if node.node_type in (NodeType.FUNCTION, NodeType.METHOD) and not self._filters["show_functions"]:
            return False
        if node.node_type == NodeType.VARIABLE and not self._filters["show_variables"]:
            return False
        if node.node_type == NodeType.IMPORT and not self._filters["show_imports"]:
            return False
        return True

    def _get_node_style(self, node: Node) -> Dict[str, Any]:
        """获取节点样式"""
        # 根据节点类型和语言返回不同样式
        styles = {
            NodeType.CLASS: {
                "color": "#4A90E2",
                "shape": "box",
                "size": 30,
            },
            NodeType.FUNCTION: {
                "color": "#7ED321",
                "shape": "ellipse",
                "size": 20,
            },
            NodeType.METHOD: {
                "color": "#F5A623",
                "shape": "ellipse",
                "size": 20,
            },
            NodeType.INTERFACE: {
                "color": "#9013FE",
                "shape": "hexagon",
                "size": 25,
            },
            NodeType.IMPORT: {
                "color": "#999999",
                "shape": "diamond",
                "size": 15,
            },
        }

        base_style = styles.get(node.node_type, {
            "color": "#CCCCCC",
            "shape": "dot",
            "size": 15,
        })

        # 根据语言调整颜色
        lang_colors = {
            "python": "#3776AB",
            "typescript": "#3178C6",
            "javascript": "#F7DF1E",
        }

        if hasattr(node, 'language') and node.language.value in lang_colors:
            base_style["border_color"] = lang_colors[node.language.value]

        return base_style

    def _get_edge_style(self, edge: Edge) -> Dict[str, Any]:
        """获取边样式"""
        styles = {
            "extends": {"color": "#E74C3C", "dashed": False, "width": 2},
            "implements": {"color": "#9B59B6", "dashed": True, "width": 2},
            "calls": {"color": "#3498DB", "dashed": False, "width": 1},
            "imports": {"color": "#95A5A6", "dashed": True, "width": 1},
        }
        return styles.get(edge.edge_type.value, {"color": "#CCCCCC", "width": 1})

    def _handle_select_node(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理节点选择"""
        node_id = message.get("node_id")
        self._selected_node = node_id

        graph = self.get_graph()
        if graph and node_id in graph.nodes:
            node = graph.nodes[node_id]
            return {
                "action": "node_selected",
                "node": {
                    "id": node.id,
                    "name": node.name,
                    "type": node.node_type.value,
                    "file_path": node.file_path,
                    "line": node.line_start,
                    "signature": node.signature,
                    "source_code": node.source_code[:500] if node.source_code else None,
                }
            }

        return {"error": "Node not found"}

    def _handle_expand_node(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理节点展开"""
        node_id = message.get("node_id")
        graph = self.get_graph()

        if not graph or node_id not in graph.nodes:
            return {"error": "Node not found"}

        # 获取相邻节点
        neighbors = graph.get_neighbors(node_id)
        neighbor_data = []

        for neighbor in neighbors:
            neighbor_data.append({
                "id": neighbor.id,
                "name": neighbor.name,
                "type": neighbor.node_type.value,
            })

        return {
            "action": "node_expanded",
            "node_id": node_id,
            "neighbors": neighbor_data,
        }

    def _handle_search(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理搜索"""
        query = message.get("query", "")
        graph = self.get_graph()

        if not graph:
            return {"error": "No graph available"}

        # 简单搜索实现
        results = []
        for node in graph:
            if query.lower() in node.name.lower():
                results.append({
                    "id": node.id,
                    "name": node.name,
                    "type": node.node_type.value,
                    "file_path": node.file_path,
                })

        return {
            "action": "search_results",
            "query": query,
            "results": results[:20],  # 限制结果数量
        }

    def _handle_change_layout(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理布局切换"""
        layout = message.get("layout", "force")
        self._layout = layout

        return {
            "action": "layout_changed",
            "layout": layout,
        }

    def _handle_update_filters(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理过滤器更新"""
        filters = message.get("filters", {})
        self._filters.update(filters)

        return {
            "action": "filters_updated",
            "filters": self._filters,
        }

    def _handle_get_node_details(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """获取节点详细信息"""
        node_id = message.get("node_id")
        graph = self.get_graph()

        if not graph or node_id not in graph.nodes:
            return {"error": "Node not found"}

        node = graph.nodes[node_id]

        # 获取调用关系
        call_graph = graph.get_call_graph(node.name)

        return {
            "action": "node_details",
            "node": node.to_dict(),
            "call_graph": call_graph,
        }
