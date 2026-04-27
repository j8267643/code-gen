"""
JSON Editor Tool - JSON 文件编辑器工具
Based on Trae Agent's json_edit_tool
"""
import json
from pathlib import Path
from typing import Optional, Any, List
from code_gen.tools.base import Tool, ToolResult


class JSONEditorTool(Tool):
    """
    Tool for editing JSON files with JSONPath-like expressions
    Based on Trae Agent's json_edit_tool
    """
    
    name = "json_editor"
    description = """Tool for editing JSON files with path expressions
* Supports targeted modifications to JSON structures using dot notation paths
* Operations: view, set, add, remove
* Path examples: 'users[0].name', 'config.database.host', 'items'
* Safe JSON parsing and validation with detailed error messages
* Preserves JSON formatting where possible

Operation details:
- `view`: Display JSON content or specific paths
- `set`: Update existing values at specified paths
- `add`: Add new key-value pairs (for objects) or append to arrays
- `remove`: Delete elements at specified paths

Path syntax supported:
- Use dot notation for object properties: 'config.database.host'
- Use bracket notation for array indices: 'users[0]'
- Use bracket notation for object keys with special chars: 'config["api-key"]'
"""
    
    input_schema = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "The operation to perform on the JSON file",
                "enum": ["view", "set", "add", "remove"],
            },
            "file_path": {
                "type": "string",
                "description": "The full, ABSOLUTE path to the JSON file to edit",
            },
            "path": {
                "type": "string",
                "description": "Path expression to specify the target location (e.g., 'users[0].name', 'config.database'). Required for set, add, and remove operations. Optional for view to show specific paths.",
            },
            "value": {
                "type": "object",
                "description": "The value to set or add. Must be JSON-serializable. Required for set and add operations.",
            },
            "pretty_print": {
                "type": "boolean",
                "description": "Whether to format the JSON output with proper indentation. Defaults to true.",
                "default": True,
            },
        },
        "required": ["operation", "file_path"],
    }
    
    async def execute(
        self,
        operation: str,
        file_path: str,
        path: Optional[str] = None,
        value: Optional[Any] = None,
        pretty_print: bool = True,
    ) -> ToolResult:
        """Execute the JSON edit operation"""
        try:
            path_obj = Path(file_path)
            
            if not path_obj.exists():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"File not found: {file_path}"
                )
            
            # Read and parse JSON
            try:
                content = path_obj.read_text(encoding='utf-8')
                data = json.loads(content)
            except json.JSONDecodeError as e:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Invalid JSON: {str(e)}"
                )
            
            if operation == "view":
                return await self._view(data, path, pretty_print)
            elif operation == "set":
                return await self._set(data, path, value, path_obj, pretty_print)
            elif operation == "add":
                return await self._add(data, path, value, path_obj, pretty_print)
            elif operation == "remove":
                return await self._remove(data, path, path_obj, pretty_print)
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Unknown operation: {operation}"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"JSON editor error: {str(e)}"
            )
    
    async def _view(self, data: Any, path: Optional[str], pretty_print: bool) -> ToolResult:
        """View JSON content"""
        try:
            if path:
                # Navigate to specific path
                result = self._get_value_at_path(data, path)
                if result is None:
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"Path not found: {path}"
                    )
            else:
                result = data
            
            # Format output
            if pretty_print:
                output = json.dumps(result, indent=2, ensure_ascii=False)
            else:
                output = json.dumps(result, ensure_ascii=False)
            
            # Truncate if too long
            if len(output) > 10000:
                output = output[:10000] + "\n\n<response clipped>\n<NOTE>To save on context only part of this JSON has been shown to you.</NOTE>"
            
            return ToolResult(
                success=True,
                content=output,
                error=None
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error viewing JSON: {str(e)}"
            )
    
    async def _set(
        self,
        data: Any,
        path: Optional[str],
        value: Optional[Any],
        file_path: Path,
        pretty_print: bool
    ) -> ToolResult:
        """Set a value at a specific path"""
        try:
            if not path:
                return ToolResult(
                    success=False,
                    content="",
                    error="Path is required for set operation"
                )
            
            if value is None:
                return ToolResult(
                    success=False,
                    content="",
                    error="Value is required for set operation"
                )
            
            # Set value at path
            success = self._set_value_at_path(data, path, value)
            if not success:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Could not set value at path: {path}"
                )
            
            # Write back
            if pretty_print:
                output = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                output = json.dumps(data, ensure_ascii=False)
            
            file_path.write_text(output, encoding='utf-8')
            
            return ToolResult(
                success=True,
                content=f"Value set successfully at path: {path}",
                error=None
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error setting JSON value: {str(e)}"
            )
    
    async def _add(
        self,
        data: Any,
        path: Optional[str],
        value: Optional[Any],
        file_path: Path,
        pretty_print: bool
    ) -> ToolResult:
        """Add a value to an array or object"""
        try:
            if not path:
                return ToolResult(
                    success=False,
                    content="",
                    error="Path is required for add operation"
                )
            
            if value is None:
                return ToolResult(
                    success=False,
                    content="",
                    error="Value is required for add operation"
                )
            
            # Get parent
            parent_path, key = self._split_path(path)
            if parent_path:
                parent = self._get_value_at_path(data, parent_path)
            else:
                parent = data
                key = path
            
            if parent is None:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Parent path not found: {parent_path}"
                )
            
            # Add to array or object
            if isinstance(parent, list):
                if key == "":
                    # Append to array
                    parent.append(value)
                else:
                    try:
                        idx = int(key)
                        parent.insert(idx, value)
                    except ValueError:
                        return ToolResult(
                            success=False,
                            content="",
                            error=f"Cannot add to list with key: {key}"
                        )
            elif isinstance(parent, dict):
                parent[key] = value
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Cannot add to type: {type(parent)}"
                )
            
            # Write back
            if pretty_print:
                output = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                output = json.dumps(data, ensure_ascii=False)
            
            file_path.write_text(output, encoding='utf-8')
            
            return ToolResult(
                success=True,
                content=f"Value added successfully at path: {path}",
                error=None
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error adding JSON value: {str(e)}"
            )
    
    async def _remove(
        self,
        data: Any,
        path: Optional[str],
        file_path: Path,
        pretty_print: bool
    ) -> ToolResult:
        """Remove a value at a specific path"""
        try:
            if not path:
                return ToolResult(
                    success=False,
                    content="",
                    error="Path is required for remove operation"
                )
            
            # Get parent
            parent_path, key = self._split_path(path)
            if parent_path:
                parent = self._get_value_at_path(data, parent_path)
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error="Cannot remove root element"
                )
            
            if parent is None:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Parent path not found: {parent_path}"
                )
            
            # Remove from array or object
            if isinstance(parent, list):
                try:
                    idx = int(key)
                    del parent[idx]
                except (ValueError, IndexError) as e:
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"Cannot remove from list: {str(e)}"
                    )
            elif isinstance(parent, dict):
                if key in parent:
                    del parent[key]
                else:
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"Key not found: {key}"
                    )
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Cannot remove from type: {type(parent)}"
                )
            
            # Write back
            if pretty_print:
                output = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                output = json.dumps(data, ensure_ascii=False)
            
            file_path.write_text(output, encoding='utf-8')
            
            return ToolResult(
                success=True,
                content=f"Value removed successfully at path: {path}",
                error=None
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error removing JSON value: {str(e)}"
            )
    
    def _get_value_at_path(self, data: Any, path: str) -> Any:
        """Get value at a path expression"""
        parts = self._parse_path(path)
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                if part not in current:
                    return None
                current = current[part]
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    if idx < 0 or idx >= len(current):
                        return None
                    current = current[idx]
                except ValueError:
                    return None
            else:
                return None
        
        return current
    
    def _set_value_at_path(self, data: Any, path: str, value: Any) -> bool:
        """Set value at a path expression"""
        parts = self._parse_path(path)
        current = data
        
        for i, part in enumerate(parts[:-1]):
            if isinstance(current, dict):
                if part not in current:
                    # Create intermediate objects if needed
                    next_part = parts[i + 1]
                    try:
                        int(next_part)
                        current[part] = []
                    except ValueError:
                        current[part] = {}
                current = current[part]
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    if idx < 0 or idx >= len(current):
                        return False
                    current = current[idx]
                except ValueError:
                    return False
            else:
                return False
        
        # Set final value
        final_part = parts[-1]
        if isinstance(current, dict):
            current[final_part] = value
            return True
        elif isinstance(current, list):
            try:
                idx = int(final_part)
                if idx < 0:
                    return False
                # Extend list if needed
                while len(current) <= idx:
                    current.append(None)
                current[idx] = value
                return True
            except ValueError:
                return False
        
        return False
    
    def _split_path(self, path: str) -> tuple:
        """Split path into parent and key"""
        parts = self._parse_path(path)
        if len(parts) == 1:
            return ("", parts[0])
        return (".".join(parts[:-1]), parts[-1])
    
    def _parse_path(self, path: str) -> List[str]:
        """Parse path expression into parts"""
        parts = []
        current = ""
        in_bracket = False
        
        for char in path:
            if char == '[':
                if current:
                    parts.append(current)
                    current = ""
                in_bracket = True
            elif char == ']':
                if current:
                    parts.append(current)
                    current = ""
                in_bracket = False
            elif char == '.' and not in_bracket:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char
        
        if current:
            parts.append(current)
        
        return parts
