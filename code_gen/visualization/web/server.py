"""Visualization Server - Web 可视化服务器

提供 HTTP API 和 WebSocket 服务
"""

from __future__ import annotations

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Set
from dataclasses import asdict
import logging

from .plugin_manager import PluginManager, PluginInfo
from .plugins import GraphViewerPlugin, SearchPanelPlugin, ImpactViewerPlugin

logger = logging.getLogger(__name__)


class VisualizationServer:
    """可视化服务器

    提供 HTTP API 和 WebSocket 服务
    """

    def __init__(
        self,
        graph,
        host: str = "127.0.0.1",
        port: int = 8080,
    ):
        self.graph = graph
        self.host = host
        self.port = port
        self.plugin_manager = PluginManager()
        self._clients: Set = set()
        self._running = False

    def register_default_plugins(self):
        """注册默认插件"""
        # 注册图谱查看器
        self.plugin_manager.register(
            GraphViewerPlugin,
            PluginInfo(
                id="graph_viewer",
                name="代码图谱",
                description="可视化展示代码知识图谱",
                version="1.0.0",
                author="CodeGen",
                icon="🕸️",
                position="panel",
                order=1,
            )
        )

        # 注册搜索面板
        self.plugin_manager.register(
            SearchPanelPlugin,
            PluginInfo(
                id="search_panel",
                name="代码搜索",
                description="智能代码搜索",
                version="1.0.0",
                author="CodeGen",
                icon="🔍",
                position="sidebar",
                order=1,
            )
        )

        # 注册影响分析器
        self.plugin_manager.register(
            ImpactViewerPlugin,
            PluginInfo(
                id="impact_viewer",
                name="影响分析",
                description="分析代码变更影响",
                version="1.0.0",
                author="CodeGen",
                icon="⚡",
                position="panel",
                order=2,
            )
        )

    def init_plugins(self):
        """初始化所有插件"""
        context = {
            'graph': self.graph,
            'server': self,
        }
        self.plugin_manager.init_all(context)

    async def start(self):
        """启动服务器"""
        try:
            from aiohttp import web

            # 注册默认插件
            self.register_default_plugins()
            self.init_plugins()

            # 创建应用
            app = web.Application()
            app.router.add_get('/', self._handle_index)
            app.router.add_get('/api/plugins', self._handle_get_plugins)
            app.router.add_post('/api/plugin/{id}/message', self._handle_plugin_message)
            app.router.add_get('/api/graph/stats', self._handle_graph_stats)
            app.router.add_get('/api/graph/search', self._handle_graph_search)
            app.router.add_static('/static', Path(__file__).parent / 'static')

            # WebSocket
            app.router.add_get('/ws', self._handle_websocket)

            runner = web.AppRunner(app)
            await runner.setup()

            site = web.TCPSite(runner, self.host, self.port)
            await site.start()

            self._running = True
            logger.info(f"Visualization server started at http://{self.host}:{self.port}")

            # 保持运行
            while self._running:
                await asyncio.sleep(1)

        except ImportError:
            logger.error("aiohttp not installed. Run: pip install aiohttp")
            raise

    def stop(self):
        """停止服务器"""
        self._running = False
        self.plugin_manager.destroy_all()
        logger.info("Visualization server stopped")

    async def _handle_index(self, request):
        """处理首页请求"""
        from aiohttp import web

        html = self._generate_html()
        return web.Response(text=html, content_type='text/html')

    async def _handle_get_plugins(self, request):
        """获取插件列表"""
        from aiohttp import web

        plugins = self.plugin_manager.list_plugins()
        data = [asdict(p) for p in plugins]
        return web.json_response({"plugins": data})

    async def _handle_plugin_message(self, request):
        """处理插件消息"""
        from aiohttp import web

        plugin_id = request.match_info['id']
        plugin = self.plugin_manager.get_plugin(plugin_id)

        if not plugin:
            return web.json_response({"error": "Plugin not found"}, status=404)

        try:
            data = await request.json()
            result = plugin.handle_message(data)
            return web.json_response(result or {})
        except Exception as e:
            logger.error(f"Plugin message error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_graph_stats(self, request):
        """获取图谱统计"""
        from aiohttp import web

        stats = {
            "total_nodes": len(self.graph.nodes),
            "total_edges": len(self.graph.edges),
            "node_types": {},
            "languages": {},
        }

        # 统计节点类型
        for node in self.graph:
            node_type = node.node_type.value
            stats["node_types"][node_type] = stats["node_types"].get(node_type, 0) + 1

            # 统计语言
            lang = node.language.value if hasattr(node, 'language') else "unknown"
            stats["languages"][lang] = stats["languages"].get(lang, 0) + 1

        return web.json_response(stats)

    async def _handle_graph_search(self, request):
        """搜索图谱"""
        from aiohttp import web

        query = request.query.get('q', '')
        method = request.query.get('method', 'hybrid')
        limit = int(request.query.get('limit', '10'))

        if not query:
            return web.json_response({"results": []})

        try:
            from code_gen.knowledge_graph import search_code
            results = search_code(query, self.graph, top_k=limit, method=method)

            data = []
            for result in results:
                data.append({
                    "id": result.node.id,
                    "name": result.node.name,
                    "type": result.node.node_type.value,
                    "language": result.node.language.value if hasattr(result.node, 'language') else "unknown",
                    "file_path": result.node.file_path,
                    "line": result.node.line_start,
                    "score": result.score,
                })

            return web.json_response({"results": data})

        except Exception as e:
            logger.error(f"Search error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_websocket(self, request):
        """处理 WebSocket 连接"""
        from aiohttp import web

        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._clients.add(ws)

        logger.info(f"WebSocket client connected")

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_ws_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_json({"error": "Invalid JSON"})
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            self._clients.discard(ws)
            logger.info("WebSocket client disconnected")

        return ws

    async def _handle_ws_message(self, ws, data: Dict[str, Any]):
        """处理 WebSocket 消息"""
        message_type = data.get("type")

        if message_type == "plugin_message":
            plugin_id = data.get("plugin_id")
            plugin = self.plugin_manager.get_plugin(plugin_id)

            if plugin:
                result = plugin.handle_message(data.get("data", {}))
                await ws.send_json({
                    "type": "plugin_response",
                    "plugin_id": plugin_id,
                    "data": result,
                })

        elif message_type == "get_plugins":
            plugins = self.plugin_manager.list_plugins()
            await ws.send_json({
                "type": "plugins_list",
                "plugins": [asdict(p) for p in plugins],
            })

        elif message_type == "ping":
            await ws.send_json({"type": "pong"})

    def _generate_html(self) -> str:
        """生成 HTML 页面"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Knowledge Graph - 代码知识图谱</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1e1e1e;
            color: #d4d4d4;
            height: 100vh;
            overflow: hidden;
        }

        /* 三明治布局 */
        .container {
            display: grid;
            grid-template-areas:
                "header header header"
                "sidebar main panel"
                "status status status";
            grid-template-rows: 48px 1fr 28px;
            grid-template-columns: 280px 1fr 320px;
            height: 100vh;
        }

        /* 顶部栏 */
        .header {
            grid-area: header;
            background: #252526;
            border-bottom: 1px solid #3c3c3c;
            display: flex;
            align-items: center;
            padding: 0 16px;
            gap: 16px;
        }

        .header h1 {
            font-size: 14px;
            font-weight: 600;
            color: #cccccc;
        }

        .header .search-box {
            flex: 1;
            max-width: 400px;
            position: relative;
        }

        .header .search-box input {
            width: 100%;
            padding: 6px 12px 6px 32px;
            background: #3c3c3c;
            border: 1px solid #3c3c3c;
            border-radius: 4px;
            color: #cccccc;
            font-size: 13px;
        }

        .header .search-box input:focus {
            outline: none;
            border-color: #007acc;
        }

        /* 侧边栏 */
        .sidebar {
            grid-area: sidebar;
            background: #252526;
            border-right: 1px solid #3c3c3c;
            display: flex;
            flex-direction: column;
        }

        .sidebar-tabs {
            display: flex;
            background: #2d2d30;
            border-bottom: 1px solid #3c3c3c;
        }

        .sidebar-tab {
            flex: 1;
            padding: 10px;
            text-align: center;
            cursor: pointer;
            font-size: 12px;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }

        .sidebar-tab:hover {
            background: #3c3c3c;
        }

        .sidebar-tab.active {
            border-bottom-color: #007acc;
            color: #ffffff;
        }

        .sidebar-content {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
        }

        /* 主内容区 */
        .main {
            grid-area: main;
            background: #1e1e1e;
            position: relative;
            overflow: hidden;
        }

        .main-tabs {
            display: flex;
            background: #2d2d30;
            border-bottom: 1px solid #3c3c3c;
            overflow-x: auto;
        }

        .main-tab {
            padding: 8px 16px;
            cursor: pointer;
            font-size: 12px;
            white-space: nowrap;
            border-right: 1px solid #3c3c3c;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .main-tab:hover {
            background: #3c3c3c;
        }

        .main-tab.active {
            background: #1e1e1e;
            border-bottom: 1px solid #1e1e1e;
            margin-bottom: -1px;
        }

        .main-content {
            height: calc(100% - 36px);
            overflow: auto;
        }

        /* 右侧面板 */
        .panel {
            grid-area: panel;
            background: #252526;
            border-left: 1px solid #3c3c3c;
            display: flex;
            flex-direction: column;
        }

        .panel-header {
            padding: 10px 12px;
            background: #2d2d30;
            border-bottom: 1px solid #3c3c3c;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .panel-content {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
        }

        /* 状态栏 */
        .status {
            grid-area: status;
            background: #007acc;
            color: white;
            display: flex;
            align-items: center;
            padding: 0 12px;
            font-size: 12px;
            gap: 16px;
        }

        .status-item {
            display: flex;
            align-items: center;
            gap: 4px;
        }

        /* 搜索结果 */
        .search-result {
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            margin-bottom: 4px;
            transition: background 0.2s;
        }

        .search-result:hover {
            background: #2a2d2e;
        }

        .search-result .name {
            font-size: 13px;
            color: #d4d4d4;
            margin-bottom: 2px;
        }

        .search-result .meta {
            font-size: 11px;
            color: #858585;
        }

        /* 图谱容器 */
        #graph-container {
            width: 100%;
            height: 100%;
            position: relative;
        }

        /* 加载动画 */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            font-size: 14px;
            color: #858585;
        }

        /* 响应式 */
        @media (max-width: 1200px) {
            .container {
                grid-template-columns: 240px 1fr 280px;
            }
        }

        @media (max-width: 900px) {
            .container {
                grid-template-areas:
                    "header header"
                    "sidebar main"
                    "status status";
                grid-template-columns: 200px 1fr;
            }
            .panel {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 顶部栏 -->
        <header class="header">
            <h1>🕸️ Code Knowledge Graph</h1>
            <div class="search-box">
                <input type="text" id="global-search" placeholder="搜索代码... (Ctrl+P)">
            </div>
        </header>

        <!-- 侧边栏 -->
        <aside class="sidebar">
            <div class="sidebar-tabs">
                <div class="sidebar-tab active" data-tab="search">🔍 搜索</div>
                <div class="sidebar-tab" data-tab="explorer">📁 文件</div>
            </div>
            <div class="sidebar-content" id="sidebar-content">
                <div class="loading">加载中...</div>
            </div>
        </aside>

        <!-- 主内容区 -->
        <main class="main">
            <div class="main-tabs">
                <div class="main-tab active" data-tab="graph">
                    🕸️ 代码图谱
                </div>
                <div class="main-tab" data-tab="impact">
                    ⚡ 影响分析
                </div>
            </div>
            <div class="main-content" id="main-content">
                <div id="graph-container">
                    <div class="loading">正在加载图谱...</div>
                </div>
            </div>
        </main>

        <!-- 右侧面板 -->
        <aside class="panel">
            <div class="panel-header">详细信息</div>
            <div class="panel-content" id="panel-content">
                <div class="loading">选择一个节点查看详情</div>
            </div>
        </aside>

        <!-- 状态栏 -->
        <footer class="status">
            <div class="status-item">
                <span>🟢</span>
                <span>已连接</span>
            </div>
            <div class="status-item">
                <span id="node-count">0</span> 节点
            </div>
            <div class="status-item">
                <span id="edge-count">0</span> 边
            </div>
        </footer>
    </div>

    <script>
        // WebSocket 连接
        const ws = new WebSocket(`ws://${window.location.host}/ws`);

        ws.onopen = () => {
            console.log('WebSocket connected');
            // 请求插件列表
            ws.send(JSON.stringify({ type: 'get_plugins' }));
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleMessage(data);
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
        };

        // 处理消息
        function handleMessage(data) {
            switch(data.type) {
                case 'plugins_list':
                    renderPlugins(data.plugins);
                    break;
                case 'plugin_response':
                    handlePluginResponse(data.plugin_id, data.data);
                    break;
                default:
                    console.log('Unknown message:', data);
            }
        }

        // 渲染插件
        function renderPlugins(plugins) {
            const sidebar = document.getElementById('sidebar-content');
            sidebar.innerHTML = plugins.map(p => `
                <div class="search-result" onclick="activatePlugin('${p.id}')">
                    <div class="name">${p.icon} ${p.name}</div>
                    <div class="meta">${p.description}</div>
                </div>
            `).join('');
        }

        // 激活插件
        function activatePlugin(pluginId) {
            ws.send(JSON.stringify({
                type: 'plugin_message',
                plugin_id: pluginId,
                data: { action: 'render' }
            }));
        }

        // 处理插件响应
        function handlePluginResponse(pluginId, data) {
            console.log(`Plugin ${pluginId} response:`, data);
            // 根据插件类型渲染内容
        }

        // 标签页切换
        document.querySelectorAll('.sidebar-tab, .main-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                tab.parentElement.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
            });
        });

        // 全局搜索
        document.getElementById('global-search').addEventListener('input', (e) => {
            const query = e.target.value;
            if (query.length > 2) {
                fetch(`/api/graph/search?q=${encodeURIComponent(query)}`)
                    .then(r => r.json())
                    .then(data => {
                        console.log('Search results:', data);
                    });
            }
        });

        // 加载统计
        fetch('/api/graph/stats')
            .then(r => r.json())
            .then(stats => {
                document.getElementById('node-count').textContent = stats.total_nodes;
                document.getElementById('edge-count').textContent = stats.total_edges;
            });
    </script>
</body>
</html>'''


# 便捷函数
async def start_visualization_server(graph, host: str = "localhost", port: int = 8080):
    """启动可视化服务器"""
    server = VisualizationServer(graph, host, port)
    await server.start()
