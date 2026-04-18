"""Storage Demo - 持久化存储演示

演示知识图谱的持久化存储功能：
1. JSON 文件存储
2. SQLite 数据库存储
3. 存储管理器使用
4. 增量更新
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.knowledge_graph import (
    KnowledgeGraph,
    CodeIndexer,
    JSONStorage,
    SQLiteStorage,
    StorageManager,
    save_graph,
    load_graph,
)


async def demo_json_storage():
    """演示 JSON 存储"""
    print("=" * 60)
    print("1. JSON 文件存储")
    print("=" * 60)

    # 创建知识图谱
    graph = KnowledgeGraph()
    indexer = CodeIndexer(graph)

    # 索引代码
    project_path = Path(__file__).parent.parent / "code_gen" / "knowledge_graph"
    print(f"\n索引项目: {project_path}")
    stats = indexer.index_directory(project_path)
    print(f"索引完成: {stats['total_nodes']} 个节点, {stats['total_edges']} 条边")

    # 保存到 JSON
    json_path = Path("demo_graph.json")
    storage = JSONStorage(json_path)

    print(f"\n保存到 JSON: {json_path}")
    success = storage.save(graph)
    print(f"保存{'成功' if success else '失败'}")

    # 检查文件大小
    if json_path.exists():
        size = json_path.stat().st_size
        print(f"文件大小: {size / 1024:.2f} KB")

    # 从 JSON 加载
    print(f"\n从 JSON 加载...")
    loaded_graph = storage.load()
    if loaded_graph:
        print(f"加载成功: {len(loaded_graph)} 个节点, {len(loaded_graph.edges)} 条边")

    # 清理
    storage.clear()
    print(f"\n已清理临时文件")


async def demo_sqlite_storage():
    """演示 SQLite 存储"""
    print("\n" + "=" * 60)
    print("2. SQLite 数据库存储")
    print("=" * 60)

    # 创建知识图谱
    graph = KnowledgeGraph()
    indexer = CodeIndexer(graph)

    # 索引代码
    project_path = Path(__file__).parent.parent / "code_gen" / "knowledge_graph"
    print(f"\n索引项目: {project_path}")
    stats = indexer.index_directory(project_path)
    print(f"索引完成: {stats['total_nodes']} 个节点, {stats['total_edges']} 条边")

    # 保存到 SQLite
    db_path = Path("demo_graph.db")
    storage = SQLiteStorage(db_path)

    print(f"\n保存到 SQLite: {db_path}")
    success = storage.save(graph)
    print(f"保存{'成功' if success else '失败'}")

    # 检查文件大小
    if db_path.exists():
        size = db_path.stat().st_size
        print(f"数据库大小: {size / 1024:.2f} KB")

    # 执行查询
    print(f"\n执行 SQL 查询:")
    results = storage.query(
        "SELECT node_type, COUNT(*) as count FROM nodes GROUP BY node_type"
    )
    print("节点类型统计:")
    for row in results:
        print(f"  - {row['node_type']}: {row['count']} 个")

    # 从 SQLite 加载
    print(f"\n从 SQLite 加载...")
    loaded_graph = storage.load()
    if loaded_graph:
        print(f"加载成功: {len(loaded_graph)} 个节点, {len(loaded_graph.edges)} 条边")

    # 清理
    storage.clear()
    print(f"\n已清理数据库")


async def demo_storage_manager():
    """演示存储管理器"""
    print("\n" + "=" * 60)
    print("3. 存储管理器")
    print("=" * 60)

    # 创建图谱
    graph = KnowledgeGraph()
    indexer = CodeIndexer(graph)

    project_path = Path(__file__).parent.parent / "code_gen" / "knowledge_graph"
    print(f"\n索引项目...")
    indexer.index_directory(project_path)

    # 使用存储管理器
    print("\n使用 JSON 存储管理器:")
    manager = StorageManager.create_json("demo_manager.json")

    print("  保存图谱...")
    manager.save(graph)

    print("  检查存储是否存在...")
    print(f"  存储存在: {manager.exists()}")

    print("  加载图谱...")
    loaded = manager.load()
    print(f"  加载成功: {len(loaded)} 个节点")

    print("  清空存储...")
    manager.clear()
    print(f"  存储存在: {manager.exists()}")

    # SQLite 存储管理器
    print("\n使用 SQLite 存储管理器:")
    manager = StorageManager.create_sqlite("demo_manager.db")

    print("  保存图谱...")
    manager.save(graph)

    print("  加载或创建...")
    loaded = manager.load_or_create()
    print(f"  图谱节点数: {len(loaded)}")

    manager.clear()


async def demo_incremental_update():
    """演示增量更新"""
    print("\n" + "=" * 60)
    print("4. 增量更新场景")
    print("=" * 60)

    db_path = Path("demo_incremental.db")
    storage = SQLiteStorage(db_path)
    manager = StorageManager(storage)

    # 第一次索引
    print("\n第一次索引 (部分代码)...")
    graph1 = KnowledgeGraph()
    indexer1 = CodeIndexer(graph1)

    # 只索引部分代码
    partial_path = Path(__file__).parent.parent / "code_gen" / "knowledge_graph" / "graph.py"
    indexer1.index_file(partial_path)

    print(f"索引结果: {len(graph1)} 个节点")
    manager.save(graph1)

    # 第二次索引（完整）
    print("\n第二次索引 (完整代码)...")
    graph2 = KnowledgeGraph()
    indexer2 = CodeIndexer(graph2)

    full_path = Path(__file__).parent.parent / "code_gen" / "knowledge_graph"
    stats = indexer2.index_directory(full_path)

    print(f"索引结果: {stats['total_nodes']} 个节点")
    manager.save(graph2)

    # 加载验证
    print("\n验证保存结果...")
    loaded = manager.load()
    print(f"加载的图谱: {len(loaded)} 个节点, {len(loaded.edges)} 条边")

    manager.clear()


async def demo_convenience_functions():
    """演示便捷函数"""
    print("\n" + "=" * 60)
    print("5. 便捷函数")
    print("=" * 60)

    # 创建图谱
    graph = KnowledgeGraph()
    indexer = CodeIndexer(graph)

    project_path = Path(__file__).parent.parent / "code_gen" / "knowledge_graph"
    indexer.index_directory(project_path)

    # 使用便捷函数保存
    print("\n使用便捷函数保存...")
    filepath = "demo_convenience.json"
    success = save_graph(graph, filepath)
    print(f"保存{'成功' if success else '失败'}")

    # 使用便捷函数加载
    print("使用便捷函数加载...")
    loaded = load_graph(filepath)
    if loaded:
        print(f"加载成功: {len(loaded)} 个节点")

    # 清理
    Path(filepath).unlink(missing_ok=True)
    print("已清理")


async def demo_performance_comparison():
    """演示性能对比"""
    print("\n" + "=" * 60)
    print("6. 性能对比")
    print("=" * 60)

    import time

    # 创建图谱
    graph = KnowledgeGraph()
    indexer = CodeIndexer(graph)

    project_path = Path(__file__).parent.parent / "code_gen" / "knowledge_graph"
    indexer.index_directory(project_path)

    print(f"\n图谱大小: {len(graph)} 个节点, {len(graph.edges)} 条边")

    # JSON 性能
    print("\nJSON 存储:")
    json_storage = JSONStorage("demo_perf.json")

    start = time.time()
    json_storage.save(graph)
    json_save_time = time.time() - start
    print(f"  保存时间: {json_save_time:.3f}s")

    start = time.time()
    json_loaded = json_storage.load()
    json_load_time = time.time() - start
    print(f"  加载时间: {json_load_time:.3f}s")

    json_size = Path("demo_perf.json").stat().st_size
    print(f"  文件大小: {json_size / 1024:.2f} KB")

    # SQLite 性能
    print("\nSQLite 存储:")
    sqlite_storage = SQLiteStorage("demo_perf.db")

    start = time.time()
    sqlite_storage.save(graph)
    sqlite_save_time = time.time() - start
    print(f"  保存时间: {sqlite_save_time:.3f}s")

    start = time.time()
    sqlite_loaded = sqlite_storage.load()
    sqlite_load_time = time.time() - start
    print(f"  加载时间: {sqlite_load_time:.3f}s")

    sqlite_size = Path("demo_perf.db").stat().st_size
    print(f"  数据库大小: {sqlite_size / 1024:.2f} KB")

    # 总结
    print("\n对比总结:")
    print(f"  JSON  保存快 {json_save_time/sqlite_save_time:.1f}x" if json_save_time < sqlite_save_time else f"  SQLite 保存快 {sqlite_save_time/json_save_time:.1f}x")
    print(f"  JSON  加载快 {json_load_time/sqlite_load_time:.1f}x" if json_load_time < sqlite_load_time else f"  SQLite 加载快 {sqlite_load_time/json_load_time:.1f}x")
    print(f"  {'JSON' if json_size < sqlite_size else 'SQLite'} 体积更小")

    # 清理
    json_storage.clear()
    sqlite_storage.clear()


async def main():
    """主函数"""
    print("\n" + "💾 " * 20)
    print("持久化存储系统演示")
    print("💾 " * 20 + "\n")

    await demo_json_storage()
    await demo_sqlite_storage()
    await demo_storage_manager()
    await demo_incremental_update()
    await demo_convenience_functions()
    await demo_performance_comparison()

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)
    print("\n存储方案对比:")
    print("  JSON:")
    print("    ✅ 简单易用，无需依赖")
    print("    ✅ 人类可读，便于调试")
    print("    ✅ 适合小型项目")
    print("    ⚠️  不适合大量数据")
    print("    ⚠️  不支持复杂查询")
    print("\n  SQLite:")
    print("    ✅ 支持复杂 SQL 查询")
    print("    ✅ 支持索引，查询更快")
    print("    ✅ 适合大型项目")
    print("    ✅ 支持增量更新")
    print("    ⚠️  需要 SQLite 依赖")
    print("\n  推荐:")
    print("    • 开发/调试: JSON")
    print("    • 生产环境: SQLite")


if __name__ == "__main__":
    asyncio.run(main())
