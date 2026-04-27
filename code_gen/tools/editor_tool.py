"""
Advanced Text Editor Tool - 高级文本编辑器工具
Based on Trae Agent's str_replace_based_edit_tool
"""
import os
import re
from pathlib import Path
from typing import Optional, List, Tuple
from code_gen.tools.base import Tool, ToolResult


SNIPPET_LINES = 4


class EditorTool(Tool):
    """
    Advanced text editor tool for viewing, creating and editing files
    Based on Trae Agent's str_replace_based_edit_tool
    """
    
    name = "editor"
    description = """Custom editing tool for viewing, creating and editing files
* State is persistent across command calls and discussions with the user
* If `path` is a file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep
* The `create` command cannot be used if the specified `path` already exists as a file !!! If you know that the `path` already exists, please remove it first and then perform the `create` operation!
* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`

Notes for using the `str_replace` command:
* The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!
* If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique
* The `new_str` parameter should contain the edited lines that should replace the `old_str`
"""
    
    input_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The commands to run. Allowed options are: view, create, str_replace, insert",
                "enum": ["view", "create", "str_replace", "insert"],
            },
            "path": {
                "type": "string",
                "description": "Absolute path to file or directory, e.g. 'D:\\project\\file.py' or 'D:\\project'",
            },
            "file_text": {
                "type": "string",
                "description": "Required parameter of `create` command, with the content of the file to be created.",
            },
            "old_str": {
                "type": "string",
                "description": "Required parameter of `str_replace` command containing the string in `path` to replace.",
            },
            "new_str": {
                "type": "string",
                "description": "Optional parameter of `str_replace` command containing the new string (if not given, no string will be added). Required parameter of `insert` command containing the string to insert.",
            },
            "insert_line": {
                "type": "integer",
                "description": "Required parameter of `insert` command. The `new_str` will be inserted AFTER the line `insert_line` of `path`.",
            },
            "view_range": {
                "type": "array",
                "description": "Optional parameter of `view` command when `path` points to a file. If none is given, the full file is shown. If provided, the file will be shown in the indicated line number range, e.g. [11, 12] will show lines 11 and 12. Indexing at 1 to start. Setting `[start_line, -1]` shows all lines from `start_line` to the end of the file.",
                "items": {"type": "integer"},
            },
        },
        "required": ["command", "path"],
    }
    
    async def execute(
        self,
        command: str,
        path: str,
        file_text: Optional[str] = None,
        old_str: Optional[str] = None,
        new_str: Optional[str] = None,
        insert_line: Optional[int] = None,
        view_range: Optional[List[int]] = None,
    ) -> ToolResult:
        """Execute the editor command"""
        try:
            path_obj = Path(path)
            
            if command == "view":
                return await self._view(path_obj, view_range)
            elif command == "create":
                return await self._create(path_obj, file_text)
            elif command == "str_replace":
                return await self._str_replace(path_obj, old_str, new_str)
            elif command == "insert":
                return await self._insert(path_obj, insert_line, new_str)
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Unknown command: {command}"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Editor error: {str(e)}"
            )
    
    async def _view(self, path: Path, view_range: Optional[List[int]] = None) -> ToolResult:
        """View file or directory"""
        if path.is_dir():
            # List directory contents
            return await self._view_directory(path)
        else:
            # View file contents
            return await self._view_file(path, view_range)
    
    async def _view_directory(self, path: Path) -> ToolResult:
        """List directory contents up to 2 levels deep"""
        try:
            lines = []
            lines.append(f"📁 {path.name}/")
            
            # List contents up to 2 levels
            for item in sorted(path.iterdir()):
                if item.name.startswith('.'):
                    continue  # Skip hidden files
                
                if item.is_dir():
                    lines.append(f"  📁 {item.name}/")
                    # List subdirectories one level deep
                    try:
                        for subitem in sorted(item.iterdir()):
                            if subitem.name.startswith('.'):
                                continue
                            if subitem.is_dir():
                                lines.append(f"    📁 {subitem.name}/")
                            else:
                                size = subitem.stat().st_size
                                lines.append(f"    📄 {subitem.name} ({self._format_size(size)})")
                    except PermissionError:
                        lines.append(f"    [Permission Denied]")
                else:
                    size = item.stat().st_size
                    lines.append(f"  📄 {item.name} ({self._format_size(size)})")
            
            return ToolResult(
                success=True,
                content="\n".join(lines),
                error=None
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error viewing directory: {str(e)}"
            )
    
    async def _view_file(self, path: Path, view_range: Optional[List[int]] = None) -> ToolResult:
        """View file contents with line numbers"""
        try:
            if not path.exists():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"File not found: {path}"
                )
            
            content = path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Determine range
            if view_range:
                start = max(0, view_range[0] - 1)  # Convert to 0-indexed
                end = len(lines) if view_range[1] == -1 else min(len(lines), view_range[1])
                lines = lines[start:end]
                line_offset = start
            else:
                line_offset = 0
            
            # Format with line numbers
            max_line_num = line_offset + len(lines)
            line_num_width = len(str(max_line_num))
            
            formatted_lines = []
            for i, line in enumerate(lines):
                line_num = line_offset + i + 1
                formatted_lines.append(f"{line_num:>{line_num_width}} | {line}")
            
            result = "\n".join(formatted_lines)
            
            # Truncate if too long
            if len(result) > 10000:
                result = result[:10000] + "\n\n<response clipped>\n<NOTE>To save on context only part of this file has been shown to you. You should retry this tool with view_range parameter to see specific sections.</NOTE>"
            
            return ToolResult(
                success=True,
                content=result,
                error=None
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error viewing file: {str(e)}"
            )
    
    async def _create(self, path: Path, file_text: Optional[str]) -> ToolResult:
        """Create a new file"""
        try:
            if path.exists():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"File already exists: {path}. Please remove it first if you want to recreate it."
                )
            
            if file_text is None:
                return ToolResult(
                    success=False,
                    content="",
                    error="file_text parameter is required for create command"
                )
            
            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            path.write_text(file_text, encoding='utf-8')
            
            return ToolResult(
                success=True,
                content=f"File created successfully: {path}",
                error=None
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error creating file: {str(e)}"
            )
    
    async def _str_replace(self, path: Path, old_str: Optional[str], new_str: Optional[str]) -> ToolResult:
        """Replace string in file"""
        try:
            if not path.exists():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"File not found: {path}"
                )
            
            if old_str is None:
                return ToolResult(
                    success=False,
                    content="",
                    error="old_str parameter is required for str_replace command"
                )
            
            content = path.read_text(encoding='utf-8')
            
            # Check if old_str exists
            if old_str not in content:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"old_str not found in file. The string must match EXACTLY including whitespace."
                )
            
            # Check if old_str is unique
            if content.count(old_str) > 1:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"old_str appears multiple times in the file. Please include more context to make it unique."
                )
            
            # Perform replacement
            new_content = content.replace(old_str, new_str or "")
            
            # Write back
            path.write_text(new_content, encoding='utf-8')
            
            # Show snippet around the change
            lines_before = content[:content.index(old_str)].count('\n')
            lines_after = new_content.count('\n')
            
            return ToolResult(
                success=True,
                content=f"File updated successfully: {path}\nChanged around line {lines_before + 1}",
                error=None
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error replacing string: {str(e)}"
            )
    
    async def _insert(self, path: Path, insert_line: Optional[int], new_str: Optional[str]) -> ToolResult:
        """Insert text after a specific line"""
        try:
            if not path.exists():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"File not found: {path}"
                )
            
            if insert_line is None:
                return ToolResult(
                    success=False,
                    content="",
                    error="insert_line parameter is required for insert command"
                )
            
            if new_str is None:
                return ToolResult(
                    success=False,
                    content="",
                    error="new_str parameter is required for insert command"
                )
            
            content = path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Insert after the specified line (convert to 0-indexed)
            insert_idx = insert_line
            if insert_idx < 0 or insert_idx > len(lines):
                return ToolResult(
                    success=False,
                    content="",
                    error=f"insert_line {insert_line} is out of range (file has {len(lines)} lines)"
                )
            
            # Insert the new string
            lines.insert(insert_idx, new_str)
            
            # Write back
            new_content = '\n'.join(lines)
            path.write_text(new_content, encoding='utf-8')
            
            return ToolResult(
                success=True,
                content=f"Text inserted successfully at line {insert_line + 1} in {path}",
                error=None
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error inserting text: {str(e)}"
            )
    
    def _format_size(self, size: int) -> str:
        """Format file size"""
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f}KB"
        else:
            return f"{size / (1024 * 1024):.1f}MB"
