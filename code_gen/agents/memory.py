"""
Memory System - 记忆系统
Inspired by PraisonAI's Memory System

支持多层级记忆：
1. Short-term Memory (STM) - 短期记忆/上下文
2. Long-term Memory (LTM) - 长期记忆/持久化知识
3. Entity Memory - 实体记忆
4. Episodic Memory - 情景记忆

存储后端：
- File (JSON) - 文件存储
- SQLite - 数据库存储
- ChromaDB - 向量数据库存储
"""
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
import json
import sqlite3
import hashlib
import re


class MemoryType(str, Enum):
    """记忆类型"""
    SHORT_TERM = "short_term"    # 短期记忆
    LONG_TERM = "long_term"      # 长期记忆
    ENTITY = "entity"            # 实体记忆
    EPISODIC = "episodic"        # 情景记忆


class StorageBackend(str, Enum):
    """存储后端类型"""
    FILE = "file"           # JSON文件
    SQLITE = "sqlite"       # SQLite数据库
    MEMORY = "memory"       # 内存（临时）


@dataclass
class MemoryEntry:
    """记忆条目"""
    content: str
    memory_type: MemoryType
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    importance: float = 0.5  # 0-1，重要性评分
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: hashlib.md5(
        datetime.now().isoformat().encode()).hexdigest()[:12])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """从字典创建"""
        return cls(
            id=data.get("id", ""),
            content=data.get("content", ""),
            memory_type=MemoryType(data.get("memory_type", "short_term")),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            importance=data.get("importance", 0.5),
            metadata=data.get("metadata", {})
        )


@dataclass
class MemoryConfig:
    """记忆系统配置"""
    backend: StorageBackend = StorageBackend.FILE
    storage_path: Path = field(default_factory=lambda: Path(".memory"))
    user_id: str = "default"
    
    # 短期记忆配置
    short_term_limit: int = 100
    short_term_ttl: int = 24  # 小时
    
    # 长期记忆配置
    long_term_limit: int = 1000
    importance_threshold: float = 0.7  # 自动晋升到长期记忆的阈值
    auto_promote: bool = True
    
    # 实体记忆配置
    entity_extraction: bool = True
    
    # 情景记忆配置
    episodic_retention_days: int = 30
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.storage_path, str):
            self.storage_path = Path(self.storage_path)


class BaseMemoryStore:
    """记忆存储基类"""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
    
    def store(self, entry: MemoryEntry) -> bool:
        """存储记忆"""
        raise NotImplementedError
    
    def retrieve(self, memory_type: MemoryType, limit: int = 10) -> List[MemoryEntry]:
        """检索记忆"""
        raise NotImplementedError
    
    def search(self, query: str, memory_type: Optional[MemoryType] = None, 
               limit: int = 10) -> List[MemoryEntry]:
        """搜索记忆"""
        raise NotImplementedError
    
    def delete(self, entry_id: str) -> bool:
        """删除记忆"""
        raise NotImplementedError
    
    def clear(self, memory_type: Optional[MemoryType] = None):
        """清空记忆"""
        raise NotImplementedError


