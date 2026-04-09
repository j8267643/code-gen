"""
Git operation tools
"""
import subprocess
from pathlib import Path

from code_gen.tools.base import Tool, ToolResult


class GitStatusTool(Tool):
    """Check git status"""
    
    name = "git_status"
    description = "Check the git status of the repository"
    input_schema = {
        "type": "object",
        "properties": {},
    }
    
    async def execute(self) -> ToolResult:
        try:
            result = subprocess.run(
                ['git', 'status', '--short'],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )
            
            if result.returncode != 0:
                return ToolResult(False, "", "Not a git repository or git error")
            
            output = result.stdout.strip()
            if not output:
                return ToolResult(True, "Working tree clean")
            
            return ToolResult(True, output)
            
        except Exception as e:
            return ToolResult(False, "", str(e))


class GitDiffTool(Tool):
    """Show git diff"""
    
    name = "git_diff"
    description = "Show git diff for changes"
    input_schema = {
        "type": "object",
        "properties": {
            "staged": {
                "type": "boolean",
                "description": "Show staged changes",
                "default": False,
            },
            "file": {
                "type": "string",
                "description": "Specific file to diff",
            },
        },
    }
    
    async def execute(self, staged: bool = False, file: str = None) -> ToolResult:
        try:
            cmd = ['git', 'diff']
            if staged:
                cmd.append('--staged')
            if file:
                cmd.append(file)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )
            
            output = result.stdout.strip()
            if not output:
                return ToolResult(True, "No changes to show")
            
            return ToolResult(True, output)
            
        except Exception as e:
            return ToolResult(False, "", str(e))


class GitLogTool(Tool):
    """Show git log"""
    
    name = "git_log"
    description = "Show recent git commits"
    input_schema = {
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "Number of commits to show",
                "default": 10,
            },
        },
    }
    
    async def execute(self, count: int = 10) -> ToolResult:
        try:
            result = subprocess.run(
                ['git', 'log', f'--max-count={count}', '--oneline', '--decorate'],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )
            
            if result.returncode != 0:
                return ToolResult(False, "", "Git error")
            
            return ToolResult(True, result.stdout.strip())
            
        except Exception as e:
            return ToolResult(False, "", str(e))


class GitTools:
    """Collection of git tools"""
    
    @staticmethod
    def get_tools() -> list[Tool]:
        """Get all git tools"""
        return [
            GitStatusTool(),
            GitDiffTool(),
            GitLogTool(),
        ]
