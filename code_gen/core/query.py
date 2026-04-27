"""
Query engine for Claude Code
Based on QueryEngine.ts from TypeScript project
"""
from typing import Optional, List
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime


@dataclass
class Message:
    """A message in the conversation"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)


@dataclass
class QueryConfig:
    """Query configuration"""
    model: str
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt: str = ""
    tools: List = field(default_factory=list)


class QueryEngine:
    """Query engine for managing conversations"""
    
    def __init__(self, work_dir: Path, model: str):
        self.work_dir = work_dir
        self.model = model
        self.messages: List[Message] = []
        self.total_usage = {"input_tokens": 0, "output_tokens": 0}
        self.abort_controller = AbortController()
        self.permission_denials: List[dict] = []
        self.file_read_state: dict = {}
        self.discovered_skills: set = set()
        self.memory_paths: set = set()
    
    def submit_message(self, role: str, content: str, **metadata) -> Message:
        """Submit a message to the query engine"""
        # Create message
        message = Message(
            role=role,
            content=content,
            metadata=metadata
        )
        
        # Add to messages
        self.messages.append(message)
        
        # Update usage
        self._update_usage(message)
        
        return message
    
    def _update_usage(self, message: Message):
        """Update token usage"""
        # Simple token counting (in real implementation, this would be more sophisticated)
        content = message.content
        tokens = len(content.split())
        
        if message.role == "user":
            self.total_usage["input_tokens"] += tokens
        else:
            self.total_usage["output_tokens"] += tokens
    
    def get_messages(self) -> List[Message]:
        """Get all messages"""
        return self.messages
    
    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """Get recent messages"""
        return self.messages[-count:]
    
    def get_read_file_state(self) -> dict:
        """Get file reading state"""
        return self.file_read_state
    
    def get_session_id(self) -> str:
        """Get session ID"""
        return f"{self.work_dir.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def set_model(self, model: str):
        """Set model"""
        self.model = model
    
    def interrupt(self):
        """Interrupt current operation"""
        self.abort_controller.abort()
    
    def add_permission_denial(self, denial: dict):
        """Add permission denial"""
        self.permission_denials.append(denial)
    
    def discover_skill(self, skill_name: str):
        """Discover a new skill"""
        self.discovered_skills.add(skill_name)
    
    def load_memory_path(self, path: str):
        """Load a memory path"""
        self.memory_paths.add(path)


class AbortController:
    """Abort controller for canceling operations"""
    
    def __init__(self):
        self._aborted = False
    
    def abort(self):
        """Abort operation"""
        self._aborted = True
    
    def signal(self) -> bool:
        """Check if operation should be aborted"""
        return self._aborted
    
    def is_aborted(self) -> bool:
        """Check if aborted"""
        return self._aborted
