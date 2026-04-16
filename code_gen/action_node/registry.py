"""Action Registry - 动作注册表"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime

from .node import ActionNode, ActionTemplates


class ActionRegistry:
    """动作注册表
    
    管理所有 ActionNode 定义
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.actions: Dict[str, ActionNode] = {}
        self.storage_path = storage_path or Path(".action_nodes")
        self._load_builtin_actions()
    
    def _load_builtin_actions(self):
        """加载内置动作"""
        self.register(ActionTemplates.code_generation())
        self.register(ActionTemplates.code_review())
        self.register(ActionTemplates.test_generation())
    
    def register(self, action: ActionNode) -> ActionNode:
        """注册动作"""
        self.actions[action.name] = action
        return action
    
    def get(self, name: str) -> Optional[ActionNode]:
        """获取动作"""
        return self.actions.get(name)
    
    def list_actions(self) -> List[ActionNode]:
        """列出所有动作"""
        return list(self.actions.values())
    
    def list_by_tag(self, tag: str) -> List[ActionNode]:
        """按标签列出"""
        return [a for a in self.actions.values() if tag in a.tags]
    
    def remove(self, name: str) -> bool:
        """移除动作"""
        if name in self.actions:
            del self.actions[name]
            return True
        return False
    
    def create_action(
        self,
        name: str,
        description: str,
        instruction: str,
        input_fields: List[Dict],
        output_fields: List[Dict],
        **kwargs
    ) -> ActionNode:
        """创建新动作"""
        from .node import FieldDefinition
        
        type_mapping = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
        }
        
        def create_field(f_data: Dict) -> FieldDefinition:
            return FieldDefinition(
                name=f_data["name"],
                field_type=type_mapping.get(f_data.get("type", "str"), str),
                description=f_data.get("description", ""),
                required=f_data.get("required", True),
                default=f_data.get("default"),
                example=f_data.get("example"),
            )
        
        action = ActionNode(
            name=name,
            description=description,
            instruction=instruction,
            input_fields=[create_field(f) for f in input_fields],
            output_fields=[create_field(f) for f in output_fields],
            **kwargs
        )
        
        return self.register(action)
    
    def save(self, path: Optional[Path] = None):
        """保存到文件"""
        save_path = path or self.storage_path / "actions.json"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "actions": {name: action.to_dict() for name, action in self.actions.items()},
            "saved_at": datetime.now().isoformat(),
        }
        
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, path: Optional[Path] = None):
        """从文件加载"""
        load_path = path or self.storage_path / "actions.json"
        
        if not load_path.exists():
            return
        
        with open(load_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for name, action_data in data.get("actions", {}).items():
            try:
                action = ActionNode.from_dict(action_data)
                self.register(action)
            except Exception as e:
                print(f"Failed to load action '{name}': {e}")


# 全局注册表实例
_global_registry: Optional[ActionRegistry] = None


def get_registry() -> ActionRegistry:
    """获取全局注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ActionRegistry()
    return _global_registry


def register_action(action: ActionNode) -> ActionNode:
    """注册动作到全局注册表"""
    return get_registry().register(action)


def get_action(name: str) -> Optional[ActionNode]:
    """从全局注册表获取动作"""
    return get_registry().get(name)
