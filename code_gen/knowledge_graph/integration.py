"""Knowledge Graph Integration - 知识图谱集成

将知识图谱功能集成到现有的 Agent 和 SOP 系统中
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import logging

from .graph import KnowledgeGraph
from .indexer import CodeIndexer
from .impact_analyzer import ImpactAnalyzer, RiskLevel
from .search import HybridSearcher, SearchResult

logger = logging.getLogger(__name__)


class CodeContextProvider:
    """代码上下文提供者

    为 Agent 提供代码相关的上下文信息
    """

    def __init__(self, graph: Optional[KnowledgeGraph] = None):
        self.graph = graph or KnowledgeGraph()
        self.indexer = CodeIndexer(self.graph)
        self.analyzer = ImpactAnalyzer(self.graph)

    def index_project(self, project_path: str | Path) -> Dict[str, Any]:
        """索引整个项目"""
        logger.info(f"Indexing project: {project_path}")
        self.indexer.index_directory(project_path)
        stats = self.indexer.get_statistics()
        logger.info(f"Indexing complete: {stats}")
        return stats

    def get_symbol_context(self, symbol_name: str) -> Dict[str, Any]:
        """获取符号的完整上下文

        包括：
        - 符号定义
        - 调用关系
        - 继承关系
        - 所在文件
        """
        from .graph import NodeType

        node = self.graph.find_node_by_name(symbol_name)
        if not node:
            return {"error": f"Symbol not found: {symbol_name}"}

        context = {
            "symbol": node.to_dict(),
            "callers": [],
            "callees": [],
            "related_files": [],
        }

        # 获取调用关系
        call_graph = self.graph.get_call_graph(symbol_name)
        if call_graph:
            context["callers"] = call_graph.get("called_by", [])
            context["callees"] = call_graph.get("calls", [])

        # 如果是类，获取继承关系
        if node.node_type == NodeType.CLASS:
            hierarchy = self.graph.get_class_hierarchy(symbol_name)
            context["inheritance"] = hierarchy

        # 获取相关文件
        if node.file_path:
            file_nodes = self.graph.get_nodes_by_file(node.file_path)
            context["related_files"] = [n.to_dict() for n in file_nodes[:10]]

        return context

    def analyze_change_impact(
        self,
        symbol_name: str,
        max_depth: int = 3,
    ) -> Dict[str, Any]:
        """分析变更影响"""
        try:
            result = self.analyzer.analyze(
                symbol_name,
                direction="both",
                max_depth=max_depth,
            )
            return result.to_dict()
        except Exception as e:
            logger.error(f"Failed to analyze impact: {e}")
            return {"error": str(e)}

    def search_code(self, query: str, limit: int = 10, method: str = "hybrid") -> List[Dict[str, Any]]:
        """搜索代码

        支持：
        - 精确名称匹配
        - 模糊模式匹配
        - 文件路径匹配
        - 混合搜索 (BM25 + 向量)

        Args:
            query: 查询字符串
            limit: 返回结果数量
            method: 搜索方法 ("exact", "fuzzy", "hybrid")
        """
        if method == "hybrid":
            # 使用混合搜索
            searcher = HybridSearcher()
            search_results = searcher.search(query, self.graph, top_k=limit)
            return [r.to_dict() for r in search_results]

        results = []

        # 1. 精确匹配
        node = self.graph.find_node_by_name(query)
        if node:
            results.append(node.to_dict())

        # 2. 模糊匹配
        if method == "fuzzy" and len(results) < limit:
            pattern_results = self.graph.find_nodes_by_pattern(query)
            for node in pattern_results:
                if len(results) >= limit:
                    break
                node_dict = node.to_dict()
                if node_dict not in results:
                    results.append(node_dict)

        return results

    def get_file_overview(self, file_path: str) -> Dict[str, Any]:
        """获取文件概览"""
        nodes = self.graph.get_nodes_by_file(file_path)

        if not nodes:
            return {"error": f"File not found: {file_path}"}

        # 分类统计
        classes = []
        functions = []
        imports = []

        for node in nodes:
            from .graph import NodeType
            if node.node_type == NodeType.CLASS:
                classes.append(node.to_dict())
            elif node.node_type in (NodeType.FUNCTION, NodeType.METHOD):
                functions.append(node.to_dict())
            elif node.node_type == NodeType.IMPORT:
                imports.append(node.to_dict())

        return {
            "file_path": file_path,
            "total_symbols": len(nodes),
            "classes": classes,
            "functions": functions,
            "imports": imports,
        }

    def suggest_related_symbols(self, symbol_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """建议相关符号"""
        node = self.graph.find_node_by_name(symbol_name)
        if not node:
            return []

        related = []

        # 1. 同文件的符号
        if node.file_path:
            file_nodes = self.graph.get_nodes_by_file(node.file_path)
            for n in file_nodes:
                if n.id != node.id and len(related) < limit:
                    related.append(n.to_dict())

        # 2. 调用关系
        if len(related) < limit:
            neighbors = self.graph.get_neighbors(node.id)
            for n in neighbors:
                if n.id != node.id and len(related) < limit:
                    n_dict = n.to_dict()
                    if n_dict not in related:
                        related.append(n_dict)

        return related


class KnowledgeGraphTool:
    """知识图谱工具

    为 Agent 提供的工具接口
    """

    def __init__(self, provider: Optional[CodeContextProvider] = None):
        self.provider = provider or CodeContextProvider()

    def query(self, query: str, limit: int = 10) -> str:
        """查询代码

        Tool: code_gen.knowledge_graph.query
        """
        results = self.provider.search_code(query, limit)

        if not results:
            return f"未找到与 '{query}' 相关的代码"

        lines = [f"找到 {len(results)} 个相关结果："]
        for i, result in enumerate(results, 1):
            lines.append(f"\n{i}. {result['name']} ({result['node_type']})")
            if result.get('file_path'):
                lines.append(f"   文件: {result['file_path']}")
            if result.get('signature'):
                lines.append(f"   签名: {result['signature']}")

        return "\n".join(lines)

    def context(self, symbol_name: str) -> str:
        """获取符号上下文

        Tool: code_gen.knowledge_graph.context
        """
        context = self.provider.get_symbol_context(symbol_name)

        if "error" in context:
            return f"错误: {context['error']}"

        lines = [
            f"🎯 符号: {context['symbol']['name']}",
            f"类型: {context['symbol']['node_type']}",
        ]

        if context['symbol'].get('file_path'):
            lines.append(f"文件: {context['symbol']['file_path']}")

        if context['symbol'].get('signature'):
            lines.append(f"签名: {context['symbol']['signature']}")

        if context['callers']:
            lines.append(f"\n📞 被调用 ({len(context['callers'])} 次):")
            for caller in context['callers'][:5]:
                lines.append(f"  - {caller['name']}")

        if context['callees']:
            lines.append(f"\n📤 调用 ({len(context['callees'])} 次):")
            for callee in context['callees'][:5]:
                lines.append(f"  - {callee['name']}")

        return "\n".join(lines)

    def impact(self, symbol_name: str) -> str:
        """分析变更影响

        Tool: code_gen.knowledge_graph.impact
        """
        result = self.provider.analyze_change_impact(symbol_name)

        if "error" in result:
            return f"错误: {result['error']}"

        lines = [
            f"🎯 目标: {result['target']['name']}",
            f"⚡ 风险等级: {result['risk_level'].upper()}",
            f"\n📊 影响范围:",
            f"  - 上游调用方: {result['upstream']['count']} 个",
            f"  - 下游依赖: {result['downstream']['count']} 个",
            f"  - 涉及文件: {result['statistics']['total_affected_files']} 个",
        ]

        if result.get('risk_factors'):
            lines.append(f"\n⚠️ 风险因素:")
            for factor in result['risk_factors']:
                lines.append(f"  - {factor}")

        if result.get('recommendations'):
            lines.append(f"\n💡 建议:")
            for rec in result['recommendations']:
                lines.append(f"  - {rec}")

        return "\n".join(lines)

    def file_overview(self, file_path: str) -> str:
        """获取文件概览

        Tool: code_gen.knowledge_graph.file_overview
        """
        overview = self.provider.get_file_overview(file_path)

        if "error" in overview:
            return f"错误: {overview['error']}"

        lines = [
            f"📄 文件: {overview['file_path']}",
            f"总符号数: {overview['total_symbols']}",
        ]

        if overview['classes']:
            lines.append(f"\n🔷 类 ({len(overview['classes'])}):")
            for cls in overview['classes'][:5]:
                lines.append(f"  - {cls['name']}")

        if overview['functions']:
            lines.append(f"\n🔶 函数 ({len(overview['functions'])}):")
            for func in overview['functions'][:5]:
                lines.append(f"  - {func['name']}")

        return "\n".join(lines)


def create_knowledge_graph_hook(provider: CodeContextProvider) -> Callable:
    """创建知识图谱钩子

    可以在 Agent 执行前/后自动索引代码
    """
    async def before_execution_hook(action, inputs):
        """执行前钩子 - 确保代码已索引"""
        # 如果图谱为空，自动索引当前项目
        if len(provider.graph) == 0:
            logger.info("Knowledge graph is empty, indexing project...")
            # 尝试索引当前目录
            current_dir = Path.cwd()
            if (current_dir / "code_gen").exists():
                provider.index_project(current_dir)

    return before_execution_hook


# 全局实例（单例模式）
_global_provider: Optional[CodeContextProvider] = None

def get_global_provider() -> CodeContextProvider:
    """获取全局代码上下文提供者"""
    global _global_provider
    if _global_provider is None:
        _global_provider = CodeContextProvider()
    return _global_provider
