"""
Process Management Tools - 进程管理工具
"""
import subprocess
import platform
from typing import Optional, List
from code_gen.tools.base import Tool, ToolResult


class KillProcessTool(Tool):
    """Kill a process by PID or port"""
    
    name = "kill_process"
    description = "Kill a process by PID or port number"
    input_schema = {
        "type": "object",
        "properties": {
            "pid": {
                "type": "integer",
                "description": "Process ID to kill",
            },
            "port": {
                "type": "integer",
                "description": "Port number to find and kill process",
            },
        },
    }
    
    async def execute(self, pid: Optional[int] = None, port: Optional[int] = None) -> ToolResult:
        try:
            if not pid and not port:
                return ToolResult(
                    success=False,
                    content="",
                    error="Either pid or port must be provided"
                )
            
            is_windows = platform.system().lower() == "windows"
            
            # If port is provided, find the PID first
            if port and not pid:
                if is_windows:
                    # Use netstat to find PID
                    result = subprocess.run(
                        ["netstat", "-ano", "|", "findstr", f":{port}"],
                        capture_output=True,
                        text=True,
                        shell=True
                    )
                    # Parse output to find PID
                    for line in result.stdout.split('\n'):
                        if f":{port}" in line and "LISTENING" in line:
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                pid = int(parts[-1])
                                break
                else:
                    # Unix/Linux/Mac
                    result = subprocess.run(
                        ["lsof", "-ti", f":{port}"],
                        capture_output=True,
                        text=True
                    )
                    if result.stdout.strip():
                        pid = int(result.stdout.strip().split()[0])
                
                if not pid:
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"No process found using port {port}"
                    )
            
            # Kill the process
            if is_windows:
                result = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ["kill", "-9", str(pid)],
                    capture_output=True,
                    text=True
                )
            
            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    content=f"Process {pid} killed successfully",
                    error=None
                )
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Failed to kill process: {result.stderr}"
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error killing process: {str(e)}"
            )


class RunShellScriptTool(Tool):
    """Run a shell script file"""
    
    name = "run_sh"
    description = "Execute a shell script (.sh file). Automatically detects and runs the appropriate command."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the shell script",
            },
            "args": {
                "type": "array",
                "description": "Arguments to pass to the script",
                "items": {"type": "string"},
                "default": [],
            },
        },
        "required": ["path"],
    }
    
    async def execute(self, path: str, args: Optional[List[str]] = None) -> ToolResult:
        try:
            from pathlib import Path
            
            script_path = Path(path)
            if not script_path.exists():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Script not found: {path}"
                )
            
            # Read script content to determine what to run
            content = script_path.read_text(encoding='utf-8')
            
            is_windows = platform.system().lower() == "windows"
            
            # Extract command from script (look for common patterns)
            command = None
            for line in content.split('\n'):
                line = line.strip()
                # Skip shebang and comments
                if line.startswith('#') or not line:
                    continue
                # Look for run commands
                if 'uvicorn' in line or 'python' in line or 'node' in line or 'npm' in line:
                    command = line
                    break
            
            if not command:
                return ToolResult(
                    success=False,
                    content="",
                    error="Could not determine command from script"
                )
            
            # Run the command in the script's directory
            cwd = str(script_path.parent)
            
            if is_windows:
                # On Windows, run with PowerShell
                full_command = f"cd '{cwd}'; {command}"
                result = subprocess.run(
                    ["powershell", "-Command", full_command],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            else:
                # On Unix, make script executable and run
                script_path.chmod(0o755)
                cmd = [str(script_path)] + (args or [])
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=cwd
                )
            
            output = result.stdout if result.stdout else "Script executed"
            error = result.stderr if result.stderr else None
            
            return ToolResult(
                success=result.returncode == 0,
                content=output,
                error=error
            )
                
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=True,
                content="Script started (timeout after 10s, may be running in background)",
                error=None
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error running script: {str(e)}"
            )


class ListProcessesTool(Tool):
    """List running processes"""
    
    name = "list_processes"
    description = "List running processes, optionally filtered by port or name"
    input_schema = {
        "type": "object",
        "properties": {
            "port": {
                "type": "integer",
                "description": "Filter by port number",
            },
            "name": {
                "type": "string",
                "description": "Filter by process name",
            },
        },
    }
    
    async def execute(self, port: Optional[int] = None, name: Optional[str] = None) -> ToolResult:
        try:
            is_windows = platform.system().lower() == "windows"
            
            if port:
                # Find process by port
                if is_windows:
                    result = subprocess.run(
                        ["netstat", "-ano", "|", "findstr", f":{port}"],
                        capture_output=True,
                        text=True,
                        shell=True
                    )
                else:
                    result = subprocess.run(
                        ["lsof", "-i", f":{port}"],
                        capture_output=True,
                        text=True
                    )
                
                return ToolResult(
                    success=True,
                    content=result.stdout or f"No process found using port {port}",
                    error=None
                )
            
            elif name:
                # Find process by name
                if is_windows:
                    result = subprocess.run(
                        ["tasklist", "/FI", f"IMAGENAME eq {name}"],
                        capture_output=True,
                        text=True
                    )
                else:
                    result = subprocess.run(
                        ["ps", "aux", "|", "grep", name],
                        capture_output=True,
                        text=True,
                        shell=True
                    )
                
                return ToolResult(
                    success=True,
                    content=result.stdout or f"No process found with name {name}",
                    error=None
                )
            
            else:
                # List all processes
                if is_windows:
                    result = subprocess.run(
                        ["tasklist"],
                        capture_output=True,
                        text=True
                    )
                else:
                    result = subprocess.run(
                        ["ps", "aux"],
                        capture_output=True,
                        text=True
                    )
                
                return ToolResult(
                    success=True,
                    content=result.stdout[:2000],  # Limit output
                    error=None
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error listing processes: {str(e)}"
            )
