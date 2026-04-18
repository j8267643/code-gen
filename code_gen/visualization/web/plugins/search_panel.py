"""Search Panel Plugin - 代码搜索面板插件

提供混合搜索功能的可视化界面
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import logging

from .base import VisualizationPlugin
from code_gen.knowledge_graph import HybridSearcher, search_code

logger = logging.getLogger(__name__)


class SearchPanelPlugin(VisualizationPlugin):
    """代码搜索面板插件

    提供类似 IDE 的智能搜索界面
    """

    id = "search_panel"
    name = "代码搜索"
    description = "智能代码搜索，支持关键词和语义搜索"
    icon = "🔍"
    position = "sidebar"
    width = 300

    def __init__(self):
        super().__init__()
        self._searcher = HybridSearcher()
        self._last_query = ""
        self._last_results = []
        self._search_method = "hybrid"  # hybrid, bm25, vector

    def on_init(self):
        """初始化"""
        logger.info("SearchPanelPlugin initialized")

    def on_destroy(self):
        """销毁"""
        logger.info("SearchPanelPlugin destroyed")

    def render(self) -> Dict[str, Any]:
        """渲染搜索面板"""
        return {
            "type": "search_panel",
            "query": self._last_query,
            "method": self._search_method,
            "results": self._format_results(self._last_results),
        }

    def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理前端消息"""
        action = message.get("action")

        if action == "search":
            return self._handle_search(message)
        elif action == "change_method":
            return self._handle_change_method(message)
        elif action == "open_result":
            return self._handle_open_result(message)
        elif action == "get_recent":
            return self._handle_get_recent()

        return None

    def _handle_search(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理搜索请求"""
        query = message.get("query", "")
        self._last_query = query

        graph = self.get_graph()
        if not graph:
            return {"error": "No graph available"}

        try:
            # 执行搜索
            results = search_code(
                query,
                graph,
                top_k=20,
                method=self._search_method
            )

            self._last_results = results

            return {
                "action": "search_complete",
                "query": query,
                "method": self._search_method,
                "result_count": len(results),
                "results": self._format_results(results),
            }

        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"error": str(e)}

    def _handle_change_method(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理搜索方法切换"""
        method = message.get("method", "hybrid")
        self._search_method = method

        # 如果有上一次的查询，重新搜索
        if self._last_query:
            return self._handle_search({"query": self._last_query})

        return {
            "action": "method_changed",
            "method": method,
        }

    def _handle_open_result(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理打开结果"""
        result_id = message.get("result_id")

        # 找到对应的结果
        for result in self._last_results:
            if result.node.id == result_id:
                return {
                    "action": "open_file",
                    "file_path": result.node.file_path,
                    "line": result.node.line_start,
                    "column": getattr(result.node, 'column_start', 0),
                }

        return {"error": "Result not found"}

    def _handle_get_recent(self) -> Dict[str, Any]:
        """获取最近搜索"""
        # 这里可以实现搜索历史
        return {
            "action": "recent_searches",
            "searches": [],
        }

    def _format_results(self, results: List) -> List[Dict[str, Any]]:
        """格式化搜索结果"""
        formatted = []

        for result in results:
            node = result.node

            # 确定图标
            icon = self._get_icon(node.node_type.value)

            # 确定来源标签
            source_tag = {
                "bm25": "关键词",
                "vector": "语义",
                "hybrid": "混合",
            }.get(result.source, result.source)

            formatted.append({
                "id": node.id,
                "icon": icon,
                "name": node.name,
                "type": node.node_type.value,
                "language": node.language.value if hasattr(node, 'language') else "unknown",
                "file_path": node.file_path,
                "line": node.line_start,
                "signature": node.signature,
                "score": round(result.score, 4),
                "source": source_tag,
                "matched_terms": result.matched_terms if hasattr(result, 'matched_terms') else [],
            })

        return formatted

    def _get_icon(self, node_type: str) -> str:
        """获取节点类型图标"""
        icons = {
            "class": "🔷",
            "function": "🔶",
            "method": "📦",
            "interface": "🔌",
            "variable": "📋",
            "import": "📥",
            "file": "📄",
        }
        return icons.get(node_type, "📄")
