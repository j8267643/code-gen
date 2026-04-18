"""Knowledge Graph System - 代码知识图谱系统

灵感来源于 GitNexus 的代码知识图谱实现。
提供代码索引、图查询、影响分析、混合搜索、持久化存储、多语言支持等功能。
"""

from .graph import (
    Node,
    Edge,
    NodeType,
    EdgeType,
    KnowledgeGraph,
    Language,
)
from .indexer import CodeIndexer
from .impact_analyzer import ImpactAnalyzer, RiskLevel, ImpactResult
from .search import (
    BM25Searcher,
    VectorSearcher,
    HybridSearcher,
    SearchResult,
    search_code,
)
from .storage import (
    GraphStorage,
    JSONStorage,
    SQLiteStorage,
    StorageManager,
    save_graph,
    load_graph,
)
from .parsers import (
    BaseParser,
    TypeScriptParser,
)

__all__ = [
    # 图模型
    "Node",
    "Edge",
    "NodeType",
    "EdgeType",
    "KnowledgeGraph",
    "Language",
    # 索引器
    "CodeIndexer",
    # 影响分析
    "ImpactAnalyzer",
    "RiskLevel",
    "ImpactResult",
    # 搜索
    "BM25Searcher",
    "VectorSearcher",
    "HybridSearcher",
    "SearchResult",
    "search_code",
    # 存储
    "GraphStorage",
    "JSONStorage",
    "SQLiteStorage",
    "StorageManager",
    "save_graph",
    "load_graph",
    # 解析器
    "BaseParser",
    "TypeScriptParser",
]
