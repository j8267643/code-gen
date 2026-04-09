"""
File operation tools
"""
import os
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
            file_path = Path(path)
            
            if not file_path.exists():
                return ToolResult(False, "", f"File not found: {path}")
            
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
            file_path = Path(path)
            
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return ToolResult(True, f"File written successfully: {path}")
            
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
        },
    }
    
    async def execute(self, path: str = ".") -> ToolResult:
        try:
            dir_path = Path(path)
            
            if not dir_path.exists():
                return ToolResult(False, "", f"Directory not found: {path}")
            
            if not dir_path.is_dir():
                return ToolResult(False, "", f"Not a directory: {path}")
            
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
        ]
