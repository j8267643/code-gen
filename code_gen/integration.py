"""
Integration module for Claude Code
Combines all new features into a unified system
"""
from pathlib import Path
from typing import Optional

# Import all new modules
from .permissions import permission_system, PermissionSystem
from .state import app_state, AppStateStore
from .query import QueryEngine, AbortController
from .mcp import mcp_manager, MCPClientManager
from .compact import compressor, ContextCompressor
from .memory import memory_system, MemorySystem
from .cost_tracker import cost_tracker, CostTracker
from .history import history_system, HistorySystem
from .plugins import plugin_loader, PluginLoader
from .skills import skill_system, SkillSystem
from .prompt_suggestions import prompt_suggestion_system, PromptSuggestionSystem
from .lsp import lsp_client, LSPClient
from .security import SecurityMonitor, SecurityConfig
from .schemas import ControlRequest, ControlResponse, SDKMessage, ToolUse, ToolResult


class ClaudeCodeIntegration:
    """Main integration class for Claude Code"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.security_monitor: Optional[SecurityMonitor] = None
        self._initialize_systems()
    
    def _initialize_systems(self):
        """Initialize all systems"""
        global memory_system, cost_tracker, history_system, plugin_loader
        global skill_system, prompt_suggestion_system, lsp_client
        
        # Initialize global systems
        memory_system = MemorySystem(self.work_dir)
        cost_tracker = CostTracker(self.work_dir)
        history_system = HistorySystem(self.work_dir)
        plugin_loader = PluginLoader(self.work_dir)
        skill_system = SkillSystem(self.work_dir)
        prompt_suggestion_system = PromptSuggestionSystem(self.work_dir)
        
        # Initialize security monitor
        self.security_monitor = SecurityMonitor(self.work_dir, SecurityConfig())
        
        # Load plugins
        plugin_loader.load_bundled_plugins()
        plugin_loader.load_project_plugins()
        
        # Load skills
        skill_system.load_skills()
    
    def create_query_engine(self, model: str) -> QueryEngine:
        """Create a new query engine"""
        return QueryEngine(self.work_dir, model)
    
    def get_mcp_manager(self) -> MCPClientManager:
        """Get MCP manager"""
        return mcp_manager
    
    def get_compressor(self) -> ContextCompressor:
        """Get context compressor"""
        return compressor
    
    def get_permission_system(self) -> PermissionSystem:
        """Get permission system"""
        return permission_system
    
    def get_state_store(self) -> AppStateStore:
        """Get state store"""
        return app_state
    
    def get_cost_tracker(self) -> CostTracker:
        """Get cost tracker"""
        return cost_tracker
    
    def get_history_system(self) -> HistorySystem:
        """Get history system"""
        return history_system
    
    def get_plugin_loader(self) -> PluginLoader:
        """Get plugin loader"""
        return plugin_loader
    
    def get_skill_system(self) -> SkillSystem:
        """Get skill system"""
        return skill_system
    
    def get_prompt_suggestion_system(self) -> PromptSuggestionSystem:
        """Get prompt suggestion system"""
        return prompt_suggestion_system
    
    def get_security_monitor(self) -> SecurityMonitor:
        """Get security monitor"""
        return self.security_monitor
    
    def get_lsp_client(self, server_command: str) -> LSPClient:
        """Get LSP client"""
        global lsp_client
        if lsp_client is None:
            lsp_client = LSPClient(server_command, self.work_dir)
        return lsp_client
    
    def get_memory_system(self) -> MemorySystem:
        """Get memory system"""
        return memory_system
    
    def get_all_tools(self) -> list:
        """Get all available tools from all sources"""
        all_tools = []
        
        # Add built-in tools
        from code_gen.tools.files import FileTools
        from code_gen.tools.shell import ShellTools
        from code_gen.tools.git import GitTools
        from code_gen.tools.search import SearchTools
        
        all_tools.extend(FileTools.get_tools())
        all_tools.extend(ShellTools.get_tools())
        all_tools.extend(GitTools.get_tools())
        all_tools.extend(SearchTools.get_tools())
        
        # Add MCP tools
        mcp_tools = mcp_manager.get_all_tools()
        all_tools.extend(mcp_tools)
        
        # Add skill tools (skills as tools)
        for skill in skill_system.skills.values():
            if skill.enabled:
                all_tools.append(skill)
        
        return all_tools


# Global integration instance
integration_instance = None
