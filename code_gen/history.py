"""
History system for Claude Code
Based on history.ts from TypeScript project
"""
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import json
import hashlib


@dataclass
class HistoryItem:
    """History item"""
    id: str
    type: str  # "message", "command", "tool"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)


class HistorySystem:
    """History system for Claude Code"""
    
    MAX_HISTORY_ITEMS = 100
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.history_path = work_dir / ".claude" / "history.jsonl"
        self.items: list[HistoryItem] = []
        self._load_history()
    
    def _load_history(self):
        """Load history from disk"""
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.history_path.exists():
            try:
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            item = HistoryItem(**data)
                            self.items.append(item)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"Failed to load history: {e}")
    
    def add_item(self, item_type: str, content: str, **metadata) -> HistoryItem:
        """Add a history item"""
        # Generate ID from content hash
        content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
        item_id = f"{item_type}_{content_hash}"
        
        # Check for duplicates
        if any(i.id == item_id for i in self.items):
            return self.items[[i.id for i in self.items].index(item_id)]
        
        # Create item
        item = HistoryItem(
            id=item_id,
            type=item_type,
            content=content,
            metadata=metadata
        )
        
        # Add to list
        self.items.append(item)
        
        # Trim history
        self._trim_history()
        
        # Save to disk
        self._save_item(item)
        
        return item
    
    def _trim_history(self):
        """Trim history to max items"""
        if len(self.items) > self.MAX_HISTORY_ITEMS:
            self.items = self.items[-self.MAX_HISTORY_ITEMS:]
    
    def _save_item(self, item: HistoryItem):
        """Save item to disk"""
        try:
            with open(self.history_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(item.__dict__, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Failed to save item: {e}")
    
    def get_recent_items(self, count: int = 10, item_type: str = None) -> list[HistoryItem]:
        """Get recent items"""
        if item_type:
            items = [i for i in self.items if i.type == item_type]
        else:
            items = self.items
        
        return sorted(items, key=lambda i: i.timestamp, reverse=True)[:count]
    
    def search(self, query: str, limit: int = 10) -> list[HistoryItem]:
        """Search history"""
        query_lower = query.lower()
        results = []
        
        for item in self.items:
            if query_lower in item.content.lower():
                results.append(item)
                
                if len(results) >= limit:
                    break
        
        return results
    
    def clear(self, before: str = None):
        """Clear history"""
        if before:
            self.items = [i for i in self.items if i.timestamp >= before]
        else:
            self.items = []
        
        # Rewrite history file
        self._rewrite_history_file()
    
    def _rewrite_history_file(self):
        """Rewrite history file"""
        try:
            with open(self.history_path, 'w', encoding='utf-8') as f:
                for item in self.items:
                    f.write(json.dumps(item.__dict__, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Failed to rewrite history file: {e}")


# Global history system instance
history_system = None
