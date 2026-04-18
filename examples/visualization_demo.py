"""Visualization Demo - Web 可视化演示

演示如何启动和使用 Web 可视化界面
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.knowledge_graph import KnowledgeGraph, CodeIndexer
from code_gen.visualization import VisualizationServer


async def main():
    """主函数"""
    print("=" * 60)
    print("🎨 Web Visualization Demo - Web 可视化演示")
    print("=" * 60)

    # 1. 创建知识图谱
    print("\n📊 创建知识图谱...")
    graph = KnowledgeGraph()

    # 2. 索引代码
    print("\n🔍 索引代码...")
    indexer = CodeIndexer(graph)

    # 索引当前项目
    project_path = Path(__file__).parent.parent / "code_gen"
    if project_path.exists():
        print(f"   索引目录: {project_path}")
        file_count = 0
        for file_path in project_path.rglob("*.py"):
            if "__pycache__" not in str(file_path):
                indexer.index_file(file_path)
                file_count += 1
                if file_count >= 20:  # 限制数量
                    break

        print(f"   已索引 {file_count} 个文件")

    # 3. 启动可视化服务器
    print("\n🚀 启动可视化服务器...")
    print("   地址: http://localhost:8080")
    print("\n" + "=" * 60)
    print("请打开浏览器访问: http://localhost:8080")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60 + "\n")

    server = VisualizationServer(graph, host="localhost", port=8080)

    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n\n🛑 停止服务器...")
        server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ImportError as e:
        print(f"\n❌ 缺少依赖: {e}")
        print("请安装: pip install aiohttp")
