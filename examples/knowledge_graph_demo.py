"""Knowledge Graph Demo - 知识图谱演示

演示代码知识图谱的功能：
1. 索引代码
2. 查询符号
3. 分析影响
4. 获取上下文
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.knowledge_graph import (
    KnowledgeGraph,
    CodeIndexer,
    ImpactAnalyzer,
    NodeType,
)
from code_gen.knowledge_graph.integration import (
    CodeContextProvider,
    KnowledgeGraphTool,
)


async def demo_indexing():
    """演示代码索引"""
    print("=" * 60)
    print("1. 代码索引演示")
    print("=" * 60)

    # 创建知识图谱
    graph = KnowledgeGraph()
    indexer = CodeIndexer(graph)

    # 索引当前项目
    project_path = Path(__file__).parent.parent / "code_gen"
    print(f"\n索引项目: {project_path}")

    stats = indexer.index_directory(project_path)

    print(f"\n索引完成!")
    print(f"  - 索引文件数: {stats['total_files_indexed']}")
    print(f"  - 总节点数: {stats['total_nodes']}")
    print(f"  - 总边数: {stats['total_edges']}")
    print(f"\n节点类型分布:")
    for node_type, count in stats['node_types'].items():
        print(f"    - {node_type}: {count}")

    return graph


async def demo_query(graph: KnowledgeGraph):
    """演示查询功能"""
    print("\n" + "=" * 60)
    print("2. 代码查询演示")
    print("=" * 60)

    # 查找类
    classes = graph.get_nodes_by_type(NodeType.CLASS)
    print(f"\n找到 {len(classes)} 个类")

    if classes:
        print("\n前5个类:")
        for cls in classes[:5]:
            print(f"  - {cls.name}")
            if cls.signature:
                print(f"    签名: {cls.signature}")

    # 查找函数
    functions = graph.get_nodes_by_type(NodeType.FUNCTION)
    print(f"\n找到 {len(functions)} 个函数")

    if functions:
        print("\n前5个函数:")
        for func in functions[:5]:
            print(f"  - {func.name}")


async def demo_impact_analysis(graph: KnowledgeGraph):
    """演示影响分析"""
    print("\n" + "=" * 60)
    print("3. 影响分析演示")
    print("=" * 60)

    analyzer = ImpactAnalyzer(graph)

    # 找一个有调用关系的函数进行分析
    functions = graph.get_nodes_by_type(NodeType.FUNCTION)

    if not functions:
        print("没有找到函数，跳过影响分析")
        return

    # 选择第一个函数进行分析
    target_func = functions[0]
    print(f"\n分析函数: {target_func.name}")
    print(f"文件: {target_func.file_path}")

    try:
        result = analyzer.analyze(target_func, direction="both", max_depth=2)

        print(f"\n影响分析结果:")
        print(analyzer.get_quick_summary(result))

        if result.recommendations:
            print(f"\n💡 建议:")
            for rec in result.recommendations:
                print(f"  - {rec}")

    except Exception as e:
        print(f"分析失败: {e}")


async def demo_context_provider(graph: KnowledgeGraph):
    """演示上下文提供者"""
    print("\n" + "=" * 60)
    print("4. 上下文提供者演示")
    print("=" * 60)

    provider = CodeContextProvider(graph)
    tool = KnowledgeGraphTool(provider)

    # 演示查询
    print("\n查询 'ActionNode':")
    result = tool.query("ActionNode", limit=5)
    print(result)

    # 演示上下文
    print("\n获取 'ActionNode' 的上下文:")
    context = tool.context("ActionNode")
    # 只显示前500字符
    print(context[:500] + "..." if len(context) > 500 else context)


async def demo_integration():
    """演示完整集成流程"""
    print("\n" + "=" * 60)
    print("5. 完整集成演示")
    print("=" * 60)

    # 创建提供者并索引项目
    provider = CodeContextProvider()

    project_path = Path(__file__).parent.parent / "code_gen" / "knowledge_graph"
    print(f"\n索引知识图谱模块: {project_path}")

    stats = provider.index_project(project_path)
    print(f"索引完成: {stats['total_nodes']} 个节点")

    # 搜索代码
    print("\n搜索 'impact':")
    results = provider.search_code("impact", limit=3)
    for result in results:
        print(f"  - {result['name']} ({result['node_type']})")

    # 获取文件概览
    if results and results[0].get('file_path'):
        file_path = results[0]['file_path']
        print(f"\n文件概览: {file_path}")
        overview = provider.get_file_overview(file_path)
        print(f"  总符号数: {overview['total_symbols']}")
        print(f"  类数: {len(overview['classes'])}")
        print(f"  函数数: {len(overview['functions'])}")

    # 分析影响
    if results:
        symbol_name = results[0]['name']
        print(f"\n分析 '{symbol_name}' 的影响:")
        impact = provider.analyze_change_impact(symbol_name)
        if 'risk_level' in impact:
            print(f"  风险等级: {impact['risk_level']}")
            print(f"  上游调用: {impact['upstream']['count']} 个")
            print(f"  下游依赖: {impact['downstream']['count']} 个")


async def main():
    """主函数"""
    print("\n" + "🚀 " * 20)
    print("代码知识图谱系统演示")
    print("🚀 " * 20 + "\n")

    # 1. 索引代码
    graph = await demo_indexing()

    # 2. 查询演示
    await demo_query(graph)

    # 3. 影响分析
    await demo_impact_analysis(graph)

    # 4. 上下文提供者
    await demo_context_provider(graph)

    # 5. 完整集成
    await demo_integration()

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)
    print("\n知识图谱功能:")
    print("  ✅ 代码索引 - 自动解析 Python 代码结构")
    print("  ✅ 符号查询 - 快速查找类、函数、变量")
    print("  ✅ 影响分析 - 分析变更的 blast radius")
    print("  ✅ 上下文提供 - 为 Agent 提供代码上下文")
    print("  ✅ 工具集成 - 可作为 MCP 工具使用")


if __name__ == "__main__":
    asyncio.run(main())
