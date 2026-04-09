"""
Search and code analysis tools
"""
import re
from pathlib import Path

from code_gen.tools.base import Tool, ToolResult


class SearchFilesTool(Tool):
    """Search for text in files"""
    
    name = "search_files"
    description = "Search for text patterns in files"
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Search pattern (regex or plain text)",
            },
            "path": {
                "type": "string",
                "description": "Directory to search in",
                "default": ".",
            },
            "file_pattern": {
                "type": "string",
                "description": "File pattern to match (e.g., *.py)",
                "default": "*",
            },
        },
        "required": ["pattern"],
    }
    
    async def execute(
        self, 
        pattern: str, 
        path: str = ".", 
        file_pattern: str = "*"
    ) -> ToolResult:
        try:
            search_path = Path(path)
            results = []
            
            # Compile regex
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error:
                # If invalid regex, treat as literal
                regex = re.compile(re.escape(pattern), re.IGNORECASE)
            
            # Search files
            for file_path in search_path.rglob(file_pattern):
                if not file_path.is_file():
                    continue
                
                # Skip binary and large files
                try:
                    if file_path.stat().st_size > 1024 * 1024:  # 1MB
                        continue
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        
                    for i, line in enumerate(lines, 1):
                        if regex.search(line):
                            rel_path = file_path.relative_to(search_path)
                            results.append(f"{rel_path}:{i}: {line.strip()}")
                            
                except (UnicodeDecodeError, PermissionError):
                    continue
            
            if not results:
                return ToolResult(True, "No matches found")
            
            return ToolResult(True, '\n'.join(results[:50]))  # Limit results
            
        except Exception as e:
            return ToolResult(False, "", str(e))


class GetFileInfoTool(Tool):
    """Get detailed file information"""
    
    name = "get_file_info"
    description = "Get detailed information about a file"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file",
            },
        },
        "required": ["path"],
    }
    
    async def execute(self, path: str) -> ToolResult:
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return ToolResult(False, "", f"File not found: {path}")
            
            stat = file_path.stat()
            
            info = {
                "Path": str(file_path.absolute()),
                "Type": "Directory" if file_path.is_dir() else "File",
                "Size": f"{stat.st_size} bytes",
                "Created": str(stat.st_ctime),
                "Modified": str(stat.st_mtime),
            }
            
            if file_path.is_file():
                # Count lines
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = sum(1 for _ in f)
                    info["Lines"] = str(lines)
                except:
                    pass
            
            content = '\n'.join(f"{k}: {v}" for k, v in info.items())
            return ToolResult(True, content)
            
        except Exception as e:
            return ToolResult(False, "", str(e))


class SearchTools:
    """Collection of search tools"""
    
    @staticmethod
    def get_tools() -> list[Tool]:
        """Get all search tools"""
        return [
            SearchFilesTool(),
            GetFileInfoTool(),
        ]
