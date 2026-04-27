"""
File operation tools
"""
import os
import platform
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional

from code_gen.tools.base import Tool, ToolResult


class ReadFileTool(Tool):
    """Read file contents"""
    
    name = "read_file"
    description = "Read the contents of a file"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to read",
            },
            "offset": {
                "type": "integer",
                "description": "Line offset to start reading from",
                "default": 0,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read",
                "default": 100,
            },
        },
        "required": ["path"],
    }
    
    async def execute(self, path: str, offset: int = 0, limit: int = 100) -> ToolResult:
        try:
            # Ensure path is relative to current working directory
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = Path.cwd() / file_path
            
            if not file_path.exists():
                return ToolResult(False, "", f"File not found: {file_path}")
            
            if not file_path.is_file():
                return ToolResult(False, "", f"Not a file: {path}")
            
            # Check file size
            size = file_path.stat().st_size
            if size > 1024 * 1024:  # 1MB limit
                return ToolResult(
                    False, 
                    "", 
                    f"File too large ({size} bytes). Maximum size is 1MB."
                )
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            # Apply offset and limit
            start = offset
            end = min(offset + limit, len(lines))
            selected_lines = lines[start:end]
            
            content = ''.join(selected_lines)
            
            # Add line numbers
            numbered_content = ''
            for i, line in enumerate(selected_lines, start=start + 1):
                numbered_content += f"{i:4d} | {line}"
            
            return ToolResult(True, numbered_content)
            
        except Exception as e:
            return ToolResult(False, "", str(e))


class WriteFileTool(Tool):
    """Write content to a file"""
    
    name = "write_file"
    description = "Write content to a file (creates if doesn't exist)"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file",
            },
            "content": {
                "type": "string",
                "description": "Content to write",
            },
        },
        "required": ["path", "content"],
    }
    
    async def execute(self, path: str, content: str) -> ToolResult:
        try:
            # Ensure path is relative to current working directory
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = Path.cwd() / file_path
            
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return ToolResult(True, f"File written successfully: {file_path}")
            
        except Exception as e:
            return ToolResult(False, "", str(e))


class ListDirectoryTool(Tool):
    """List directory contents"""
    
    name = "list_directory"
    description = "List files and directories"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to directory (default: current)",
                "default": ".",
            },
            "depth": {
                "type": "integer",
                "description": "Maximum depth to list (default: 1, -1 for unlimited)",
                "default": 1,
            },
        },
    }
    
    async def execute(self, path: str = ".", depth: int = 1) -> ToolResult:
        try:
            # Ensure path is relative to current working directory
            dir_path = Path(path)
            if not dir_path.is_absolute():
                dir_path = Path.cwd() / dir_path
            
            if not dir_path.exists():
                return ToolResult(False, "", f"Directory not found: {dir_path}")
            
            if not dir_path.is_dir():
                return ToolResult(False, "", f"Not a directory: {dir_path}")
            
            # Build tree with depth support
            def build_tree(directory: Path, current_depth: int = 0, prefix: str = "") -> list:
                if depth != -1 and current_depth >= depth:
                    return []
                
                items = []
                try:
                    dir_items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                except PermissionError:
                    return [f"{prefix}[permission denied]"]
                
                for i, item in enumerate(dir_items):
                    is_last = i == len(dir_items) - 1
                    connector = "└── " if is_last else "├── "
                    
                    # Skip hidden files at deeper levels
                    if current_depth > 0 and item.name.startswith('.'):
                        continue
                    
                    if item.is_dir():
                        items.append(f"{prefix}{connector}📁 {item.name}/")
                        if depth == -1 or current_depth < depth - 1:
                            extension = "    " if is_last else "│   "
                            items.extend(build_tree(item, current_depth + 1, prefix + extension))
                    else:
                        size = ""
                        try:
                            size_bytes = item.stat().st_size
                            if size_bytes < 1024:
                                size = f" ({size_bytes}B)"
                            elif size_bytes < 1024 * 1024:
                                size = f" ({size_bytes / 1024:.1f}KB)"
                            else:
                                size = f" ({size_bytes / (1024 * 1024):.1f}MB)"
                        except:
                            pass
                        items.append(f"{prefix}{connector}📄 {item.name}{size}")
                
                return items
            
            if depth == 1:
                # Simple listing for depth 1
                items = []
                for item in sorted(dir_path.iterdir()):
                    prefix = "📁 " if item.is_dir() else "📄 "
                    size = ""
                    if item.is_file():
                        size_bytes = item.stat().st_size
                        if size_bytes < 1024:
                            size = f" ({size_bytes}B)"
                        elif size_bytes < 1024 * 1024:
                            size = f" ({size_bytes / 1024:.1f}KB)"
                        else:
                            size = f" ({size_bytes / (1024 * 1024):.1f}MB)"
                    items.append(f"{prefix}{item.name}{size}")
                return ToolResult(True, '\n'.join(items) if items else "Empty directory")
            else:
                # Tree view for deeper levels
                tree_items = build_tree(dir_path, 0)
                header = f"📁 {dir_path.name}/\n" if dir_path != Path('.') else ""
                return ToolResult(True, header + '\n'.join(tree_items) if tree_items else "Empty directory")
            
        except Exception as e:
            return ToolResult(False, "", str(e))


