"""
Session management for Claude Code
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

from rich.console import Console

console = Console()


@dataclass
class Snapshot:
    """A snapshot of a session at a point in time"""
    id: str
    session_id: str
    name: str
    created_at: str
    messages_count: int
    context_files_count: int
    snapshot_path: str


@dataclass
class Message:
    """A message in the conversation"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)


@dataclass
class Session:
    """A coding session"""
    id: str
    work_dir: Path
    model: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    messages: list[Message] = field(default_factory=list)
    context_files: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class SessionManager:
    """Manages coding sessions"""
    
    def __init__(self, work_dir: Path, model: str):
        self.work_dir = work_dir
        self.model = model
        self.session = self._load_or_create_session()
        
    def _load_or_create_session(self) -> Session:
        """Load existing session or create new one"""
        from code_gen.config import settings
        
        # Use work directory name as session identifier (persistent across runs)
        # Handle both absolute and relative paths, and get the actual directory name
        work_dir_name = self.work_dir.name
        if not work_dir_name:
            work_dir_name = self.work_dir.resolve().name
        session_id = f"{work_dir_name}_session"
        session_file = settings.sessions_dir / f"{session_id}.json"
        
        if session_file.exists():
            with open(session_file, 'r') as f:
                data = json.load(f)
                # Convert message dicts to Message objects
                messages_data = data.get("messages", [])
                messages = []
                for msg_data in messages_data:
                    if isinstance(msg_data, dict):
                        messages.append(Message(
                            role=msg_data.get("role", ""),
                            content=msg_data.get("content", ""),
                            timestamp=msg_data.get("timestamp", ""),
                            metadata=msg_data.get("metadata", {})
                        ))
                    else:
                        messages.append(msg_data)
                data["messages"] = messages
                
                session = Session(**data)
                
                # Try to merge with old sessions (with timestamp) if they exist
                session = self._merge_old_sessions(session, settings.sessions_dir)
                
                return session
        
        # Check for old sessions to merge
        session = Session(
            id=session_id,
            work_dir=self.work_dir,
            model=self.model,
        )
        session = self._merge_old_sessions(session, settings.sessions_dir)
        
        return session
    
    def _merge_old_sessions(self, session: Session, sessions_dir: Path) -> Session:
        """Merge old sessions with timestamp to preserve history"""
        import glob
        
        # Find all old sessions for this work directory
        pattern = str(sessions_dir / f"{self.work_dir.name}_*.json")
        old_sessions = glob.glob(pattern)
        
        # Filter out the current session file
        current_file = str(sessions_dir / f"{session.id}.json")
        old_sessions = [f for f in old_sessions if f != current_file]
        
        if not old_sessions:
            return session
        
        # Load all old sessions and merge messages
        all_messages = session.messages.copy()
        
        for old_session_file in sorted(old_sessions):
            try:
                with open(old_session_file, 'r') as f:
                    data = json.load(f)
                    old_messages_data = data.get("messages", [])
                    
                    # Add messages from old session (avoid duplicates)
                    for msg_data in old_messages_data:
                        # Check if message already exists (compare dicts)
                        exists = False
                        for m in all_messages:
                            if isinstance(m, Message):
                                exists = (m.role == msg_data.get("role") and 
                                        m.content == msg_data.get("content") and 
                                        m.timestamp == msg_data.get("timestamp"))
                            else:
                                # m is a dict
                                exists = (m.get("role") == msg_data.get("role") and 
                                        m.get("content") == msg_data.get("content") and 
                                        m.get("timestamp") == msg_data.get("timestamp"))
                            if exists:
                                break
                        
                        if not exists:
                            # Create Message object from dict
                            msg = Message(
                                role=msg_data.get("role", ""),
                                content=msg_data.get("content", ""),
                                timestamp=msg_data.get("timestamp", "")
                            )
                            all_messages.append(msg)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to merge {old_session_file}: {e}[/yellow]")
        
        # Update session with merged messages
        session.messages = all_messages
        session.updated_at = datetime.now().isoformat()
        
        # Clean up old session files (only after successful merge)
        for old_session_file in old_sessions:
            try:
                import os
                if os.path.exists(old_session_file):
                    os.remove(old_session_file)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to remove {old_session_file}: {e}[/yellow]")
        
        return session
    
    def add_message(self, role: str, content: str, **metadata) -> Message:
        """Add a message to the session"""
        message = Message(
            role=role,
            content=content,
            metadata=metadata
        )
        self.session.messages.append(message)
        self.session.updated_at = datetime.now().isoformat()
        self._save_session()
        return message
    
    def get_messages(self) -> list[Message]:
        """Get all messages"""
        return self.session.messages
    
    def get_recent_messages(self, count: int = 10) -> list[Message]:
        """Get recent messages"""
        return self.session.messages[-count:]
    
    def add_context_file(self, file_path: str):
        """Add a file to session context"""
        if file_path not in self.session.context_files:
            self.session.context_files.append(file_path)
            self._save_session()
    
    def _save_session(self):
        """Save session to disk"""
        from code_gen.config import settings
        
        session_file = settings.sessions_dir / f"{self.session.id}.json"
        
        # Convert to dict for JSON serialization
        data = {
            "id": self.session.id,
            "work_dir": str(self.session.work_dir),
            "model": self.session.model,
            "created_at": self.session.created_at,
            "updated_at": self.session.updated_at,
            "messages": [
                {
                    "role": m.role if isinstance(m, Message) else m.get("role", ""),
                    "content": m.content if isinstance(m, Message) else m.get("content", ""),
                    "timestamp": m.timestamp if isinstance(m, Message) else m.get("timestamp", ""),
                    "metadata": m.metadata if isinstance(m, Message) else m.get("metadata", {})
                }
                for m in self.session.messages
            ],
            "context_files": self.session.context_files,
            "metadata": self.session.metadata,
        }
        
        with open(session_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def clear(self):
        """Clear session messages"""
        self.session.messages = []
        self._save_session()
    
    def create_snapshot(self, name: str = None) -> Snapshot:
        """Create a snapshot of the current session state"""
        from code_gen.config import settings
        
        if name is None:
            name = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        snapshot_id = f"{self.session.id}_{name}"
        snapshot_dir = settings.snapshots_dir / snapshot_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        snapshot = Snapshot(
            id=snapshot_id,
            session_id=self.session.id,
            name=name,
            created_at=datetime.now().isoformat(),
            messages_count=len(self.session.messages),
            context_files_count=len(self.session.context_files),
            snapshot_path=str(snapshot_dir)
        )
        
        snapshot_file = snapshot_dir / "snapshot.json"
        
        data = {
            "id": snapshot.id,
            "session_id": snapshot.session_id,
            "name": snapshot.name,
            "created_at": snapshot.created_at,
            "messages_count": snapshot.messages_count,
            "context_files_count": snapshot.context_files_count,
            "session_data": {
                "id": self.session.id,
                "work_dir": str(self.session.work_dir),
                "model": self.session.model,
                "created_at": self.session.created_at,
                "updated_at": self.session.updated_at,
                "messages": [
                    {
                        "role": m.role if isinstance(m, Message) else m.get("role", ""),
                        "content": m.content if isinstance(m, Message) else m.get("content", ""),
                        "timestamp": m.timestamp if isinstance(m, Message) else m.get("timestamp", ""),
                        "metadata": m.metadata if isinstance(m, Message) else m.get("metadata", {})
                    }
                    for m in self.session.messages
                ],
                "context_files": self.session.context_files,
                "metadata": self.session.metadata,
            }
        }
        
        with open(snapshot_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return snapshot
    
    def get_snapshots(self) -> list[Snapshot]:
        """Get all snapshots for this session"""
        from code_gen.config import settings
        
        snapshots = []
        
        if not settings.snapshots_dir.exists():
            return snapshots
        
        for snapshot_dir in settings.snapshots_dir.iterdir():
            if snapshot_dir.is_dir():
                snapshot_file = snapshot_dir / "snapshot.json"
                if snapshot_file.exists():
                    try:
                        with open(snapshot_file, 'r') as f:
                            data = json.load(f)
                            if data.get("session_id") == self.session.id:
                                snapshots.append(Snapshot(**data))
                    except Exception:
                        continue
        
        return sorted(snapshots, key=lambda x: x.created_at, reverse=True)
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """Get a specific snapshot by ID"""
        from code_gen.config import settings
        
        snapshot_dir = settings.snapshots_dir / snapshot_id
        snapshot_file = snapshot_dir / "snapshot.json"
        
        if snapshot_file.exists():
            try:
                with open(snapshot_file, 'r') as f:
                    data = json.load(f)
                    return Snapshot(**data)
            except Exception:
                return None
        
        return None
    
    def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restore a session from a snapshot"""
        from code_gen.config import settings
        
        snapshot_dir = settings.snapshots_dir / snapshot_id
        snapshot_file = snapshot_dir / "snapshot.json"
        
        if not snapshot_file.exists():
            return False
        
        try:
            with open(snapshot_file, 'r') as f:
                data = json.load(f)
            
            session_data = data.get("session_data", {})
            
            self.session.id = session_data.get("id", self.session.id)
            self.session.work_dir = Path(session_data.get("work_dir", str(self.work_dir)))
            self.session.model = session_data.get("model", self.model)
            self.session.created_at = session_data.get("created_at", self.session.created_at)
            self.session.updated_at = datetime.now().isoformat()
            self.session.messages = [
                Message(**m) if isinstance(m, dict) else m for m in session_data.get("messages", [])
            ]
            self.session.context_files = session_data.get("context_files", [])
            self.session.metadata = session_data.get("metadata", {})
            
            self._save_session()
            return True
        except Exception:
            return False
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot"""
        from code_gen.config import settings
        
        snapshot_dir = settings.snapshots_dir / snapshot_id
        
        if not snapshot_dir.exists():
            return False
        
        try:
            shutil.rmtree(snapshot_dir)
            return True
        except Exception:
            return False
