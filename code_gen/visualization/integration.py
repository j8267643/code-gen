"""Visualization Integration - 可视化系统集成

将可视化界面集成到现有系统中
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import asyncio
import logging

from code_gen.visualization.web import VisualizationServer
from code_gen.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class VisualizationIntegration:
    """可视化系统集成器

    将 Web 可视化界面作为常驻插件集成到系统中
    """

    def __init__(
        self,
        graph: Optional[KnowledgeGraph] = None,
        auto_start: bool = True,
        host: str = "127.0.0.1",
        port: int = 8080,
    ):
        self.graph = graph or KnowledgeGraph()
        self.server = VisualizationServer(self.graph, host, port)
        self._task: Optional[asyncio.Task] = None
        self._auto_start = auto_start

    async def start(self):
        """启动可视化服务"""
        if self._task is None:
            self._task = asyncio.create_task(self.server.start())
            # 等待服务器实际启动
            await asyncio.sleep(0.5)
            logger.info(f"Visualization service started at http://{self.server.host}:{self.server.port}")

    def stop(self):
        """停止可视化服务"""
        if self._task:
            self.server.stop()
            self._task.cancel()
            self._task = None
            logger.info("Visualization service stopped")

    def is_running(self) -> bool:
        """检查服务是否运行"""
        return self._task is not None and not self._task.done()

    def get_url(self) -> str:
        """获取访问地址"""
        return f"http://{self.server.host}:{self.server.port}"


# 全局实例
_visualization: Optional[VisualizationIntegration] = None


def init_visualization(
    graph: Optional[KnowledgeGraph] = None,
    auto_start: bool = True,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> VisualizationIntegration:
    """初始化可视化系统

    Args:
        graph: 知识图谱实例
        auto_start: 是否自动启动
        host: 主机地址
        port: 端口号

    Returns:
        VisualizationIntegration 实例
    """
    global _visualization
    _visualization = VisualizationIntegration(graph, auto_start, host, port)

    if auto_start:
        asyncio.create_task(_visualization.start())

    return _visualization


def get_visualization() -> Optional[VisualizationIntegration]:
    """获取可视化实例"""
    return _visualization


def stop_visualization():
    """停止可视化服务"""
    global _visualization
    if _visualization:
        _visualization.stop()
        _visualization = None
