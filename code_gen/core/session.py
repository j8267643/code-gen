"""
Session management for Claude Code
"""
import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


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
    messages: List[Message] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    context_files: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class SessionManager:
    """Manages coding sessions"""

    def __init__(self, work_dir: Path, model: str):
        self.work_dir = work_dir
        self.model = model
        self.session = self._load_or_create_session()

    def _load_or_create_session(self) -> Session:
        """Load existing session or create new one"""
        from code_gen.core.config import settings

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
                print(f"Warning: Failed to load old session {old_session_file}: {e}")

        # Update session with merged messages
        session.messages = all_messages

        # Clean up old session files (optional - keeps directory clean)
        for old_session_file in old_sessions:
            try:
                Path(old_session_file).unlink()
                print(f"Cleaned up old session: {old_session_file}")
            except Exception as e:
                print(f"Warning: Failed to remove old session {old_session_file}: {e}")

        return session

    def add_message(self, role: str, content: str, **metadata) -> None:
        """Add a message to the session"""
        message = Message(
            role=role,
            content=content,
            metadata=metadata
        )
        self.session.messages.append(message)
        self.session.updated_at = datetime.now().isoformat()
        self._save_session()

    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """Get session messages"""
        if limit:
            return self.session.messages[-limit:]
        return self.session.messages

    def clear(self) -> None:
        """Clear session messages"""
        self.session.messages = []
        self.session.updated_at = datetime.now().isoformat()
        self._save_session()

    def _save_session(self) -> None:
        """Save session to disk"""
        from code_gen.core.config import settings

        settings.sessions_dir.mkdir(parents=True, exist_ok=True)
        session_file = settings.sessions_dir / f"{self.session.id}.json"

        # Convert to dict for JSON serialization
        data = asdict(self.session)
        # Convert Path to string
        data["work_dir"] = str(data["work_dir"])

        with open(session_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_history_text(self, limit: Optional[int] = None) -> str:
        """Get conversation history as text"""
        messages = self.get_messages(limit)
        lines = []
        for msg in messages:
            role_emoji = {"user": "👤", "assistant": "🤖", "system": "⚙️"}.get(msg.role, "❓")
            lines.append(f"{role_emoji} **{msg.role}**: {msg.content[:200]}{'...' if len(msg.content) > 200 else ''}")
        return "\n\n".join(lines)

    def get_last_user_message(self) -> Optional[str]:
        """Get the last user message content"""
        for msg in reversed(self.session.messages):
            if msg.role == "user":
                return msg.content
        return None

    def get_last_assistant_message(self) -> Optional[str]:
        """Get the last assistant message content"""
        for msg in reversed(self.session.messages):
            if msg.role == "assistant":
                return msg.content
        return None

    def get_token_count(self) -> int:
        """Estimate total token count"""
        total = 0
        for msg in self.session.messages:
            # Rough estimate: 1 token ≈ 4 characters
            total += len(msg.content) // 4
        return total

    def should_compress(self, threshold: int = 8000) -> bool:
        """Check if context should be compressed"""
        return self.get_token_count() > threshold

    def compress_context(self, keep_recent: int = 10) -> None:
        """Compress context by summarizing old messages"""
        from code_gen.core.config import settings

        if len(self.session.messages) <= keep_recent:
            return

        # Keep recent messages
        recent = self.session.messages[-keep_recent:]

        # Summarize older messages
        old_messages = self.session.messages[:-keep_recent]
        if old_messages:
            summary = f"[Previous conversation: {len(old_messages)} messages summarized]"
            summary_msg = Message(
                role="system",
                content=summary,
                metadata={"compressed": True, "original_count": len(old_messages)}
            )
            self.session.messages = [summary_msg] + recent
            self.session.updated_at = datetime.now().isoformat()
            self._save_session()

    def export(self, format: str = "json") -> str:
        """Export session to various formats"""
        if format == "json":
            data = asdict(self.session)
            data["work_dir"] = str(data["work_dir"])
            return json.dumps(data, indent=2)
        elif format == "markdown":
            lines = [f"# Session: {self.session.id}\n"]
            lines.append(f"**Model**: {self.session.model}\n")
            lines.append(f"**Created**: {self.session.created_at}\n")
            lines.append(f"**Updated**: {self.session.updated_at}\n\n")
            lines.append("## Messages\n\n")
            for msg in self.session.messages:
                lines.append(f"### {msg.role} ({msg.timestamp})\n")
                lines.append(f"{msg.content}\n\n")
            return "".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def delete(self) -> bool:
        """Delete the session file"""
        from code_gen.core.config import settings

        session_file = settings.sessions_dir / f"{self.session.id}.json"
        if session_file.exists():
            session_file.unlink()
            return True
        return False

    def list_all_sessions(self) -> List[dict]:
        """List all available sessions"""
        from code_gen.core.config import settings

        sessions = []
        if settings.sessions_dir.exists():
            for session_file in settings.sessions_dir.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                        sessions.append({
                            "id": data.get("id"),
                            "work_dir": data.get("work_dir"),
                            "model": data.get("model"),
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at"),
                            "message_count": len(data.get("messages", []))
                        })
                except Exception as e:
                    print(f"Warning: Failed to read session {session_file}: {e}")
        return sessions

    @staticmethod
    def load_session(session_id: str, work_dir: Path) -> Optional['SessionManager']:
        """Load a specific session by ID"""
        from code_gen.core.config import settings

        session_file = settings.sessions_dir / f"{session_id}.json"
        if not session_file.exists():
            return None

        try:
            with open(session_file, 'r') as f:
                data = json.load(f)
                model = data.get("model", "claude-3-5-sonnet-20241022")
                manager = SessionManager(work_dir, model)
                # Override with loaded session data
                messages_data = data.get("messages", [])
                manager.session.messages = [
                    Message(**msg) if isinstance(msg, dict) else msg
                    for msg in messages_data
                ]
                manager.session.created_at = data.get("created_at", manager.session.created_at)
                manager.session.updated_at = data.get("updated_at", manager.session.updated_at)
                return manager
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None
