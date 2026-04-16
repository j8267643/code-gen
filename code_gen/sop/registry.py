"""SOP Registry - SOP 注册和管理"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime

from .sop import SOP, SOPTemplates


class SOPRegistry:
    """SOP 注册表
    
    管理所有 SOP 定义，支持加载、保存和查询
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.sops: Dict[str, SOP] = {}
        self.storage_path = storage_path or Path(".sops")
        self._load_builtin_sops()
    
    def _load_builtin_sops(self):
        """加载内置 SOP"""
        self.register(SOPTemplates.code_generation())
        self.register(SOPTemplates.bug_fix())
    
    def register(self, sop: SOP) -> SOP:
        """注册 SOP"""
        # 验证 SOP
        errors = sop.validate()
        if errors:
            raise ValueError(f"SOP validation failed: {errors}")
        
        self.sops[sop.name] = sop
        return sop
    
    def get(self, name: str) -> Optional[SOP]:
        """获取 SOP"""
        return self.sops.get(name)
    
    def list_sops(self) -> List[SOP]:
        """列出所有 SOP"""
        return list(self.sops.values())
    
    def list_by_tag(self, tag: str) -> List[SOP]:
        """按标签列出 SOP"""
        return [sop for sop in self.sops.values() if tag in sop.tags]
    
    def list_by_role(self, role: str) -> List[SOP]:
        """按角色列出 SOP"""
        return [sop for sop in self.sops.values() if role in sop.roles]
    
    def remove(self, name: str) -> bool:
        """移除 SOP"""
        if name in self.sops:
            del self.sops[name]
            return True
        return False
    
    def save(self, path: Optional[Path] = None):
        """保存所有 SOP 到文件"""
        save_path = path or self.storage_path / "sops.json"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "sops": {name: sop.to_dict() for name, sop in self.sops.items()},
            "saved_at": datetime.now().isoformat(),
        }
        
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, path: Optional[Path] = None):
        """从文件加载 SOP"""
        load_path = path or self.storage_path / "sops.json"
        
        if not load_path.exists():
            return
        
        with open(load_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for name, sop_data in data.get("sops", {}).items():
            try:
                sop = SOP.from_dict(sop_data)
                self.register(sop)
            except Exception as e:
                print(f"Failed to load SOP '{name}': {e}")
    
    def create_from_template(
        self,
        template_name: str,
        new_name: str,
        modifications: Optional[Dict] = None,
    ) -> SOP:
        """从模板创建 SOP"""
        template = self.get(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # 创建副本
        sop_data = template.to_dict()
        sop_data["name"] = new_name
        sop_data["id"] = None  # 生成新 ID
        
        if modifications:
            sop_data.update(modifications)
        
        sop = SOP.from_dict(sop_data)
        return self.register(sop)
