"""
Shell command execution tools
"""
import asyncio
import os
import shlex
from pathlib import Path

from code_gen.tools.base import Tool, ToolResult


class ExecuteCommandTool(Tool):
    """Execute shell commands"""
    
    name = "execute_command"
    description = "Execute a shell command in the working directory"
    input_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 30)",
                "default": 30,
            },
        },
        "required": ["command"],
    }
    
    async def execute(self, command: str, timeout: int = 30) -> ToolResult:
        try:
            # Security check - block dangerous commands
            dangerous_commands = ['rm -rf /', 'mkfs', 'dd if=', '> /dev/sda']
            for dangerous in dangerous_commands:
                if dangerous in command:
                    return ToolResult(
                        False, 
                        "", 
                        f"Command blocked for security: {dangerous}"
                    )
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd(),
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    False, 
                    "", 
                    f"Command timed out after {timeout} seconds"
                )
            
            output = stdout.decode('utf-8', errors='ignore')
            error = stderr.decode('utf-8', errors='ignore')
            
            if process.returncode != 0:
                return ToolResult(
                    False,
                    output,
                    f"Exit code {process.returncode}: {error}"
                )
            
            return ToolResult(True, output or error or "Command executed successfully")
            
        except Exception as e:
            return ToolResult(False, "", str(e))


class ViewDirectoryTreeTool(Tool):
    """View directory tree structure"""
    
    name = "view_directory_tree"
    description = "View the directory tree structure"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Root directory path",
                "default": ".",
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum depth to display",
                "default": 3,
            },
        },
    }
    
    async def execute(self, path: str = ".", max_depth: int = 3) -> ToolResult:
        try:
            root = Path(path)
            
            if not root.exists():
                return ToolResult(False, "", f"Path not found: {path}")
            
            # Common directories to ignore
            ignore_patterns = {
                '.git', '__pycache__', 'node_modules', '.venv', 
                'venv', '.pytest_cache', '.mypy_cache', 'dist',
                'build', '.idea', '.vscode', '*.pyc'
            }
            
            def build_tree(directory: Path, prefix: str = "", depth: int = 0) -> str:
                if depth > max_depth:
                    return ""
                
                result = []
                try:
                    items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                except PermissionError:
                    return f"{prefix}[permission denied]\n"
                
                for i, item in enumerate(items):
                    # Skip ignored patterns
                    if any(pattern in str(item) for pattern in ignore_patterns):
                        continue
                    
                    is_last = i == len(items) - 1
                    connector = "└── " if is_last else "├── "
                    
                    if item.is_dir():
                        result.append(f"{prefix}{connector}📁 {item.name}/")
                        extension = "    " if is_last else "│   "
                        result.append(build_tree(item, prefix + extension, depth + 1))
                    else:
                        result.append(f"{prefix}{connector}📄 {item.name}")
                
                return '\n'.join(result)
            
            tree = f"📁 {root.name}/\n" + build_tree(root)
            
            return ToolResult(True, tree)
            
        except Exception as e:
            return ToolResult(False, "", str(e))


class ShellTools:
    """Collection of shell tools"""
    
    @staticmethod
    def get_tools() -> list[Tool]:
        """Get all shell tools"""
        return [
            ExecuteCommandTool(),
            ViewDirectoryTreeTool(),
        ]
