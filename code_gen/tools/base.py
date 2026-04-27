"""
Base tool definitions for MCP
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict
from datetime import datetime
import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PermissionCheckResult:
    """Result of a permission check"""
    allowed: bool
    reason: Optional[str] = None
    prompt_user: bool = False
    permissions_required: List[str] = field(default_factory=list)
    
    @classmethod
    def allow(cls) -> 'PermissionCheckResult':
        """Create an allowed result"""
        return cls(allowed=True)
    
    @classmethod
    def deny(cls, reason: str = "Permission denied") -> 'PermissionCheckResult':
        """Create a denied result"""
        return cls(allowed=False, reason=reason)
    
    @classmethod
    def prompt(cls, permissions: List[str] = None) -> 'PermissionCheckResult':
        """Create a prompt result"""
        return cls(
            allowed=False,
            prompt_user=True,
            permissions_required=permissions or []
        )


@dataclass
class ToolResult:
    """Result of a tool execution"""
    success: bool
    content: str
    error: Optional[str] = None
    data: Optional[Any] = None
    tool_name: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "content": self.content,
            "error": self.error,
            "data": self.data,
            "tool_name": self.tool_name,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ToolResult':
        """Create from dictionary"""
        return cls(
            success=data.get("success", False),
            content=data.get("content", ""),
            error=data.get("error"),
            data=data.get("data"),
            tool_name=data.get("tool_name"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            duration_ms=data.get("duration_ms"),
            metadata=data.get("metadata", {})
        )
    
    def get_hash(self) -> str:
        """Get result hash for caching"""
        content = f"{self.tool_name}:{self.success}:{self.content}"
        return hashlib.md5(content.encode()).hexdigest()


class PermissionSystem:
    """Permission system for tools"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.config_dir = work_dir / ".code_gen"
        self.permissions_file = self.config_dir / "permissions.json"
        self._permissions: Dict[str, Dict[str, Any]] = {}
        self._ensure_config_dir()
        self._load_permissions()
    
    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_permissions(self):
        """Load permissions from file"""
        if self.permissions_file.exists():
            try:
                with open(self.permissions_file, 'r', encoding='utf-8') as f:
                    self._permissions = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load permissions: {e}")
                self._permissions = {}
    
    def _save_permissions(self):
        """Save permissions to file"""
        try:
            with open(self.permissions_file, 'w', encoding='utf-8') as f:
                json.dump(self._permissions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save permissions: {e}")
    
    def check_permission(self, tool_name: str, context: Dict[str, Any] = None) -> PermissionCheckResult:
        """Check if tool execution is allowed"""
        # Check if tool is explicitly denied
        if tool_name in self._permissions:
            perm = self._permissions[tool_name]
            if not perm.get("allowed", True):
                return PermissionCheckResult.deny(perm.get("reason", "Tool is disabled"))
        
        # Default: allow
        return PermissionCheckResult.allow()
    
    def allow_tool(self, tool_name: str, reason: str = None):
        """Allow a tool"""
        if tool_name not in self._permissions:
            self._permissions[tool_name] = {}
        
        self._permissions[tool_name]["allowed"] = True
        if reason:
            self._permissions[tool_name]["reason"] = reason
        
        self._save_permissions()
    
    def deny_tool(self, tool_name: str, reason: str = None):
        """Deny a tool"""
        if tool_name not in self._permissions:
            self._permissions[tool_name] = {}
        
        self._permissions[tool_name]["allowed"] = False
        if reason:
            self._permissions[tool_name]["reason"] = reason
        
        self._save_permissions()
    
    def get_tool_permissions(self, tool_name: str) -> Dict[str, Any]:
        """Get permissions for a tool"""
        return self._permissions.get(tool_name, {"allowed": True})
    
    def list_permissions(self) -> Dict[str, Dict[str, Any]]:
        """List all permissions"""
        return self._permissions.copy()


class ToolResultStorage:
    """Storage for tool results"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.results_dir = work_dir / ".code_gen" / "tool_results"
        self._ensure_results_dir()
    
    def _ensure_results_dir(self):
        """Ensure results directory exists"""
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_result_path(self, result_hash: str) -> Path:
        """Get result file path"""
        return self.results_dir / f"{result_hash}.json"
    
    def save_result(self, result: ToolResult) -> bool:
        """Save tool result"""
        try:
            result_hash = result.get_hash()
            result_path = self._get_result_path(result_hash)
            
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save result: {e}")
            return False
    
    def get_result(self, result_hash: str) -> Optional[ToolResult]:
        """Get tool result by hash"""
        try:
            result_path = self._get_result_path(result_hash)
            
            if not result_path.exists():
                return None
            
            with open(result_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return ToolResult.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to get result: {e}")
            return None
    
    def clear_old_results(self, max_age_days: int = 7) -> int:
        """Clear old results"""
        try:
            import time
            
            current_time = time.time()
            cleared = 0
            
            for result_file in self.results_dir.glob("*.json"):
                file_time = result_file.stat().st_mtime
                
                if current_time - file_time > max_age_days * 24 * 3600:
                    result_file.unlink()
                    cleared += 1
            
            return cleared
        except Exception as e:
            logger.error(f"Failed to clear old results: {e}")
            return 0


class Tool(ABC):
    """Base class for MCP tools"""
    
    name: str
    description: str
    input_schema: dict
    permission_system: Optional[PermissionSystem] = None
    result_storage: Optional[ToolResultStorage] = None
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        pass
    
    def to_claude_format(self) -> dict:
        """Convert to Claude API tool format"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.input_schema.get("properties", {}),
                "required": self.input_schema.get("required", []),
            },
        }
    
    def to_openai_format(self) -> dict:
        """Convert to OpenAI API tool format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.input_schema.get("properties", {}),
                    "required": self.input_schema.get("required", []),
                },
            }
        }
    
    async def execute_with_permissions(self, **kwargs) -> ToolResult:
        """Execute tool with permission check"""
        if self.permission_system:
            permission = self.permission_system.check_permission(self.name)
            
            if not permission.allowed:
                return ToolResult(
                    success=False,
                    content="",
                    error=permission.reason or "Permission denied",
                    tool_name=self.name
                )
        
        return await self.execute(**kwargs)
    
    async def execute_with_caching(self, **kwargs) -> ToolResult:
        """Execute tool with result caching"""
        # Create a result object to get hash
        temp_result = ToolResult(
            success=False,
            content="",
            tool_name=self.name,
            data=kwargs
        )
        
        result_hash = temp_result.get_hash()
        
        # Check cache
        if self.result_storage:
            cached_result = self.result_storage.get_result(result_hash)
            if cached_result:
                logger.debug(f"Cache hit for {self.name}")
                return cached_result
        
        # Execute tool
        result = await self.execute_with_permissions(**kwargs)
        result.tool_name = self.name
        
        # Cache result
        if self.result_storage:
            self.result_storage.save_result(result)
        
        return result
