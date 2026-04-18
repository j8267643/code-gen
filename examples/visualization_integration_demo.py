"""Visualization Integration Demo - 可视化集成演示

演示如何将可视化界面作为常驻插件集成到系统中
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.knowledge_graph import KnowledgeGraph, CodeIndexer
from code_gen.visualization.integration import (
    init_visualization,
    get_visualization,
    stop_visualization,
)


async def simulate_agent_work():
    """模拟 Agent 工作"""
    print("\n🤖 Agent 正在工作...")

    for i in range(5):
        print(f"   执行任务 {i+1}/5...")
        await asyncio.sleep(2)

    print("   ✅ 任务完成")


async def main():
    """主函数"""
    print("=" * 70)
    print("🎨 Visualization Integration Demo - 可视化集成演示")
    print("=" * 70)

    # 1. 创建知识图谱并索引代码
    print("\n📊 准备知识图谱...")
    graph = KnowledgeGraph()
    indexer = CodeIndexer(graph)

    project_path = Path(__file__).parent.parent / "code_gen"
    if project_path.exists():
        file_count = 0
        for file_path in project_path.rglob("*.py"):
            if "__pycache__" not in str(file_path):
                indexer.index_file(file_path)
                file_count += 1
                if file_count >= 30:
                    break
        print(f"   已索引 {file_count} 个文件")

    # 2. 初始化可视化系统（作为常驻插件）
    print("\n🚀 启动可视化服务...")
    viz = init_visualization(
        graph=graph,
        auto_start=True,
        host="localhost",
        port=8080,
    )

    # 等待服务启动
    await asyncio.sleep(1)

    print(f"\n{'='*70}")
    print("✅ 可视化服务已启动！")
    print(f"   访问地址: {viz.get_url()}")
    print(f"{'='*70}\n")

    # 3. 模拟 Agent 工作（可视化服务在后台运行）
    print("💡 此时可视化界面已在后台运行")
    print("   你可以打开浏览器查看代码图谱\n")

    await simulate_agent_work()

    # 4. 保持运行
    print("\n" + "=" * 70)
    print("🔄 可视化服务正在后台运行...")
    print("   按 Ctrl+C 停止")
    print("=" * 70 + "\n")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 停止服务...")
        stop_visualization()
        print("✅ 已停止")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ImportError as e:
        print(f"\n❌ 缺少依赖: {e}")
        print("请安装: pip install aiohttp")