class FileMemoryStore(BaseMemoryStore):
    """文件存储后端 (JSON)"""
    
    def __init__(self, config: MemoryConfig):
        super().__init__(config)
        self.memory_dir = config.storage_path / config.user_id
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化存储文件
        self._init_storage()
    
    def _init_storage(self):
        """初始化存储文件"""
        for mem_type in MemoryType:
            file_path = self._get_file_path(mem_type)
            if not file_path.exists():
                self._save_to_file(mem_type, [])
    
    def _get_file_path(self, memory_type: MemoryType) -> Path:
        """获取存储文件路径"""
        return self.memory_dir / f"{memory_type.value}.json"
    
    def _load_from_file(self, memory_type: MemoryType) -> List[Dict]:
        """从文件加载"""
        file_path = self._get_file_path(memory_type)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_to_file(self, memory_type: MemoryType, data: List[Dict]):
        """保存到文件"""
        file_path = self._get_file_path(memory_type)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def store(self, entry: MemoryEntry) -> bool:
        """存储记忆"""
        try:
            data = self._load_from_file(entry.memory_type)
            data.append(entry.to_dict())
            
            # 限制数量
            limit = (self.config.short_term_limit 
                     if entry.memory_type == MemoryType.SHORT_TERM 
                     else self.config.long_term_limit)
            if len(data) > limit:
                data = data[-limit:]
            
            self._save_to_file(entry.memory_type, data)
            return True
        except Exception as e:
            print(f"存储记忆失败: {e}")
            return False
    
    def retrieve(self, memory_type: MemoryType, limit: int = 10) -> List[MemoryEntry]:
        """检索记忆"""
        data = self._load_from_file(memory_type)
        entries = [MemoryEntry.from_dict(d) for d in data]
        
        # 按时间排序，返回最新的
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        return entries[:limit]
    
    def search(self, query: str, memory_type: Optional[MemoryType] = None,
               limit: int = 10) -> List[MemoryEntry]:
        """简单文本搜索"""
        results = []
        types_to_search = [memory_type] if memory_type else list(MemoryType)
        
        for mem_type in types_to_search:
            entries = self.retrieve(mem_type, limit=1000)
            for entry in entries:
                if query.lower() in entry.content.lower():
                    results.append(entry)
        
        # 按相关性排序（简单实现：包含查询词次数）
        results.sort(key=lambda x: x.content.lower().count(query.lower()), reverse=True)
        return results[:limit]
    
    def delete(self, entry_id: str) -> bool:
        """删除记忆"""
        for mem_type in MemoryType:
            data = self._load_from_file(mem_type)
            original_len = len(data)
            data = [d for d in data if d.get("id") != entry_id]
            if len(data) < original_len:
                self._save_to_file(mem_type, data)
                return True
        return False
    
    def clear(self, memory_type: Optional[MemoryType] = None):
        """清空记忆"""
        types_to_clear = [memory_type] if memory_type else list(MemoryType)
        for mem_type in types_to_clear:
            self._save_to_file(mem_type, [])


class SQLiteMemoryStore(BaseMemoryStore):
    """SQLite存储后端"""
    
    def __init__(self, config: MemoryConfig):
        super().__init__(config)
        self.db_path = config.storage_path / f"{config.user_id}.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    importance REAL DEFAULT 0.5,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp)
            """)
    
    def store(self, entry: MemoryEntry) -> bool:
        """存储记忆"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO memories 
                       (id, content, memory_type, timestamp, importance, metadata)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (entry.id, entry.content, entry.memory_type.value,
                     entry.timestamp, entry.importance, json.dumps(entry.metadata))
                )
                
                # 清理过期数据
                self._cleanup_old_memories(conn)
                
            return True
        except Exception as e:
            print(f"存储记忆失败: {e}")
            return False
    
    def _cleanup_old_memories(self, conn: sqlite3.Connection):
        """清理过期记忆"""
        # 清理短期记忆
        cutoff = (datetime.now() - timedelta(hours=self.config.short_term_ttl)).isoformat()
        conn.execute(
            "DELETE FROM memories WHERE memory_type = ? AND timestamp < ?",
            (MemoryType.SHORT_TERM.value, cutoff)
        )
        
        # 限制数量
        for mem_type in [MemoryType.SHORT_TERM, MemoryType.LONG_TERM]:
            limit = (self.config.short_term_limit if mem_type == MemoryType.SHORT_TERM 
                     else self.config.long_term_limit)
            conn.execute(
                """DELETE FROM memories WHERE id IN (
                    SELECT id FROM memories WHERE memory_type = ?
                    ORDER BY timestamp DESC LIMIT -1 OFFSET ?
                )""",
                (mem_type.value, limit)
            )
    
    def retrieve(self, memory_type: MemoryType, limit: int = 10) -> List[MemoryEntry]:
        """检索记忆"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT id, content, memory_type, timestamp, importance, metadata
                   FROM memories WHERE memory_type = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (memory_type.value, limit)
            )
            rows = cursor.fetchall()
            
        return [self._row_to_entry(row) for row in rows]
    
    def search(self, query: str, memory_type: Optional[MemoryType] = None,
               limit: int = 10) -> List[MemoryEntry]:
        """搜索记忆"""
        sql = """SELECT id, content, memory_type, timestamp, importance, metadata
                 FROM memories WHERE content LIKE ?"""
        params = [f"%{query}%"]
        
        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type.value)
        
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
        
        return [self._row_to_entry(row) for row in rows]
    
    def _row_to_entry(self, row: tuple) -> MemoryEntry:
        """数据库行转记忆条目"""
        return MemoryEntry(
            id=row[0],
            content=row[1],
            memory_type=MemoryType(row[2]),
            timestamp=row[3],
            importance=row[4],
            metadata=json.loads(row[5]) if row[5] else {}
        )
    
    def delete(self, entry_id: str) -> bool:
        """删除记忆"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (entry_id,))
            return cursor.rowcount > 0
    
    def clear(self, memory_type: Optional[MemoryType] = None):
        """清空记忆"""
        with sqlite3.connect(self.db_path) as conn:
            if memory_type:
                conn.execute("DELETE FROM memories WHERE memory_type = ?", 
                           (memory_type.value,))
            else:
                conn.execute("DELETE FROM memories")


