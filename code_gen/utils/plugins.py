"""
Plugin system for Claude Code
Based on plugins/ and loadPluginCommands.ts from TypeScript project
"""
from typing import Optional, List, Callable, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import json
import hashlib
import time
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class PluginType(str, Enum):
    """Plugin types"""
    BUNDLED = "bundled"
    PROJECT = "project"
    EXTERNAL = "external"


@dataclass
class PluginManifest:
    """Plugin manifest"""
    name: str
    version: str
    description: str
    author: Optional[str] = None
    license: Optional[str] = None
    entry_point: Optional[str] = None
    config_schema: Optional[dict] = None


@dataclass
class Plugin:
    """Plugin instance"""
    manifest: PluginManifest
    path: str
    type: PluginType
    enabled: bool = True
    config: dict = field(default_factory=dict)
    state: dict = field(default_factory=dict)


class PluginChange:
    """Represents a change in a plugin"""
    def __init__(self, plugin: Plugin, change_type: str):
        self.plugin = plugin
        self.change_type = change_type  # 'added', 'modified', 'deleted'


class PluginChangeHandler:
    """Handler for plugin changes"""
    async def on_plugin_changed(self, change: PluginChange):
        pass


class PluginChangeDetector:
    """Detects changes in plugins"""
    def __init__(self, plugin_dir: Path):
        self.plugin_dir = plugin_dir
        self._file_hashes: Dict[str, str] = {}
        self._handlers: List[PluginChangeHandler] = []
    
    def add_handler(self, handler: PluginChangeHandler):
        self._handlers.append(handler)
    
    async def notify_changes(self, changes: List[PluginChange]):
        for handler in self._handlers:
            await handler.on_plugin_changed(changes[0]) if changes else None
    
    def detect_changes(self) -> List[PluginChange]:
        """Detect plugin file changes"""
        changes = []
        current_files = {}
        
        if not self.plugin_dir.exists():
            return changes
        
        for plugin_file in self.plugin_dir.rglob("*.json"):
            file_hash = self._get_file_hash(plugin_file)
            if file_hash:
                current_files[str(plugin_file)] = file_hash
                
                if str(plugin_file) not in self._file_hashes:
                    changes.append(PluginChange(
                        plugin=Plugin(
                            manifest=PluginManifest(
                                name=plugin_file.stem,
                                version="1.0.0",
                                description="Loaded from file"
                            ),
                            path=str(plugin_file),
                            type=PluginType.PROJECT
                        ),
                        change_type="added"
                    ))
                elif self._file_hashes[str(plugin_file)] != file_hash:
                    changes.append(PluginChange(
                        plugin=Plugin(
                            manifest=PluginManifest(
                                name=plugin_file.stem,
                                version="1.0.0",
                                description="Loaded from file"
                            ),
                            path=str(plugin_file),
                            type=PluginType.PROJECT
                        ),
                        change_type="modified"
                    ))
        
        for plugin_file in self._file_hashes:
            if plugin_file not in current_files:
                changes.append(PluginChange(
                    plugin=Plugin(
                        manifest=PluginManifest(
                            name=Path(plugin_file).stem,
                            version="1.0.0",
                            description="Loaded from file"
                        ),
                        path=plugin_file,
                        type=PluginType.PROJECT
                    ),
                    change_type="deleted"
                ))
        
        self._file_hashes = current_files
        return changes
    
    def _get_file_hash(self, file_path: Path) -> Optional[str]:
        """Get hash of file content"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return None


class PluginPermissionSystem:
    """Permission system for plugins"""
    def __init__(self):
        self._permissions: Dict[str, Dict[str, Any]] = {}
    
    def set_permission(self, plugin_name: str, permission: str, allowed: bool):
        """Set permission for a plugin"""
        if plugin_name not in self._permissions:
            self._permissions[plugin_name] = {}
        self._permissions[plugin_name][permission] = allowed
    
    def check_permission(self, plugin_name: str, permission: str) -> bool:
        """Check if plugin has permission"""
        if plugin_name not in self._permissions:
            return True  # Default: allow
        return self._permissions[plugin_name].get(permission, True)
    
    def get_plugin_permissions(self, plugin_name: str) -> Dict[str, Any]:
        """Get all permissions for a plugin"""
        return self._permissions.get(plugin_name, {})
    
    def list_plugins_with_permission(self, permission: str) -> List[str]:
        """List all plugins with a specific permission"""
        return [
            name for name, perms in self._permissions.items()
            if perms.get(permission, True)
        ]


class PluginLoader:
    """Loads and manages plugins"""
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.plugins: List[Plugin] = []
        self._change_detector: Optional[PluginChangeDetector] = None
        self._permission_system = PluginPermissionSystem()
    
    def set_change_detector(self, detector: PluginChangeDetector):
        """Set change detector"""
        self._change_detector = detector
    
    def get_permission_system(self) -> PluginPermissionSystem:
        """Get permission system"""
        return self._permission_system
    
    def load_bundled_plugins(self):
        """Load bundled plugins"""
        # Bundled plugins are included in the package
        pass
    
    def load_project_plugins(self):
        """Load project-specific plugins"""
        plugins_dir = self.work_dir / ".code_gen" / "plugins"
        
        if not plugins_dir.exists():
            return
        
        for plugin_file in plugins_dir.glob("*.json"):
            try:
                with open(plugin_file, 'r') as f:
                    data = json.load(f)
                
                manifest = PluginManifest(
                    name=data.get("name", plugin_file.stem),
                    version=data.get("version", "1.0.0"),
                    description=data.get("description", ""),
                    author=data.get("author"),
                    license=data.get("license"),
                    entry_point=data.get("entry_point"),
                    config_schema=data.get("config_schema")
                )
                
                plugin = Plugin(
                    manifest=manifest,
                    path=str(plugin_file),
                    type=PluginType.PROJECT,
                    config=data.get("config", {}),
                    state=data.get("state", {})
                )
                
                self.plugins.append(plugin)
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_file}: {e}")
    
    def load_external_plugins(self, plugin_dir: Path):
        """Load external plugins from directory"""
        if not plugin_dir.exists():
            return
        
        for plugin_file in plugin_dir.glob("*.json"):
            try:
                with open(plugin_file, 'r') as f:
                    data = json.load(f)
                
                manifest = PluginManifest(
                    name=data.get("name", plugin_file.stem),
                    version=data.get("version", "1.0.0"),
                    description=data.get("description", ""),
                    author=data.get("author"),
                    license=data.get("license"),
                    entry_point=data.get("entry_point"),
                    config_schema=data.get("config_schema")
                )
                
                plugin = Plugin(
                    manifest=manifest,
                    path=str(plugin_file),
                    type=PluginType.EXTERNAL,
                    config=data.get("config", {}),
                    state=data.get("state", {})
                )
                
                self.plugins.append(plugin)
            except Exception as e:
                logger.error(f"Failed to load external plugin {plugin_file}: {e}")
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin"""
        for plugin in self.plugins:
            if plugin.manifest.name == plugin_name:
                plugin.enabled = True
                return True
        return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin"""
        for plugin in self.plugins:
            if plugin.manifest.name == plugin_name:
                plugin.enabled = False
                return True
        return False
    
    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """Get a plugin by name"""
        for plugin in self.plugins:
            if plugin.manifest.name == plugin_name and plugin.enabled:
                return plugin
        return None
    
    def get_all_plugins(self) -> List[Plugin]:
        """Get all enabled plugins"""
        return [p for p in self.plugins if p.enabled]
    
    async def check_for_changes(self) -> List[PluginChange]:
        """Check for plugin changes and notify handlers"""
        if not self._change_detector:
            return []
        
        changes = self._change_detector.detect_changes()
        if changes:
            await self._change_detector.notify_changes(changes)
            self.plugins.clear()
            self.load_bundled_plugins()
            self.load_project_plugins()
        
        return changes


# Global plugin loader instance
plugin_loader: Optional[PluginLoader] = None
