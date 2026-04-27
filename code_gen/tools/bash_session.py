"""
Persistent Bash Session Tool - Inspired by Trae Agent
Maintains state across command calls (current directory, environment variables, etc.)
"""
import asyncio
import os
from typing import Optional

from code_gen.tools.base import Tool, ToolResult


class BashSession:
    """A persistent bash/cmd session that maintains state across commands"""
    
    def __init__(self):
        self._started = False
        self._process: Optional[asyncio.subprocess.Process] = None
        self._output_delay = 0.2  # seconds
        self._timeout = 300.0  # seconds (5 minutes)
        self._sentinel = ",,,,bash-command-exit-__ERROR_CODE__-banner,,,,"
        
    async def start(self) -> None:
        """Start the bash session"""
        if self._started:
            return
            
        if os.name == "nt":  # Windows
            # Use PowerShell for better compatibility
            self._process = await asyncio.create_subprocess_exec(
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-Command",
                "-",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:  # Unix-like
            self._process = await asyncio.create_subprocess_shell(
                "/bin/bash",
                shell=True,
                bufsize=0,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setsid,
            )
        
        self._started = True
        
    async def stop(self) -> None:
        """Stop the bash session"""
        if not self._started or self._process is None:
            return
            
        try:
            self._process.terminate()
            await asyncio.wait_for(self._process.communicate(), timeout=5.0)
        except asyncio.TimeoutError:
            self._process.kill()
            try:
                await asyncio.wait_for(self._process.communicate(), timeout=2.0)
            except asyncio.TimeoutError:
                pass
        except Exception:
            pass
            
    async def run(self, command: str, timeout: Optional[int] = None) -> ToolResult:
        """Execute a command in the bash session"""
        if not self._started or self._process is None:
            return ToolResult(False, "", "Bash session not started")
            
        if self._process.returncode is not None:
            return ToolResult(False, "", f"Bash has exited with code {self._process.returncode}")
            
        # Get process pipes
        stdin = self._process.stdin
        stdout = self._process.stdout
        stderr = self._process.stderr
        
        if stdin is None or stdout is None or stderr is None:
            return ToolResult(False, "", "Process pipes not available")
            
        # Prepare sentinel with error code
        if os.name == "nt":  # PowerShell
            # PowerShell format - use double quotes to expand variables
            sentinel_template = self._sentinel.replace("__ERROR_CODE__", "$LASTEXITCODE")
            # Use Invoke-Expression to properly execute and get exit code
            full_command = f"& {{ {command} }}; Write-Host \"{sentinel_template}\"\n"
        else:  # Bash
            errcode_retriever = "$?"
            command_sep = ";"
            sentinel_cmd = self._sentinel.replace("__ERROR_CODE__", errcode_retriever)
            full_command = f"(\n{command}\n){command_sep} echo {sentinel_cmd}\n"
        stdin.write(full_command.encode())
        await stdin.drain()
        
        # Read output until sentinel is found
        output_parts = []
        error_parts = []
        error_code = 0
        
        try:
            async with asyncio.timeout(timeout or self._timeout):
                while True:
                    await asyncio.sleep(self._output_delay)
                    
                    # Try to read from stdout
                    stdout_data = ""
                    try:
                        # Use readline for line-by-line reading
                        line = await asyncio.wait_for(stdout.readline(), timeout=0.5)
                        if line:
                            stdout_data = line.decode('utf-8', errors='replace')
                    except asyncio.TimeoutError:
                        pass
                    except Exception:
                        pass
                    
                    # Try to read from stderr
                    stderr_data = ""
                    try:
                        line = await asyncio.wait_for(stderr.readline(), timeout=0.5)
                        if line:
                            stderr_data = line.decode('utf-8', errors='replace')
                    except asyncio.TimeoutError:
                        pass
                    except Exception:
                        pass
                    
                    if stdout_data:
                        output_parts.append(stdout_data)
                    if stderr_data:
                        error_parts.append(stderr_data)
                    
                    # Check for sentinel in output
                    full_output = "".join(output_parts)
                    sentinel_before = self._sentinel.partition("__ERROR_CODE__")[0]
                    
                    if sentinel_before in full_output:
                        # Found sentinel, parse output
                        output, _, exit_banner = full_output.rpartition(sentinel_before)
                        
                        # Extract error code
                        sentinel_after = self._sentinel.partition("__ERROR_CODE__")[2]
                        error_code_str, _, _ = exit_banner.partition(sentinel_after)
                        
                        if error_code_str.strip().isdecimal():
                            error_code = int(error_code_str.strip())
                            break
                        elif error_code_str.strip() == "":
                            # Empty error code, assume success
                            error_code = 0
                            break
                            
        except asyncio.TimeoutError:
            return ToolResult(False, "".join(output_parts), f"Command timed out after {timeout or self._timeout} seconds")
        
        # Clean up output
        output = "".join(output_parts).rstrip("\n")
        error = "".join(error_parts).rstrip("\n")
        
        if error_code != 0:
            return ToolResult(False, output, error or f"Exit code: {error_code}")
            
        return ToolResult(True, output or error or "Command executed successfully", "")


class BashSessionTool(Tool):
    """
    Execute commands in a persistent bash session.
    State (current directory, environment variables) is maintained across calls.
    """
    
    name = "bash"
    description = """Execute commands in a persistent bash session.
    
This tool maintains state across commands:
- Current working directory is preserved
- Environment variables persist
- Use 'cd' to change directories

For long-running servers, use ' &' suffix to run in background.
Examples:
- List files: ls -la
- Change directory: cd backend
- Run server: uvicorn main:app --reload &
- Check current directory: cd
"""
    input_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Command to execute in the bash session",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 300, 5 minutes)",
                "default": 300,
            },
        },
        "required": ["command"],
    }
    
    def __init__(self):
        super().__init__()
        self._session: Optional[BashSession] = None
        
    async def execute(self, command: str = "", timeout: int = 300) -> ToolResult:
        """Execute command in persistent session"""
        # Validate command
        if not command:
            return ToolResult(False, "", "No command provided. Please specify a command to execute.")
        
        # Start session if not started
        if self._session is None:
            self._session = BashSession()
            await self._session.start()
            
        # Run command with shorter default timeout for interactive use
        return await self._session.run(command, timeout)
        
    async def close(self):
        """Close the session"""
        if self._session:
            await self._session.stop()
            self._session = None