class OpenFileTool(Tool):
    """Open file in default application or browser"""
    
    name = "open_file"
    description = "Open a file in the default application or browser"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to open",
            },
            "in_browser": {
                "type": "boolean",
                "description": "Whether to open in browser (for HTML files)",
                "default": False,
            },
        },
        "required": ["path"],
    }
    
    async def execute(self, path: str, in_browser: bool = False) -> ToolResult:
        try:
            file_path = Path(path).resolve()
            
            if not file_path.exists():
                return ToolResult(False, "", f"File not found: {path}")
            
            if not file_path.is_file():
                return ToolResult(False, "", f"Not a file: {path}")
            
            file_url = file_path.as_uri()
            
            # For HTML files or when explicitly requested, use browser
            if in_browser or file_path.suffix.lower() in ['.html', '.htm']:
                try:
                    webbrowser.open(file_url)
                    return ToolResult(True, f"Opened in browser: {file_path}")
                except Exception as e:
                    return ToolResult(False, "", f"Failed to open in browser: {e}")
            
            # Use platform-specific method to open file
            system = platform.system()
            try:
                if system == "Windows":
                    os.startfile(str(file_path))
                elif system == "Darwin":  # macOS
                    subprocess.run(["open", str(file_path)], check=True)
                else:  # Linux
                    subprocess.run(["xdg-open", str(file_path)], check=True)
                
                return ToolResult(True, f"Opened file: {file_path}")
            except Exception as e:
                return ToolResult(False, "", f"Failed to open file: {e}")
                
        except Exception as e:
            return ToolResult(False, "", str(e))


class AnalyzeProjectTool(Tool):
    """Analyze project structure and determine how to run it"""
    
    name = "analyze_project"
    description = "Analyze project structure to detect project type, entry file, and run command. MUST use this before running a project."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the project directory (default: current directory)",
                "default": ".",
            },
        },
        "required": [],
    }
    
    async def execute(self, path: str = ".") -> ToolResult:
        try:
            from code_gen.core.project_analyzer import ProjectAnalyzer
            import json
            
            analyzer = ProjectAnalyzer(path)
            info = analyzer.analyze()
            
            # Return clean JSON data only - let AI decide what to do
            data = {
                "project_type": info.project_type.value,
                "is_fullstack": info.is_fullstack,
                "entry_file": info.entry_file,
                "run_command": info.run_command,
                "install_command": info.install_command,
                "port": info.port,
                "detected_files": info.detected_files[:10],  # Limit to 10 files
            }
            
            if info.is_fullstack and info.components:
                data["components"] = [
                    {
                        "name": c.name,
                        "type": c.project_type.value,
                        "path": str(c.path),
                        "run_command": c.run_command,
                        "port": c.port,
                    }
                    for c in info.components
                ]
            
            return ToolResult(True, json.dumps(data, ensure_ascii=False, indent=2))
            
        except Exception as e:
            return ToolResult(False, "", str(e))


class SmartRunTool(Tool):
    """Smart project runner with background support"""
    
    name = "smart_run"
    description = "Intelligently run a project with automatic background execution and port checking. Use this instead of execute_command for running projects."
    input_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Command to run (e.g., 'uvicorn main:app --reload')",
            },
            "port": {
                "type": "integer",
                "description": "Port number to check (optional)",
            },
            "background": {
                "type": "boolean",
                "description": "Run in background (default: true)",
                "default": True,
            },
            "install_first": {
                "type": "string",
                "description": "Install command to run first (e.g., 'pip install -r requirements.txt')",
            },
            "cwd": {
                "type": "string",
                "description": "Working directory to run the command in (optional)",
            },
        },
        "required": ["command"],
    }
    
    async def execute(self, command: str, port: Optional[int] = None, 
                      background: bool = True, install_first: Optional[str] = None,
                      cwd: Optional[str] = None) -> ToolResult:
        try:
            from code_gen.smart_runner import SmartRunner
            import os
            
            # Change to working directory if specified
            original_dir = None
            if cwd:
                original_dir = os.getcwd()
                os.chdir(cwd)
            
            try:
                runner = SmartRunner()
                
                # Install dependencies first if specified
                if install_first:
                    success, message = runner.install_dependencies(install_first)
                    if not success:
                        return ToolResult(False, f"Installation failed: {message}", message)
                
                # Run the project
                result = runner.run_project(command, port=port, background=background)
            finally:
                # Restore original directory
                if original_dir:
                    os.chdir(original_dir)
            
            # Format result
            lines = [
                f"Status: {result.status.value}",
                f"Message: {result.message}",
            ]
            
            if result.process_id:
                lines.append(f"Process ID: {result.process_id}")
            
            if result.url:
                lines.append(f"URL: {result.url}")
            
            if result.error:
                lines.append(f"Error: {result.error}")
            
            # Add action guidance for already_running status
            if result.status.value == "already_running":
                lines.append("")
                lines.append("⚠️ ACTION REQUIRED: Port is already in use!")
                lines.append(f"   Use kill_process tool to free port {port}, then run again.")
                lines.append(f"   Example: {{'tool': 'kill_process', 'arguments': {{'port': {port}}}}}")
            
            success = result.status.value == "success"
            return ToolResult(success, "\n".join(lines))
            
        except Exception as e:
            return ToolResult(False, "", str(e))


class FileTools:
    """Collection of file tools"""
    
    @staticmethod
    def get_tools() -> list[Tool]:
        """Get all file tools"""
        return [
            ReadFileTool(),
            WriteFileTool(),
            ListDirectoryTool(),
            OpenFileTool(),
            AnalyzeProjectTool(),
            # Note: SmartRunTool removed - use bash tool instead
        ]
