"""Visualization Simple Demo - 简化版可视化演示"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from aiohttp import web


async def hello(request):
    """测试页面"""
    return web.Response(text="""<!DOCTYPE html>
<html>
<head>
    <title>Code Knowledge Graph</title>
    <style>
        body { font-family: sans-serif; background: #1e1e1e; color: #d4d4d4; padding: 40px; }
        h1 { color: #4A90E2; }
        .container { max-width: 800px; margin: 0 auto; }
        .status { background: #252526; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .success { color: #7ED321; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🕸️ Code Knowledge Graph</h1>
        <div class="status">
            <h2 class="success">✅ 服务运行正常</h2>
            <p>可视化服务器已成功启动！</p>
            <p>访问时间: <span id="time"></span></p>
        </div>
        <div class="status">
            <h3>可用端点:</h3>
            <ul>
                <li><a href="/api/stats" style="color: #4A90E2;">/api/stats</a> - 统计信息</li>
                <li><a href="/api/plugins" style="color: #4A90E2;">/api/plugins</a> - 插件列表</li>
            </ul>
        </div>
    </div>
    <script>
        document.getElementById('time').textContent = new Date().toLocaleString();
    </script>
</body>
</html>""", content_type='text/html')


async def stats(request):
    """统计信息"""
    return web.json_response({
        "status": "running",
        "total_nodes": 42,
        "total_edges": 128,
        "version": "1.0.0"
    })


async def plugins(request):
    """插件列表"""
    return web.json_response({
        "plugins": [
            {"id": "graph_viewer", "name": "代码图谱", "icon": "🕸️"},
            {"id": "search_panel", "name": "代码搜索", "icon": "🔍"},
            {"id": "impact_viewer", "name": "影响分析", "icon": "⚡"},
        ]
    })


async def main():
    """主函数"""
    print("=" * 60)
    print("🎨 Visualization Simple Demo")
    print("=" * 60)

    app = web.Application()
    app.router.add_get('/', hello)
    app.router.add_get('/api/stats', stats)
    app.router.add_get('/api/plugins', plugins)

    runner = web.AppRunner(app)
    await runner.setup()

    # 尝试不同端口
    ports = [8080, 8081, 8082, 3000, 5000]
    site = None
    used_port = None

    for port in ports:
        try:
            site = web.TCPSite(runner, 'localhost', port)
            await site.start()
            used_port = port
            break
        except OSError:
            print(f"   端口 {port} 被占用，尝试下一个...")
            continue

    if not site:
        print("❌ 无法找到可用端口")
        return

    print(f"\n✅ 服务器已启动!")
    print(f"   访问: http://localhost:{used_port}")
    print(f"\n按 Ctrl+C 停止\n")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 停止服务器...")
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
