"""
Advanced Memory System for Code Gen
Hybrid architecture: SQLite + Markdown + Vector search
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
import json
import sqlite3
import hashlib
import re
from enum import Enum


class MemoryCategory(str, Enum):
    """Memory categories"""
    CONVERSATION = "conversation"  # 对话历史
    KNOWLEDGE = "knowledge"        # 提取的知识
    REFLECTION = "reflection"      # AI 反思
    USER_PREF = "user_pref"        # 用户偏好
    PROJECT = "project"            # 项目信息
    TASK = "task"                  # 任务相关


@dataclass
class MemoryEntry:
    """A memory entry with rich metadata"""
    id: str
    category: MemoryCategory
    content: str
    summary: str = ""                    # 内容摘要
    tags: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)  # 关联的记忆ID
    importance: int = 5                  # 1-10 重要性
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0                # 访问次数
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "category": self.category.value,
            "content": self.content,
            "summary": self.summary,
            "tags": json.dumps(self.tags),
            "links": json.dumps(self.links),
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "metadata": json.dumps(self.metadata)
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryEntry":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            category=MemoryCategory(data["category"]),
            content=data["content"],
            summary=data.get("summary", ""),
            tags=json.loads(data.get("tags", "[]")),
            links=json.loads(data.get("links", "[]")),
            importance=data.get("importance", 5),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
            metadata=json.loads(data.get("metadata", "{}"))
        )


class AdvancedMemorySystem:
    """
    Advanced memory system with:
    - SQLite for metadata and indexing
    - Markdown files for long content
    - Tag-based organization
    - Memory linking/graph
    - Importance scoring
    """
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.memory_dir = work_dir / ".code_gen" / "memory"
        self.db_path = self.memory_dir / "memory.db"
        self.content_dir = self.memory_dir / "content"
        
        # Ensure directories exist
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.content_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Cache for hot data
        self._cache: Dict[str, MemoryEntry] = {}
        self._cache_size = 100
    
    def _init_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    tags TEXT DEFAULT '[]',
                    links TEXT DEFAULT '[]',
                    importance INTEGER DEFAULT 5,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            
            # Create indexes for fast queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON memories(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tags ON memories(tags)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at)")
            
            # Full-text search index
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_search USING fts5(
                    id,
                    content,
                    summary,
                    tags,
                    content='memories',
                    content_rowid='rowid'
                )
            """)
            
            conn.commit()
    
    def _generate_id(self, content: str, category: MemoryCategory) -> str:
        """Generate unique ID for memory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_part = hashlib.md5(content[:100].encode()).hexdigest()[:8]
        return f"{category.value}_{timestamp}_{hash_part}"
    
    def add_memory(
        self,
        content: str,
        category: MemoryCategory,
        summary: str = "",
        tags: List[str] = None,
        links: List[str] = None,
        importance: int = 5,
        metadata: Dict[str, Any] = None
    ) -> MemoryEntry:
        """Add a new memory entry"""
        if tags is None:
            tags = []
        if links is None:
            links = []
        if metadata is None:
            metadata = {}
        
        # Auto-generate summary if not provided
        if not summary:
            summary = self._generate_summary(content)
        
        # Auto-extract tags if not provided
        if not tags:
            tags = self._extract_tags(content)
        
        # Create memory entry
        memory = MemoryEntry(
            id=self._generate_id(content, category),
            category=category,
            content=content,
            summary=summary,
            tags=tags,
            links=links,
            importance=importance,
            metadata=metadata
        )
        
        # Save to database
        self._save_to_db(memory)
        
        # Save long content to markdown file
        if len(content) > 500:
            self._save_content_file(memory)
        
        # Update cache
        self._cache[memory.id] = memory
        
        return memory
    
    def _generate_summary(self, content: str, max_length: int = 200) -> str:
        """Generate summary from content"""
        # Simple summarization - take first few sentences
        sentences = re.split(r'[。！？.!?]', content)
        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) < max_length:
                summary += sentence + " "
            else:
                break
        return summary.strip() or content[:max_length]
    
    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from content"""
        # Simple keyword extraction
        keywords = []
        
        # Look for code-related keywords
        code_keywords = ["python", "javascript", "typescript", "react", "api", 
                        "database", "function", "class", "module", "test"]
        content_lower = content.lower()
        
        for kw in code_keywords:
            if kw in content_lower:
                keywords.append(kw)
        
        return keywords[:5]  # Limit to 5 tags
    
    def _save_to_db(self, memory: MemoryEntry):
        """Save memory to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memories 
                (id, category, content, summary, tags, links, importance, 
                 created_at, updated_at, access_count, last_accessed, metadata)
                VALUES 
                (:id, :category, :content, :summary, :tags, :links, :importance,
                 :created_at, :updated_at, :access_count, :last_accessed, :metadata)
            """, memory.to_dict())
            
            # Update FTS index
            conn.execute("""
                INSERT OR REPLACE INTO memory_search (id, content, summary, tags)
                VALUES (?, ?, ?, ?)
            """, (memory.id, memory.content, memory.summary, json.dumps(memory.tags)))
            
            conn.commit()
    
    def _save_content_file(self, memory: MemoryEntry):
        """Save long content to markdown file"""
        category_dir = self.content_dir / memory.category.value
        category_dir.mkdir(exist_ok=True)
        
        file_path = category_dir / f"{memory.id}.md"
        
        # Build markdown content with metadata
        md_content = f"""---
id: {memory.id}
category: {memory.category.value}
created: {memory.created_at.isoformat()}
updated: {memory.updated_at.isoformat()}
importance: {memory.importance}
tags: {', '.join(memory.tags)}
links: {', '.join(memory.links)}
---

# {memory.summary[:50]}

{memory.content}
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
    
    def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get memory by ID"""
        # Check cache first
        if memory_id in self._cache:
            memory = self._cache[memory_id]
            self._update_access_stats(memory)
            return memory
        
        # Query database
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            
            if row:
                memory = MemoryEntry.from_dict(dict(row))
                self._cache[memory_id] = memory
                self._update_access_stats(memory)
                return memory
        
        return None
    
    def _update_access_stats(self, memory: MemoryEntry):
        """Update access statistics"""
        memory.access_count += 1
        memory.last_accessed = datetime.now()
        
        # Update in database (async would be better)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE memories SET access_count = ?, last_accessed = ? WHERE id = ?",
                (memory.access_count, memory.last_accessed.isoformat(), memory.id)
            )
            conn.commit()
    
    def search_memories(
        self,
        query: str,
        category: MemoryCategory = None,
        tags: List[str] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Search memories with multiple filters"""
        results = []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Build query
            sql = "SELECT * FROM memories WHERE 1=1"
            params = []
            
            if category:
                sql += " AND category = ?"
                params.append(category.value)
            
            if tags:
                for tag in tags:
                    sql += " AND tags LIKE ?"
                    params.append(f'%"{tag}"%')
            
            if query:
                # Simple LIKE search instead of FTS5 to avoid sync issues
                sql += " AND (content LIKE ? OR summary LIKE ?)"
                params.extend([f'%{query}%', f'%{query}%'])
            
            sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(sql, params).fetchall()
            
            for row in rows:
                memory = MemoryEntry.from_dict(dict(row))
                results.append(memory)
                self._cache[memory.id] = memory
        
        return results
    
    def get_memories_by_category(
        self,
        category: MemoryCategory,
        limit: int = 50
    ) -> List[MemoryEntry]:
        """Get memories by category"""
        return self.search_memories("", category=category, limit=limit)
    
    def get_related_memories(self, memory_id: str, limit: int = 5) -> List[MemoryEntry]:
        """Get memories related to given memory"""
        memory = self.get_memory(memory_id)
        if not memory:
            return []
        
        related = []
        
        # Get directly linked memories
        for linked_id in memory.links:
            linked = self.get_memory(linked_id)
            if linked:
                related.append(linked)
        
        # Find memories with similar tags
        if len(related) < limit:
            for tag in memory.tags:
                tag_results = self.search_memories("", tags=[tag], limit=limit)
                for r in tag_results:
                    if r.id != memory_id and r not in related:
                        related.append(r)
                        if len(related) >= limit:
                            break
        
        return related[:limit]
    
    def link_memories(self, memory_id1: str, memory_id2: str):
        """Create bidirectional link between two memories"""
        mem1 = self.get_memory(memory_id1)
        mem2 = self.get_memory(memory_id2)
        
        if mem1 and mem2:
            if memory_id2 not in mem1.links:
                mem1.links.append(memory_id2)
            if memory_id1 not in mem2.links:
                mem2.links.append(memory_id1)
            
            self._save_to_db(mem1)
            self._save_to_db(mem2)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Total count
            stats["total"] = conn.execute(
                "SELECT COUNT(*) FROM memories"
            ).fetchone()[0]
            
            # Count by category
            stats["by_category"] = {}
            for cat in MemoryCategory:
                count = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE category = ?",
                    (cat.value,)
                ).fetchone()[0]
                stats["by_category"][cat.value] = count
            
            # Average importance
            avg_importance = conn.execute(
                "SELECT AVG(importance) FROM memories"
            ).fetchone()[0]
            stats["avg_importance"] = round(avg_importance or 0, 2)
            
            # Most accessed
            most_accessed = conn.execute(
                "SELECT id, access_count FROM memories ORDER BY access_count DESC LIMIT 5"
            ).fetchall()
            stats["most_accessed"] = [{"id": r[0], "count": r[1]} for r in most_accessed]
            
            return stats
    
    def consolidate_memories(self, memory_ids: List[str]) -> Optional[MemoryEntry]:
        """Consolidate multiple memories into one"""
        memories = [self.get_memory(mid) for mid in memory_ids]
        memories = [m for m in memories if m]
        
        if not memories:
            return None
        
        # Combine content
        combined_content = "\n\n---\n\n".join([m.content for m in memories])
        
        # Merge tags
        all_tags = list(set(tag for m in memories for tag in m.tags))
        
        # Use highest importance
        max_importance = max(m.importance for m in memories)
        
        # Create consolidated memory
        consolidated = self.add_memory(
            content=combined_content,
            category=memories[0].category,  # Use first memory's category
            summary=f"Consolidated: {len(memories)} memories",
            tags=all_tags,
            links=[],  # Links will be rebuilt
            importance=max_importance,
            metadata={"consolidated_from": memory_ids}
        )
        
        # Mark original memories as consolidated
        for mem in memories:
            mem.metadata["consolidated_into"] = consolidated.id
            self._save_to_db(mem)
        
        return consolidated
