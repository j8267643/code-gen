"""
State management for Claude Code
Based on AppStateStore.ts from TypeScript project
"""
from dataclasses import dataclass, field
from typing import Optional, Any, Callable
from pathlib import Path
import json
import threading
from enum import Enum


@dataclass
class AppState:
    """Application state"""
    # Tasks
    tasks: list[dict] = field(default_factory=list)
    
    # MCP
    mcp_clients: list[dict] = field(default_factory=list)
    
    # Plugins
    plugins: list[dict] = field(default_factory=list)
    
    # Notifications
    notifications: list[dict] = field(default_factory=list)
    
    # Elicitation
    elicitation: Optional[dict] = None
    
    # Worker sandbox permissions
    worker_sandbox_permissions: dict = field(default_factory=dict)
    
    # Prompt suggestions
    prompt_suggestions: list[dict] = field(default_factory=list)
    
    # Skill improvements
    skill_improvements: list[dict] = field(default_factory=list)
    
    # Session state
    current_session: Optional[str] = None
    
    # Permission state
    permission_mode: str = "auto"
    
    # Tool state
    in_progress_tool_ids: list[str] = field(default_factory=list)
    
    # Response state
    response_length: int = 0
    
    # Stream mode
    stream_mode: str = "normal"
    
    # File history
    file_history: dict = field(default_factory=dict)
    
    # Attribution
    attribution: dict = field(default_factory=dict)
    
    # Memory
    memories: list[dict] = field(default_factory=list)
    
    # Context
    context_files: list[str] = field(default_factory=list)
    
    # Usage
    token_usage: dict = field(default_factory=dict)


class AppStateStore:
    """Application state store"""
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path.home() / ".config" / "claude-code"
        self.state = AppState()
        self._listeners: list[Callable[[AppState], None]] = []
        self._lock = threading.Lock()
        self._load_state()
    
    def _load_state(self):
        """Load state from disk"""
        state_file = self.config_dir / "state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    # Convert dict to AppState
                    self.state = AppState(**data)
            except Exception as e:
                print(f"Failed to load state: {e}")
    
    def _save_state(self):
        """Save state to disk"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        state_file = self.config_dir / "state.json"
        try:
            with open(state_file, 'w') as f:
                json.dump(self.state.__dict__, f, indent=2, default=str)
        except Exception as e:
            print(f"Failed to save state: {e}")
    
    def get_state(self) -> AppState:
        """Get current state"""
        with self._lock:
            return self.state
    
    def set_state(self, updater: Callable[[AppState], AppState]):
        """Update state with updater function"""
        with self._lock:
            self.state = updater(self.state)
            self._save_state()
            self._notify_listeners()
    
    def update(self, **kwargs):
        """Update state fields"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, value)
            self._save_state()
            self._notify_listeners()
    
    def subscribe(self, listener: Callable[[AppState], None]):
        """Subscribe to state changes"""
        self._listeners.append(listener)
    
    def _notify_listeners(self):
        """Notify listeners of state changes"""
        for listener in self._listeners:
            try:
                listener(self.state)
            except Exception as e:
                print(f"Listener error: {e}")
    
    def get_app_state(self) -> AppState:
        """Get app state (alias for get_state)"""
        return self.get_state()
    
    def set_app_state(self, updater: Callable[[AppState], AppState]):
        """Set app state (alias for set_state)"""
        self.set_state(updater)


# Global state instance
app_state = AppStateStore()
