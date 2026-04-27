"""
Tool Registry for Multi-Agent System
统一管理所有可用工具，让所有 Agent 共享
"""
from typing import Dict, List, Any, Optional, Type
from pathlib import Path
import json

from code_gen.tools.base import Tool
from code_gen.tools.files import ReadFileTool, WriteFileTool, ListDirectoryTool
from code_gen.tools.shell import ExecuteCommandTool, ViewDirectoryTreeTool
from code_gen.tools.search import SearchFilesTool, GetFileInfoTool
from code_gen.tools.git import GitStatusTool, GitDiffTool, GitLogTool
from code_gen.tools.tavily_tool import TavilySearchTool, TavilyExtractTool


class ToolRegistry:
    """
    工具注册器
    
    统一管理所有可用工具，支持：
    1. 注册/注销工具
    2. 获取工具列表
    3. 执行工具调用
    4. 工具权限管理
    """
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self._tools: Dict[str, Tool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        default_tools = [
            ReadFileTool(),
            WriteFileTool(),
            ListDirectoryTool(),
            ExecuteCommandTool(),
            ViewDirectoryTreeTool(),
            SearchFilesTool(),
            GetFileInfoTool(),
            GitStatusTool(),
            GitDiffTool(),
            GitLogTool(),
            TavilySearchTool(),
            TavilyExtractTool(),
        ]
        
        for tool in default_tools:
            self.register(tool)
    
    def register(self, tool: Tool) -> "ToolRegistry":
        """注册工具"""
        self._tools[tool.name] = tool
        return self
    
    def unregister(self, tool_name: str) -> "ToolRegistry":
        """注销工具"""
        if tool_name in self._tools:
            del self._tools[tool_name]
        return self
    
    def get(self, tool_name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())
    
    def get_all_tools(self) -> List[Tool]:
        """获取所有工具实例"""
        return list(self._tools.values())
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具的 schema（用于 AI 调用）"""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema
                }
            })
        return schemas
    
    async def execute(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        执行工具调用
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            {
                "success": bool,
                "content": str,
                "error": str
            }
        """
        tool = self.get(tool_name)
        if not tool:
            return {
                "success": False,
                "content": "",
                "error": f"Tool not found: {tool_name}"
            }
        
        try:
            result = await tool.execute(**kwargs)
            return {
                "success": result.success,
                "content": result.content,
                "error": result.error or ""
            }
        except Exception as e:
            return {
                "success": False,
                "content": "",
                "error": str(e)
            }
    
    def get_tools_prompt(self) -> str:
        """生成工具说明的提示词"""
        lines = ["## 可用工具", ""]
        
        for tool in self._tools.values():
            lines.append(f"- {tool.name}: {tool.description}")
        
        lines.append("")
        lines.append("## 工具使用格式")
        lines.append("当你需要使用工具时，请使用以下格式：")
        lines.append("")
        lines.append("```tool")
        lines.append('{"tool": "工具名称", "parameters": {"参数名": "参数值"}}')
        lines.append("```")
        lines.append("")
        lines.append("常用工具：")
        lines.append("- read_file: 读取文件内容，参数: path, offset, limit")
        lines.append("- write_file: 写入文件，参数: path, content")
        lines.append("- list_directory: 列出目录，参数: path")
        lines.append("- execute_command: 执行命令，参数: command")
        lines.append("- search_files: 搜索文件内容，参数: pattern, path")
        
        return "\n".join(lines)


# 全局工具注册器实例
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry(work_dir: Path) -> ToolRegistry:
    """获取或创建全局工具注册器"""
    global _tool_registry
    if _tool_registry is None or _tool_registry.work_dir != work_dir:
        _tool_registry = ToolRegistry(work_dir)
    return _tool_registry
