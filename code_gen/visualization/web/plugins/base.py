"""Base Plugin - 可视化插件基类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class VisualizationPlugin(ABC):
    """可视化插件基类

    所有可视化插件必须继承此类
    """

    # 插件元数据
    id: str = ""
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    icon: str = "📊"

    # UI 配置
    position: str = "sidebar"  # sidebar, panel, modal, floating
    width: Optional[int] = None  # 宽度（像素）
    height: Optional[int] = None  # 高度（像素）
    resizable: bool = True
    collapsible: bool = True

    def __init__(self):
        self._context: Optional[Dict[str, Any]] = None
        self._initialized = False

    def init(self, context: Dict[str, Any]):
        """初始化插件

        Args:
            context: 全局上下文，包含 graph, indexer 等
        """
        self._context = context
        self._initialized = True
        self.on_init()

    def destroy(self):
        """销毁插件"""
        self.on_destroy()
        self._initialized = False
        self._context = None

    @abstractmethod
    def on_init(self):
        """初始化回调，子类实现"""
        pass

    @abstractmethod
    def on_destroy(self):
        """销毁回调，子类实现"""
        pass

    @abstractmethod
    def render(self) -> Dict[str, Any]:
        """渲染插件内容

        Returns:
            渲染数据，格式取决于前端实现
        """
        pass

    @abstractmethod
    def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理前端消息

        Args:
            message: 前端发送的消息

        Returns:
            响应消息（可选）
        """
        pass

    def get_context(self) -> Optional[Dict[str, Any]]:
        """获取全局上下文"""
        return self._context

    def get_graph(self):
        """获取知识图谱"""
        if self._context:
            return self._context.get('graph')
        return None

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    def send_update(self, data: Dict[str, Any]):
        """发送更新到前端"""
        # 通过 WebSocket 或 SSE 发送
        if self._context and 'websocket' in self._context:
            websocket = self._context['websocket']
            # 实现发送逻辑
            pass
