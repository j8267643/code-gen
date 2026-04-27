"""
Smart Runner - Intelligent project running with background support
Handles cross-platform differences and server startup
"""
import subprocess
import platform
import time
import socket
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RunStatus(Enum):
    """Run status"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ALREADY_RUNNING = "already_running"


@dataclass
class RunResult:
    """Run result"""
    status: RunStatus
    message: str
    process_id: Optional[int] = None
    url: Optional[str] = None
    error: Optional[str] = None


class SmartRunner:
    """Smart project runner with cross-platform support"""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.running_processes = {}
    
    def run_project(self, command: str, port: Optional[int] = None, 
                    background: bool = True, timeout: int = 5) -> RunResult:
        """
        Run project with intelligent handling
        
        Args:
            command: Command to run
            port: Port to check for availability
            background: Whether to run in background
            timeout: Timeout for startup check
        """
        try:
            # Check if something is already running on the port
            if port and self._is_port_in_use(port):
                return RunResult(
                    status=RunStatus.ALREADY_RUNNING,
                    message=f"Port {port} is already in use",
                    url=f"http://localhost:{port}"
                )
            
            # Prepare command based on platform
            if background:
                process = self._run_in_background(command)
            else:
                process = self._run_in_foreground(command)
            
            if process is None:
                return RunResult(
                    status=RunStatus.FAILED,
                    message="Failed to start process",
                    error="Process creation failed"
                )
            
            # Wait a bit for startup
            time.sleep(timeout)
            
            # Check if process is still running
            if process.poll() is not None:
                # Process exited
                stdout, stderr = process.communicate()
                # Handle encoding issues on Windows
                try:
                    error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                except UnicodeDecodeError:
                    try:
                        error_msg = stderr.decode('gbk') if stderr else "Unknown error"
                    except UnicodeDecodeError:
                        error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "Unknown error"
                return RunResult(
                    status=RunStatus.FAILED,
                    message=f"Process exited with code {process.returncode}",
                    error=error_msg
                )
            
            # Store process info
            self.running_processes[command] = process
            
            # Build result
            url = f"http://localhost:{port}" if port else None
            return RunResult(
                status=RunStatus.SUCCESS,
                message=f"Project started successfully (PID: {process.pid})",
                process_id=process.pid,
                url=url
            )
            
        except subprocess.TimeoutExpired:
            return RunResult(
                status=RunStatus.TIMEOUT,
                message=f"Command timed out after {timeout} seconds",
                error="Startup timeout - server may still be starting"
            )
        except Exception as e:
            return RunResult(
                status=RunStatus.FAILED,
                message=f"Failed to run project: {str(e)}",
                error=str(e)
            )
    
    def _run_in_background(self, command: str) -> Optional[subprocess.Popen]:
        """Run command in background (cross-platform)"""
        system = platform.system().lower()
        
        try:
            if system == "windows":
                # Windows: Use CREATE_NEW_CONSOLE to create new window
                return subprocess.Popen(
                    command,
                    shell=True,
                    cwd=self.project_path,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # Linux/Mac: Use nohup and redirect output
                return subprocess.Popen(
                    f"nohup {command} > /dev/null 2>&1 &",
                    shell=True,
                    cwd=self.project_path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
        except Exception as e:
            print(f"Error running in background: {e}")
            return None
    
    def _run_in_foreground(self, command: str) -> Optional[subprocess.Popen]:
        """Run command in foreground"""
        try:
            return subprocess.Popen(
                command,
                shell=True,
                cwd=self.project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except Exception as e:
            print(f"Error running in foreground: {e}")
            return None
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if port is in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def stop_project(self, command: str) -> bool:
        """Stop a running project"""
        if command in self.running_processes:
            process = self.running_processes[command]
            try:
                process.terminate()
                process.wait(timeout=5)
                del self.running_processes[command]
                return True
            except Exception:
                try:
                    process.kill()
                    del self.running_processes[command]
                    return True
                except Exception:
                    return False
        return False
    
    def install_dependencies(self, command: str) -> Tuple[bool, str]:
        """Install project dependencies"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.project_path,
                capture_output=True,
                timeout=120
            )
            
            # Handle encoding issues on Windows
            try:
                stderr = result.stderr.decode('utf-8') if result.stderr else ""
            except UnicodeDecodeError:
                try:
                    stderr = result.stderr.decode('gbk') if result.stderr else ""
                except UnicodeDecodeError:
                    stderr = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
            
            if result.returncode == 0:
                return True, "Dependencies installed successfully"
            else:
                return False, f"Installation failed: {stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Installation timed out"
        except Exception as e:
            return False, f"Installation error: {str(e)}"
    
    def check_health(self, url: str, timeout: int = 5) -> bool:
        """Check if service is healthy"""
        import urllib.request
        try:
            urllib.request.urlopen(url, timeout=timeout)
            return True
        except Exception:
            return False


# Global runner instance
runner = SmartRunner()
