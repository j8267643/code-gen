"""
Simplified agent workflow - Agent-driven execution
Like human developer: understand, plan, execute directly
"""
import json
from typing import Optional, List, Dict, Any

from code_gen.agent.smart_executor import SmartExecutor
from code_gen.ui.cli_ui import (
    print_info, print_success, print_warning, print_error,
    print_header, print_divider, print_session_info, Spinner
)


class ToolRegistry:
    """工具注册表 - 管理所有可用工具"""
    
    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self.aliases: Dict[str, str] = {
            # 搜索
            "search": "search_files",
            "find": "search_files",
            "grep": "search_files",
            # 文件
            "read": "read_file",
            "write": "write_file",
            "cat": "read_file",
            "ls": "list_directory",
            "dir": "list_directory",
            "list_dir": "list_directory",
            # 目录树
            "tree": "view_directory_tree",
            "view_dir": "view_directory_tree",
            "view_tree": "view_directory_tree",
            # 命令
            "exec": "execute_command",
            "cmd": "execute_command",
            "shell": "bash",
            # 流程
            "run": "bash",
            "start": "bash",
        }
    
    def register(self, tool: Any):
        """注册工具"""
        self.tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[Any]:
        """获取工具（支持别名）"""
        normalized = name.lower().replace("-", "_").replace(" ", "_")
        if normalized in self.aliases:
            normalized = self.aliases[normalized]
        return self.tools.get(normalized)


class SimpleAgent:
    """
    Agent-driven execution - Like human developer:
    - Understand the goal
    - Plan steps
    - Execute directly
    - Only ask LLM when needed
    """
    
    def __init__(self, client, tools, system_prompt=None, max_iterations: int = 30, work_dir: str = "."):
        self.client = client
        self.tool_registry = ToolRegistry()
        for tool in tools:
            self.tool_registry.register(tool)
        
        # Create smart executor for direct execution with iteration budget
        self.executor = SmartExecutor(self.tool_registry, client, max_iterations=max_iterations, work_dir=work_dir)
        
        self.system_prompt = system_prompt or "You are a helpful coding assistant."
    
    async def process(self, user_input: str, project_root: str) -> str:
        """
        Process user input - Agent-driven execution
        """
        print_info(f"Processing: {user_input[:50]}...")

        # Use smart executor for direct execution
        try:
            result = await self.executor.execute(user_input, project_root)
            return result
        except Exception as e:
            print_error(f"Execution error: {e}")
            # Fallback to simple chat
            return await self._simple_chat(user_input)
    
    async def _simple_chat(self, user_input: str) -> str:
        """简单聊天模式"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input}
        ]
        return await self.client.send_message(messages=messages)
