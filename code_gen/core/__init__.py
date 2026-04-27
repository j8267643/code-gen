"""
Core module - Essential system components
"""
from .config import settings, Settings, ModelProvider
from .client import BaseAIClient, ClaudeClient, OllamaClient, LMStudioClient
from .session import SessionManager
from .state import AppStateStore, AppState
from .project_analyzer import ProjectAnalyzer, ProjectInfo, ProjectType
from .lsp import LSPClient
from .query import QueryEngine, QueryConfig
from .mcp import MCPClient
from .context_manager import ContextWindowManager, ContextMessage
from .schemas import SDKMessage, ToolUse, ToolResult

__all__ = [
    'settings',
    'Settings',
    'ModelProvider',
    'BaseAIClient',
    'ClaudeClient',
    'OllamaClient',
    'LMStudioClient',
    'SessionManager',
    'AppStateStore',
    'AppState',
    'ProjectAnalyzer',
    'ProjectInfo',
    'ProjectType',
    'LSPClient',
    'QueryEngine',
    'QueryConfig',
    'MCPClient',
    'ContextWindowManager',
    'ContextMessage',
    'SDKMessage',
    'ToolUse',
    'ToolResult',
]
