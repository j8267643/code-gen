"""Hybrid Search Demo - 混合搜索演示

演示混合搜索的功能：
1. BM25 关键词搜索
2. 向量语义搜索
3. RRF 融合排序
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.knowledge_graph import (
    KnowledgeGraph,
    CodeIndexer,
    BM25Searcher,
    VectorSearcher,
    HybridSearcher,
    search_code,
)


async def demo_bm25_search(graph: KnowledgeGraph):
    """演示 BM25 搜索"""
    print("=" * 60)
    print("1. BM25 关键词搜索")
    print("=" * 60)

    searcher = BM25Searcher()

    queries = [
        "impact analyzer",
        "knowledge graph",
        "search code",
    ]

    for query in queries:
        print(f"\n🔍 查询: '{query}'")
        results = searcher.search(query, graph, top_k=5)

        if results:
            print(f"   找到 {len(results)} 个结果:")
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result.node.name} ({result.node.node_type.value})")
                print(f"      分数: {result.score:.4f}")
                if result.matched_terms:
                    print(f"      匹配词: {', '.join(result.matched_terms)}")
        else:
            print("   未找到结果")


async def demo_vector_search(graph: KnowledgeGraph):
    """演示向量搜索"""
    print("\n" + "=" * 60)
    print("2. 向量语义搜索")
    print("=" * 60)

    searcher = VectorSearcher()

    # 语义查询（使用描述性语言）
    queries = [
        "analyze code changes",  # 应该匹配 impact analyzer
        "find related code",     # 应该匹配 search functionality
        "graph structure",       # 应该匹配 knowledge graph
    ]

    for query in queries:
        print(f"\n🔍 查询: '{query}'")
        results = searcher.search(query, graph, top_k=5)

        if results:
            print(f"   找到 {len(results)} 个结果:")
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result.node.name} ({result.node.node_type.value})")
                print(f"      相似度: {result.score:.4f}")
        else:
            print("   未找到结果")


async def demo_hybrid_search(graph: KnowledgeGraph):
    """演示混合搜索"""
    print("\n" + "=" * 60)
    print("3. 混合搜索 (BM25 + 向量)")
    print("=" * 60)

    searcher = HybridSearcher()

    queries = [
        "impact analysis",       # 关键词 + 语义
        "search functionality",  # 关键词 + 语义
        "code indexer",          # 关键词 + 语义
    ]

    for query in queries:
        print(f"\n🔍 查询: '{query}'")
        results = searcher.search(query, graph, top_k=5)

        if results:
            print(f"   找到 {len(results)} 个结果 (RRF 融合排序):")
            for i, result in enumerate(results, 1):
                source_icon = {
                    "bm25": "🔤",
                    "vector": "🧮",
                    "hybrid": "⚡",
                }.get(result.source, "•")

                print(f"   {i}. {source_icon} {result.node.name} ({result.node.node_type.value})")
                print(f"      RRF 分数: {result.score:.4f} | 来源: {result.source}")
                if result.matched_terms:
                    print(f"      匹配词: {', '.join(result.matched_terms)}")
        else:
            print("   未找到结果")


async def demo_search_comparison(graph: KnowledgeGraph):
    """对比不同搜索方法"""
    print("\n" + "=" * 60)
    print("4. 搜索方法对比")
    print("=" * 60)

    query = "analyze code impact"

    print(f"\n查询: '{query}'")
    print("-" * 50)

    # BM25
    print("\nBM25 结果:")
    bm25_results = search_code(query, graph, top_k=3, method="bm25")
    for i, r in enumerate(bm25_results, 1):
        print(f"  {i}. {r['node']['name']} - {r['score']:.4f}")

    # 向量
    print("\n向量搜索结果:")
    vector_results = search_code(query, graph, top_k=3, method="vector")
    for i, r in enumerate(vector_results, 1):
        print(f"  {i}. {r['node']['name']} - {r['score']:.4f}")

    # 混合
    print("\n混合搜索结果:")
    hybrid_results = search_code(query, graph, top_k=3, method="hybrid")
    for i, r in enumerate(hybrid_results, 1):
        source = r.get('source', 'unknown')
        print(f"  {i}. {r['node']['name']} - {r['score']:.4f} [{source}]")


async def demo_advanced_queries(graph: KnowledgeGraph):
    """演示高级查询"""
    print("\n" + "=" * 60)
    print("5. 高级查询场景")
    print("=" * 60)

    searcher = HybridSearcher()

    scenarios = [
        {
            "name": "查找测试相关代码",
            "query": "test validation check",
        },
        {
            "name": "查找配置相关代码",
            "query": "config settings parameters",
        },
        {
            "name": "查找数据处理代码",
            "query": "parse extract transform",
        },
    ]

    for scenario in scenarios:
        print(f"\n📋 场景: {scenario['name']}")
        print(f"   查询: '{scenario['query']}'")

        results = searcher.search(scenario['query'], graph, top_k=3)

        if results:
            print("   结果:")
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result.node.name}")
        else:
            print("   未找到相关代码")


async def main():
    """主函数"""
    print("\n" + "🔍 " * 20)
    print("混合搜索系统演示")
    print("🔍 " * 20 + "\n")

    # 首先索引代码
    print("正在索引代码...")
    graph = KnowledgeGraph()
    indexer = CodeIndexer(graph)

    project_path = Path(__file__).parent.parent / "code_gen" / "knowledge_graph"
    stats = indexer.index_directory(project_path)

    print(f"索引完成: {stats['total_nodes']} 个节点\n")

    # 各种搜索演示
    await demo_bm25_search(graph)
    await demo_vector_search(graph)
    await demo_hybrid_search(graph)
    await demo_search_comparison(graph)
    await demo_advanced_queries(graph)

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)
    print("\n混合搜索特点:")
    print("  ✅ BM25 - 精确关键词匹配，适合找特定函数/类名")
    print("  ✅ 向量搜索 - 语义理解，适合描述性查询")
    print("  ✅ RRF 融合 - 综合两种方法的优势")
    print("  ✅ 自动排序 - 最相关的结果排在前面")
    print("\n应用场景:")
    print("  • 自然语言搜索代码")
    print("  • 查找相关实现")
    print("  • 代码导航和发现")


if __name__ == "__main__":
    asyncio.run(main())
