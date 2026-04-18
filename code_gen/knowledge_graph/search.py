"""Hybrid Search - 混合搜索模块

结合 BM25 关键词搜索和向量语义搜索
使用 Reciprocal Rank Fusion (RRF) 融合排序
灵感来源于 GitNexus 的混合搜索实现
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import logging

from .graph import Node, KnowledgeGraph

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜索结果"""
    node: Node
    score: float
    rank: int = 0
    source: str = ""  # "bm25", "vector", "hybrid"
    matched_terms: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": self.node.to_dict(),
            "score": self.score,
            "rank": self.rank,
            "source": self.source,
            "matched_terms": self.matched_terms,
        }


class BM25Searcher:
    """BM25 关键词搜索

    基于词频和文档长度的经典检索算法
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1  # 词频饱和参数
        self.b = b    # 文档长度归一化参数
        self.avg_doc_length = 0.0
        self.doc_freqs: Dict[str, int] = {}  # 词项文档频率
        self.doc_lengths: Dict[str, int] = {}  # 文档长度
        self.total_docs = 0
        self.indexed = False

    def index(self, graph: KnowledgeGraph):
        """构建 BM25 索引"""
        logger.info("Building BM25 index...")

        total_length = 0
        term_doc_freq: Dict[str, set] = {}

        for node in graph:
            # 构建文档文本
            doc_text = self._get_node_text(node)
            doc_id = node.id

            # 分词
            terms = self._tokenize(doc_text)
            self.doc_lengths[doc_id] = len(terms)
            total_length += len(terms)

            # 统计词项文档频率
            unique_terms = set(terms)
            for term in unique_terms:
                if term not in term_doc_freq:
                    term_doc_freq[term] = set()
                term_doc_freq[term].add(doc_id)

        self.total_docs = len(graph.nodes)
        self.avg_doc_length = total_length / self.total_docs if self.total_docs > 0 else 0

        # 转换为文档频率计数
        self.doc_freqs = {term: len(docs) for term, docs in term_doc_freq.items()}

        self.indexed = True
        logger.info(f"BM25 index built: {self.total_docs} docs, {len(self.doc_freqs)} terms")

    def search(self, query: str, graph: KnowledgeGraph, top_k: int = 10) -> List[SearchResult]:
        """BM25 搜索"""
        if not self.indexed:
            self.index(graph)

        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        scores: Dict[str, float] = {}
        matched_terms: Dict[str, List[str]] = {}

        for node in graph:
            doc_id = node.id
            doc_text = self._get_node_text(node)
            doc_terms = self._tokenize(doc_text)

            score = 0.0
            matched = []

            for term in query_terms:
                if term in doc_terms:
                    term_score = self._calc_bm25_score(term, doc_terms)
                    score += term_score
                    matched.append(term)

            if score > 0:
                scores[doc_id] = score
                matched_terms[doc_id] = matched

        # 排序并返回结果
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results = []
        for rank, (doc_id, score) in enumerate(sorted_results[:top_k], 1):
            node = graph.get_node(doc_id)
            if node:
                results.append(SearchResult(
                    node=node,
                    score=score,
                    rank=rank,
                    source="bm25",
                    matched_terms=matched_terms.get(doc_id, [])
                ))

        return results

    def _calc_bm25_score(self, term: str, doc_terms: List[str]) -> float:
        """计算单个词项的 BM25 分数"""
        doc_id = None  # 简化处理，实际需要文档ID

        # 词频
        tf = doc_terms.count(term)

        # 文档频率
        df = self.doc_freqs.get(term, 0)

        # IDF
        idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1)

        # 文档长度归一化
        doc_len = len(doc_terms)
        norm = 1 - self.b + self.b * (doc_len / self.avg_doc_length) if self.avg_doc_length > 0 else 1

        # BM25 公式
        score = idf * ((tf * (self.k1 + 1)) / (tf + self.k1 * norm))

        return score

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        # 转换为小写，提取单词
        text = text.lower()
        words = re.findall(r'\b[a-z][a-z0-9_]*\b', text)

        # 过滤停用词
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                     'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                     'through', 'during', 'before', 'after', 'above', 'below',
                     'between', 'under', 'and', 'but', 'or', 'yet', 'so',
                     'if', 'because', 'although', 'though', 'while', 'where',
                     'when', 'that', 'which', 'who', 'whom', 'whose', 'what',
                     'this', 'these', 'those', 'i', 'me', 'my', 'myself', 'we',
                     'our', 'ours', 'ourselves', 'you', 'your', 'yours',
                     'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
                     'she', 'her', 'hers', 'herself', 'it', 'its', 'itself',
                     'they', 'them', 'their', 'theirs', 'themselves', 'def',
                     'class', 'return', 'if', 'else', 'elif', 'for', 'while',
                     'try', 'except', 'finally', 'with', 'import', 'from',
                     'as', 'pass', 'break', 'continue', 'raise', 'yield',
                     'lambda', 'global', 'nonlocal', 'assert', 'del', 'print'}

        return [w for w in words if w not in stop_words and len(w) > 1]

    def _get_node_text(self, node: Node) -> str:
        """获取节点的文本表示"""
        text_parts = [node.name]

        if node.signature:
            text_parts.append(node.signature)

        if node.source_code:
            # 只取前500字符
            code = node.source_code[:500]
            text_parts.append(code)

        # 添加属性
        for key, value in node.properties.items():
            if isinstance(value, str):
                text_parts.append(value)
            elif isinstance(value, list):
                text_parts.extend(str(v) for v in value if isinstance(v, str))

        return ' '.join(text_parts)


class SimpleEmbedding:
    """简单嵌入生成器

    使用简单的词袋模型作为嵌入的简化版本
    实际应用中应该使用真正的 embedding 模型（如 OpenAI, sentence-transformers）
    """

    def __init__(self, dim: int = 128):
        self.dim = dim
        self.vocab: Dict[str, int] = {}

    def embed(self, text: str) -> List[float]:
        """生成文本嵌入"""
        # 分词
        words = re.findall(r'\b[a-z][a-z0-9_]*\b', text.lower())

        # 构建词袋向量
        vector = [0.0] * self.dim

        for word in words:
            # 使用哈希确定位置
            idx = hash(word) % self.dim
            vector[idx] += 1.0

        # 归一化
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        return dot_product


class VectorSearcher:
    """向量语义搜索"""

    def __init__(self):
        self.embedder = SimpleEmbedding()
        self.doc_embeddings: Dict[str, List[float]] = {}
        self.indexed = False

    def index(self, graph: KnowledgeGraph):
        """构建向量索引"""
        logger.info("Building vector index...")

        for node in graph:
            doc_text = self._get_node_text(node)
            embedding = self.embedder.embed(doc_text)
            self.doc_embeddings[node.id] = embedding

        self.indexed = True
        logger.info(f"Vector index built: {len(self.doc_embeddings)} docs")

    def search(self, query: str, graph: KnowledgeGraph, top_k: int = 10) -> List[SearchResult]:
        """向量搜索"""
        if not self.indexed:
            self.index(graph)

        # 生成查询向量
        query_vec = self.embedder.embed(query)

        # 计算相似度
        scores: Dict[str, float] = {}

        for doc_id, doc_vec in self.doc_embeddings.items():
            similarity = self.embedder.similarity(query_vec, doc_vec)
            if similarity > 0:
                scores[doc_id] = similarity

        # 排序
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results = []
        for rank, (doc_id, score) in enumerate(sorted_results[:top_k], 1):
            node = graph.get_node(doc_id)
            if node:
                results.append(SearchResult(
                    node=node,
                    score=score,
                    rank=rank,
                    source="vector"
                ))

        return results

    def _get_node_text(self, node: Node) -> str:
        """获取节点的文本表示"""
        text_parts = [node.name, node.node_type.value]

        if node.signature:
            text_parts.append(node.signature)

        if node.source_code:
            text_parts.append(node.source_code[:500])

        return ' '.join(text_parts)


class HybridSearcher:
    """混合搜索

    结合 BM25 和向量搜索，使用 RRF 融合排序
    """

    def __init__(self, k: int = 60):
        self.bm25_searcher = BM25Searcher()
        self.vector_searcher = VectorSearcher()
        self.k = k  # RRF 常数
        self.indexed = False

    def index(self, graph: KnowledgeGraph):
        """构建索引"""
        self.bm25_searcher.index(graph)
        self.vector_searcher.index(graph)
        self.indexed = True
        logger.info("Hybrid search index built")

    def search(
        self,
        query: str,
        graph: KnowledgeGraph,
        top_k: int = 10,
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
    ) -> List[SearchResult]:
        """混合搜索

        Args:
            query: 查询字符串
            graph: 知识图谱
            top_k: 返回结果数量
            bm25_weight: BM25 权重
            vector_weight: 向量搜索权重

        Returns:
            融合后的搜索结果
        """
        if not self.indexed:
            self.index(graph)

        # 分别搜索
        bm25_results = self.bm25_searcher.search(query, graph, top_k * 2)
        vector_results = self.vector_searcher.search(query, graph, top_k * 2)

        # RRF 融合
        fused_results = self._rrf_fusion(bm25_results, vector_results, bm25_weight, vector_weight)

        # 返回 top_k
        return fused_results[:top_k]

    def _rrf_fusion(
        self,
        bm25_results: List[SearchResult],
        vector_results: List[SearchResult],
        bm25_weight: float,
        vector_weight: float,
    ) -> List[SearchResult]:
        """Reciprocal Rank Fusion 融合排序

        RRF 公式: score = Σ (weight / (k + rank))
        """
        # 构建节点ID到结果的映射
        node_scores: Dict[str, Dict[str, Any]] = {}

        # 处理 BM25 结果
        for result in bm25_results:
            doc_id = result.node.id
            if doc_id not in node_scores:
                node_scores[doc_id] = {
                    "node": result.node,
                    "rrf_score": 0.0,
                    "sources": [],
                    "matched_terms": [],
                }
            # RRF 分数
            rrf_score = bm25_weight / (self.k + result.rank)
            node_scores[doc_id]["rrf_score"] += rrf_score
            node_scores[doc_id]["sources"].append("bm25")
            node_scores[doc_id]["matched_terms"].extend(result.matched_terms)

        # 处理向量搜索结果
        for result in vector_results:
            doc_id = result.node.id
            if doc_id not in node_scores:
                node_scores[doc_id] = {
                    "node": result.node,
                    "rrf_score": 0.0,
                    "sources": [],
                    "matched_terms": [],
                }
            # RRF 分数
            rrf_score = vector_weight / (self.k + result.rank)
            node_scores[doc_id]["rrf_score"] += rrf_score
            node_scores[doc_id]["sources"].append("vector")

        # 转换为搜索结果
        results = []
        for doc_id, data in node_scores.items():
            # 去重匹配词
            matched_terms = list(set(data["matched_terms"]))

            # 确定来源
            sources = data["sources"]
            if len(sources) == 2:
                source = "hybrid"
            else:
                source = sources[0]

            results.append(SearchResult(
                node=data["node"],
                score=data["rrf_score"],
                source=source,
                matched_terms=matched_terms,
            ))

        # 按 RRF 分数排序
        results.sort(key=lambda x: x.score, reverse=True)

        # 重新设置排名
        for rank, result in enumerate(results, 1):
            result.rank = rank

        return results


# 便捷函数
def search_code(
    query: str,
    graph: KnowledgeGraph,
    top_k: int = 10,
    method: str = "hybrid",
) -> List[SearchResult]:
    """搜索代码的便捷函数

    Args:
        query: 查询字符串
        graph: 知识图谱
        top_k: 返回结果数量
        method: 搜索方法 ("bm25", "vector", "hybrid")

    Returns:
        搜索结果列表
    """
    if method == "bm25":
        searcher = BM25Searcher()
        return searcher.search(query, graph, top_k)
    elif method == "vector":
        searcher = VectorSearcher()
        return searcher.search(query, graph, top_k)
    else:  # hybrid
        searcher = HybridSearcher()
        return searcher.search(query, graph, top_k)