class MemoryStore:
    """记忆存储工厂"""
    
    @staticmethod
    def create(config: MemoryConfig) -> BaseMemoryStore:
        """创建存储实例"""
        if config.backend == StorageBackend.FILE:
            return FileMemoryStore(config)
        elif config.backend == StorageBackend.SQLITE:
            return SQLiteMemoryStore(config)
        else:
            raise ValueError(f"不支持的存储后端: {config.backend}")


class AgentMemory:
    """
    Agent 记忆系统
    
    为 Agent 提供完整的记忆管理能力
    """
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self.store = MemoryStore.create(self.config)
        self._cache: Dict[str, Any] = {}  # 内存缓存
    
    # ========== 存储接口 ==========
    
    def store_short_term(self, content: str, importance: float = 0.5, 
                         metadata: Optional[Dict] = None) -> str:
        """存储短期记忆"""
        entry = MemoryEntry(
            content=content,
            memory_type=MemoryType.SHORT_TERM,
            importance=importance,
            metadata=metadata or {}
        )
        self.store.store(entry)
        
        # 自动晋升检查
        if self.config.auto_promote and importance >= self.config.importance_threshold:
            self._promote_to_long_term(entry)
        
        return entry.id
    
    def store_long_term(self, content: str, importance: float = 0.8,
                        metadata: Optional[Dict] = None) -> str:
        """存储长期记忆"""
        entry = MemoryEntry(
            content=content,
            memory_type=MemoryType.LONG_TERM,
            importance=importance,
            metadata=metadata or {}
        )
        self.store.store(entry)
        return entry.id
    
    def store_entity(self, name: str, entity_type: str, 
                     attributes: Dict[str, Any]) -> str:
        """存储实体记忆"""
        content = f"{name} ({entity_type}): {json.dumps(attributes, ensure_ascii=False)}"
        entry = MemoryEntry(
            content=content,
            memory_type=MemoryType.ENTITY,
            importance=0.9,
            metadata={"name": name, "type": entity_type, "attributes": attributes}
        )
        self.store.store(entry)
        return entry.id
    
    def store_episodic(self, event: str, context: Optional[Dict] = None) -> str:
        """存储情景记忆"""
        entry = MemoryEntry(
            content=event,
            memory_type=MemoryType.EPISODIC,
            importance=0.6,
            metadata={"context": context or {}, "date": datetime.now().strftime("%Y-%m-%d")}
        )
        self.store.store(entry)
        return entry.id
    
    # ========== 检索接口 ==========
    
    def get_short_term(self, limit: int = 10) -> List[MemoryEntry]:
        """获取短期记忆"""
        return self.store.retrieve(MemoryType.SHORT_TERM, limit)
    
    def get_long_term(self, limit: int = 10, 
                      min_importance: float = 0.0) -> List[MemoryEntry]:
        """获取长期记忆"""
        entries = self.store.retrieve(MemoryType.LONG_TERM, limit * 2)
        return [e for e in entries if e.importance >= min_importance][:limit]
    
    def get_entities(self, entity_type: Optional[str] = None) -> List[MemoryEntry]:
        """获取实体记忆"""
        entries = self.store.retrieve(MemoryType.ENTITY, limit=1000)
        if entity_type:
            entries = [e for e in entries 
                      if e.metadata.get("type") == entity_type]
        return entries
    
    def get_episodic(self, days: Optional[int] = None) -> List[MemoryEntry]:
        """获取情景记忆"""
        entries = self.store.retrieve(MemoryType.EPISODIC, limit=1000)
        
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            entries = [e for e in entries 
                      if datetime.fromisoformat(e.timestamp) > cutoff]
        
        return entries
    
    def search(self, query: str, memory_type: Optional[MemoryType] = None,
               limit: int = 10) -> List[MemoryEntry]:
        """搜索记忆"""
        return self.store.search(query, memory_type, limit)
    
    # ========== 上下文构建 ==========
    
    def build_context(self, query: Optional[str] = None, 
                      max_items: int = 5) -> str:
        """构建记忆上下文"""
        context_parts = []
        
        # 1. 短期记忆（最近上下文）
        short_term = self.get_short_term(limit=3)
        if short_term:
            context_parts.append("【最近对话】")
            for entry in short_term:
                context_parts.append(f"- {entry.content[:100]}")
        
        # 2. 相关长期记忆
        if query:
            long_term = self.search(query, MemoryType.LONG_TERM, limit=2)
            if long_term:
                context_parts.append("\n【相关知识】")
                for entry in long_term:
                    context_parts.append(f"- {entry.content[:100]}")
        
        # 3. 相关实体
        if query:
            entities = self.search(query, MemoryType.ENTITY, limit=2)
            if entities:
                context_parts.append("\n【相关实体】")
                for entry in entities:
                    context_parts.append(f"- {entry.content[:100]}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    # ========== 管理接口 ==========
    
    def _promote_to_long_term(self, entry: MemoryEntry):
        """将短期记忆晋升为长期记忆"""
        long_term_entry = MemoryEntry(
            content=entry.content,
            memory_type=MemoryType.LONG_TERM,
            importance=entry.importance,
            metadata={**entry.metadata, "promoted_from": entry.id}
        )
        self.store.store(long_term_entry)
        print(f"记忆已晋升为长期记忆: {entry.content[:50]}...")
    
    def delete(self, entry_id: str) -> bool:
        """删除记忆"""
        return self.store.delete(entry_id)
    
    def clear(self, memory_type: Optional[MemoryType] = None):
        """清空记忆"""
        self.store.clear(memory_type)
    
    def get_stats(self) -> Dict[str, int]:
        """获取记忆统计"""
        stats = {}
        for mem_type in MemoryType:
            entries = self.store.retrieve(mem_type, limit=10000)
            stats[mem_type.value] = len(entries)
        return stats
    
    def export(self) -> Dict[str, Any]:
        """导出所有记忆"""
        data = {}
        for mem_type in MemoryType:
            entries = self.store.retrieve(mem_type, limit=10000)
            data[mem_type.value] = [e.to_dict() for e in entries]
        return data
    
    def import_data(self, data: Dict[str, Any]):
        """导入记忆"""
        for mem_type_value, entries_data in data.items():
            mem_type = MemoryType(mem_type_value)
            for entry_data in entries_data:
                entry = MemoryEntry.from_dict(entry_data)
                entry.memory_type = mem_type
                self.store.store(entry)


# ========== 便捷函数 ==========

def create_memory(
    backend: str = "file",
    storage_path: Optional[Union[str, Path]] = None,
    user_id: str = "default",
    **kwargs
) -> AgentMemory:
    """
    便捷函数：创建记忆系统
    
    Args:
        backend: 存储后端 (file, sqlite)
        storage_path: 存储路径
        user_id: 用户ID
        **kwargs: 其他配置参数
        
    Returns:
        AgentMemory 实例
        
    Example:
        >>> memory = create_memory(backend="sqlite", user_id="user123")
        >>> memory.store_short_term("用户喜欢Python")
    """
    config = MemoryConfig(
        backend=StorageBackend(backend),
        user_id=user_id,
        **kwargs
    )
    
    if storage_path:
        config.storage_path = Path(storage_path)
    
    return AgentMemory(config)
