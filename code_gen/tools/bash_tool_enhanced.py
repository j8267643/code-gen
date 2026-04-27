"""
Enhanced Bash Tool - 增强版 Bash 工具
支持持久化会话、跨平台、更好的错误处理
"""
import asyncio
from typing import Optional
from code_gen.tools.base import Tool, ToolResult
from code_gen.tools.bash_session import get_bash_manager, BashResult


class EnhancedBashTool(Tool):
    """增强版 Bash 工具 - 支持持久化会话"""
    
    name = "bash"
    description = """Execute bash commands with persistent session support.
    
This tool provides a persistent bash shell session that maintains state between commands.
Environment variables, directory changes, and other state persist across calls.

Use this for:
- Running multiple related commands that share state
- Commands that need environment variables set by previous commands
- Long-running sessions where you want to maintain context

For simple one-off commands, use execute_command instead."""
    
    input_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute",
            },
            "session_id": {
                "type": "string",
                "description": "Session ID for persistent session (default: 'default')",
                "default": "default",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 120)",
                "default": 120,
            },
            "restart": {
                "type": "boolean",
                "description": "Restart the session if True",
                "default": False,
            },
        },
        "required": ["command"],
    }
    
    async def execute(self, command: str, session_id: str = "default",
                     timeout: int = 120, restart: bool = False) -> ToolResult:
        """执行 Bash 命令"""
        try:
            manager = get_bash_manager()
            session = manager.get_session(session_id)
            
            # 如果需要重启
            if restart:
                await session.stop()
                session = manager.get_session(session_id)
            
            # 确保会话已启动
            if not session._started:
                await session.start()
            
            # 执行命令
            result: BashResult = await session.execute(command)
            
            # 构建输出
            output_lines = []
            if result.output:
                output_lines.append(result.output)
            
            if result.error:
                output_lines.append(f"[stderr] {result.error}")
            
            output = "\n".join(output_lines) if output_lines else "Command executed successfully"
            
            if result.timed_out:
                return ToolResult(
                    success=False,
                    content=output,
                    error=f"Command timed out after {timeout} seconds"
                )
            
            if result.exit_code != 0:
                return ToolResult(
                    success=False,
                    content=output,
                    error=f"Exit code: {result.exit_code}"
                )
            
            return ToolResult(
                success=True,
                content=output,
                error=None
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Bash execution error: {str(e)}"
            )


class BashManagerTool(Tool):
    """Bash 会话管理工具"""
    
    name = "bash_manager"
    description = "Manage bash sessions - list, create, or close sessions"
    
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "close", "close_all"],
                "description": "Action to perform",
            },
            "session_id": {
                "type": "string",
                "description": "Session ID (for close action)",
            },
        },
        "required": ["action"],
    }
    
    async def execute(self, action: str, session_id: Optional[str] = None) -> ToolResult:
        """管理 Bash 会话"""
        try:
            manager = get_bash_manager()
            
            if action == "list":
                sessions = list(manager._sessions.keys())
                return ToolResult(
                    success=True,
                    content=f"Active sessions: {', '.join(sessions) if sessions else 'None'}",
                    error=None
                )
            
            elif action == "close":
                if session_id and session_id in manager._sessions:
                    await manager._sessions[session_id].stop()
                    del manager._sessions[session_id]
                    return ToolResult(
                        success=True,
                        content=f"Session '{session_id}' closed",
                        error=None
                    )
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Session '{session_id}' not found"
                )
            
            elif action == "close_all":
                await manager.close_all()
                return ToolResult(
                    success=True,
                    content="All sessions closed",
                    error=None
                )
            
            return ToolResult(
                success=False,
                content="",
                error=f"Unknown action: {action}"
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Bash manager error: {str(e)}"
            )
