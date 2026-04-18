"""Plugin Manager - 插件管理器

管理可视化插件的注册、加载和生命周期
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type, Any
from dataclasses import dataclass
import logging

from .plugins.base import VisualizationPlugin

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """插件信息"""
    id: str
    name: str
    description: str
    version: str
    author: str
    icon: str = "📊"
    position: str = "sidebar"  # sidebar, panel, modal, floating
    order: int = 0


class PluginManager:
    """插件管理器

    负责插件的注册、加载和管理
    """

    def __init__(self):
        self._plugins: Dict[str, VisualizationPlugin] = {}
        self._plugin_info: Dict[str, PluginInfo] = {}
        self._hooks: Dict[str, List] = {}

    def register(self, plugin_class: Type[VisualizationPlugin], info: PluginInfo) -> bool:
        """注册插件"""
        try:
            plugin = plugin_class()
            plugin_id = info.id

            self._plugins[plugin_id] = plugin
            self._plugin_info[plugin_id] = info

            logger.info(f"Plugin registered: {info.name} ({plugin_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to register plugin: {e}")
            return False

    def unregister(self, plugin_id: str) -> bool:
        """注销插件"""
        if plugin_id in self._plugins:
            plugin = self._plugins[plugin_id]
            plugin.destroy()
            del self._plugins[plugin_id]
            del self._plugin_info[plugin_id]
            logger.info(f"Plugin unregistered: {plugin_id}")
            return True
        return False

    def get_plugin(self, plugin_id: str) -> Optional[VisualizationPlugin]:
        """获取插件实例"""
        return self._plugins.get(plugin_id)

    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self._plugin_info.get(plugin_id)

    def list_plugins(self, position: Optional[str] = None) -> List[PluginInfo]:
        """列出所有插件"""
        plugins = list(self._plugin_info.values())
        if position:
            plugins = [p for p in plugins if p.position == position]
        return sorted(plugins, key=lambda p: p.order)

    def init_all(self, context: Dict[str, Any]):
        """初始化所有插件"""
        for plugin_id, plugin in self._plugins.items():
            try:
                plugin.init(context)
                logger.debug(f"Plugin initialized: {plugin_id}")
            except Exception as e:
                logger.error(f"Failed to initialize plugin {plugin_id}: {e}")

    def destroy_all(self):
        """销毁所有插件"""
        for plugin_id, plugin in self._plugins.items():
            try:
                plugin.destroy()
            except Exception as e:
                logger.error(f"Failed to destroy plugin {plugin_id}: {e}")

    def register_hook(self, event: str, callback):
        """注册钩子"""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def trigger_hook(self, event: str, data: Any = None):
        """触发钩子"""
        if event in self._hooks:
            for callback in self._hooks[event]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Hook error: {e}")

    def get_sidebar_plugins(self) -> List[PluginInfo]:
        """获取侧边栏插件"""
        return self.list_plugins("sidebar")

    def get_panel_plugins(self) -> List[PluginInfo]:
        """获取面板插件"""
        return self.list_plugins("panel")

    def get_floating_plugins(self) -> List[PluginInfo]:
        """获取浮动插件"""
        return self.list_plugins("floating")
