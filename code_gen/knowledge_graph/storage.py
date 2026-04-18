"""Storage - 持久化存储模块

支持多种存储后端：
- JSON: 简单的文件存储，适合小型项目
- SQLite: 关系数据库存储，支持复杂查询
- Memory: 内存存储（默认）
"""

from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterator
import logging

from .graph import Node, Edge, NodeType, EdgeType, KnowledgeGraph

logger = logging.getLogger(__name__)


class GraphStorage(ABC):
    """图存储抽象基类"""

    @abstractmethod
    def save(self, graph: KnowledgeGraph) -> bool:
        """保存图谱"""
        pass

    @abstractmethod
    def load(self) -> Optional[KnowledgeGraph]:
        """加载图谱"""
        pass

    @abstractmethod
    def exists(self) -> bool:
        """检查存储是否存在"""
        pass

    @abstractmethod
    def clear(self) -> bool:
        """清空存储"""
        pass


class JSONStorage(GraphStorage):
    """JSON 文件存储

    简单的文件存储，适合小型项目
    """

    def __init__(self, filepath: str | Path = "knowledge_graph.json"):
        self.filepath = Path(filepath)

    def save(self, graph: KnowledgeGraph) -> bool:
        """保存图谱到 JSON"""
        try:
            data = {
                "metadata": {
                    "version": "1.0",
                    "created_at": datetime.now().isoformat(),
                    "node_count": len(graph.nodes),
                    "edge_count": len(graph.edges),
                },
                "nodes": [
                    self._node_to_dict(node)
                    for node in graph.nodes.values()
                ],
                "edges": [
                    self._edge_to_dict(edge)
                    for edge in graph.edges.values()
                ],
            }

            # 确保目录存在
            self.filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Graph saved to {self.filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save graph: {e}")
            return False

    def load(self) -> Optional[KnowledgeGraph]:
        """从 JSON 加载图谱"""
        if not self.exists():
            logger.warning(f"Graph file not found: {self.filepath}")
            return None

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            graph = KnowledgeGraph()

            # 加载节点
            for node_data in data.get("nodes", []):
                node = self._dict_to_node(node_data)
                graph.nodes[node.id] = node

                # 更新索引
                if node.node_type not in graph._nodes_by_type:
                    graph._nodes_by_type[node.node_type] = set()
                graph._nodes_by_type[node.node_type].add(node.id)

                if node.file_path:
                    if node.file_path not in graph._nodes_by_file:
                        graph._nodes_by_file[node.file_path] = set()
                    graph._nodes_by_file[node.file_path].add(node.id)

            # 加载边
            for edge_data in data.get("edges", []):
                edge = self._dict_to_edge(edge_data)
                graph.edges[edge.id] = edge

                # 更新索引
                if edge.source_id not in graph._edges_by_source:
                    graph._edges_by_source[edge.source_id] = set()
                graph._edges_by_source[edge.source_id].add(edge.id)

                if edge.target_id not in graph._edges_by_target:
                    graph._edges_by_target[edge.target_id] = set()
                graph._edges_by_target[edge.target_id].add(edge.id)

                if edge.edge_type not in graph._edges_by_type:
                    graph._edges_by_type[edge.edge_type] = set()
                graph._edges_by_type[edge.edge_type].add(edge.id)

            logger.info(f"Graph loaded from {self.filepath}: "
                       f"{len(graph.nodes)} nodes, {len(graph.edges)} edges")
            return graph

        except Exception as e:
            logger.error(f"Failed to load graph: {e}")
            return None

    def exists(self) -> bool:
        """检查文件是否存在"""
        return self.filepath.exists()

    def clear(self) -> bool:
        """删除存储文件"""
        try:
            if self.exists():
                self.filepath.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to clear storage: {e}")
            return False

    def _node_to_dict(self, node: Node) -> Dict[str, Any]:
        """节点转字典"""
        return {
            "id": node.id,
            "name": node.name,
            "node_type": node.node_type.value,
            "file_path": node.file_path,
            "line_start": node.line_start,
            "line_end": node.line_end,
            "source_code": node.source_code,
            "signature": node.signature,
            "properties": node.properties,
            "created_at": node.created_at.isoformat() if isinstance(node.created_at, datetime) else node.created_at,
            "updated_at": node.updated_at.isoformat() if isinstance(node.updated_at, datetime) else node.updated_at,
        }

    def _edge_to_dict(self, edge: Edge) -> Dict[str, Any]:
        """边转字典"""
        return {
            "id": edge.id,
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "edge_type": edge.edge_type.value,
            "properties": edge.properties,
            "created_at": edge.created_at.isoformat() if isinstance(edge.created_at, datetime) else edge.created_at,
        }

    def _dict_to_node(self, data: Dict[str, Any]) -> Node:
        """字典转节点"""
        return Node(
            id=data["id"],
            name=data["name"],
            node_type=NodeType(data["node_type"]),
            file_path=data.get("file_path"),
            line_start=data.get("line_start"),
            line_end=data.get("line_end"),
            source_code=data.get("source_code"),
            signature=data.get("signature"),
            properties=data.get("properties", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else datetime.now(),
        )

    def _dict_to_edge(self, data: Dict[str, Any]) -> Edge:
        """字典转边"""
        return Edge(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            edge_type=EdgeType(data["edge_type"]),
            properties=data.get("properties", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else datetime.now(),
        )


class SQLiteStorage(GraphStorage):
    """SQLite 数据库存储

    支持复杂查询和增量更新
    """

    def __init__(self, db_path: str | Path = "knowledge_graph.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 创建节点表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    file_path TEXT,
                    line_start INTEGER,
                    line_end INTEGER,
                    source_code TEXT,
                    signature TEXT,
                    properties TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            # 创建边表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    properties TEXT,
                    created_at TEXT,
                    FOREIGN KEY (source_id) REFERENCES nodes(id),
                    FOREIGN KEY (target_id) REFERENCES nodes(id)
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_file ON nodes(file_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type)")

            # 创建元数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            conn.commit()

    def save(self, graph: KnowledgeGraph) -> bool:
        """保存图谱到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 清空现有数据
                cursor.execute("DELETE FROM edges")
                cursor.execute("DELETE FROM nodes")

                # 插入节点
                for node in graph.nodes.values():
                    cursor.execute("""
                        INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        node.id,
                        node.name,
                        node.node_type.value,
                        node.file_path,
                        node.line_start,
                        node.line_end,
                        node.source_code,
                        node.signature,
                        json.dumps(node.properties),
                        node.created_at.isoformat() if isinstance(node.created_at, datetime) else str(node.created_at),
                        node.updated_at.isoformat() if isinstance(node.updated_at, datetime) else str(node.updated_at),
                    ))

                # 插入边
                for edge in graph.edges.values():
                    cursor.execute("""
                        INSERT INTO edges VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        edge.id,
                        edge.source_id,
                        edge.target_id,
                        edge.edge_type.value,
                        json.dumps(edge.properties),
                        edge.created_at.isoformat() if isinstance(edge.created_at, datetime) else str(edge.created_at),
                    ))

                # 更新元数据
                cursor.execute("""
                    INSERT OR REPLACE INTO metadata VALUES (?, ?)
                """, ("version", "1.0"))
                cursor.execute("""
                    INSERT OR REPLACE INTO metadata VALUES (?, ?)
                """, ("updated_at", datetime.now().isoformat()))
                cursor.execute("""
                    INSERT OR REPLACE INTO metadata VALUES (?, ?)
                """, ("node_count", str(len(graph.nodes))))
                cursor.execute("""
                    INSERT OR REPLACE INTO metadata VALUES (?, ?)
                """, ("edge_count", str(len(graph.edges))))

                conn.commit()

            logger.info(f"Graph saved to {self.db_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save graph: {e}")
            return False

    def load(self) -> Optional[KnowledgeGraph]:
        """从数据库加载图谱"""
        if not self.exists():
            return None

        try:
            graph = KnowledgeGraph()

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # 加载节点
                cursor.execute("SELECT * FROM nodes")
                for row in cursor.fetchall():
                    node = self._row_to_node(row)
                    graph.nodes[node.id] = node

                    # 更新索引
                    if node.node_type not in graph._nodes_by_type:
                        graph._nodes_by_type[node.node_type] = set()
                    graph._nodes_by_type[node.node_type].add(node.id)

                    if node.file_path:
                        if node.file_path not in graph._nodes_by_file:
                            graph._nodes_by_file[node.file_path] = set()
                        graph._nodes_by_file[node.file_path].add(node.id)

                # 加载边
                cursor.execute("SELECT * FROM edges")
                for row in cursor.fetchall():
                    edge = self._row_to_edge(row)
                    graph.edges[edge.id] = edge

                    # 更新索引
                    if edge.source_id not in graph._edges_by_source:
                        graph._edges_by_source[edge.source_id] = set()
                    graph._edges_by_source[edge.source_id].add(edge.id)

                    if edge.target_id not in graph._edges_by_target:
                        graph._edges_by_target[edge.target_id] = set()
                    graph._edges_by_target[edge.target_id].add(edge.id)

                    if edge.edge_type not in graph._edges_by_type:
                        graph._edges_by_type[edge.edge_type] = set()
                    graph._edges_by_type[edge.edge_type].add(edge.id)

            logger.info(f"Graph loaded from {self.db_path}: "
                       f"{len(graph.nodes)} nodes, {len(graph.edges)} edges")
            return graph

        except Exception as e:
            logger.error(f"Failed to load graph: {e}")
            return None

    def exists(self) -> bool:
        """检查数据库是否存在"""
        return self.db_path.exists()

    def clear(self) -> bool:
        """清空数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM edges")
                cursor.execute("DELETE FROM nodes")
                cursor.execute("DELETE FROM metadata")
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to clear storage: {e}")
            return False

    def query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """执行 SQL 查询"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def _row_to_node(self, row: sqlite3.Row) -> Node:
        """数据库行转节点"""
        return Node(
            id=row["id"],
            name=row["name"],
            node_type=NodeType(row["node_type"]),
            file_path=row["file_path"],
            line_start=row["line_start"],
            line_end=row["line_end"],
            source_code=row["source_code"],
            signature=row["signature"],
            properties=json.loads(row["properties"]) if row["properties"] else {},
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
        )

    def _row_to_edge(self, row: sqlite3.Row) -> Edge:
        """数据库行转边"""
        return Edge(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            edge_type=EdgeType(row["edge_type"]),
            properties=json.loads(row["properties"]) if row["properties"] else {},
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        )


class StorageManager:
    """存储管理器

    统一管理多种存储后端
    """

    def __init__(self, storage: Optional[GraphStorage] = None):
        self.storage = storage or JSONStorage()

    def save(self, graph: KnowledgeGraph) -> bool:
        """保存图谱"""
        return self.storage.save(graph)

    def load(self) -> Optional[KnowledgeGraph]:
        """加载图谱"""
        return self.storage.load()

    def load_or_create(self) -> KnowledgeGraph:
        """加载或创建新图谱"""
        graph = self.load()
        if graph is None:
            graph = KnowledgeGraph()
        return graph

    def exists(self) -> bool:
        """检查存储是否存在"""
        return self.storage.exists()

    def clear(self) -> bool:
        """清空存储"""
        return self.storage.clear()

    @classmethod
    def create_json(cls, filepath: str | Path = "knowledge_graph.json") -> StorageManager:
        """创建 JSON 存储管理器"""
        return cls(JSONStorage(filepath))

    @classmethod
    def create_sqlite(cls, db_path: str | Path = "knowledge_graph.db") -> StorageManager:
        """创建 SQLite 存储管理器"""
        return cls(SQLiteStorage(db_path))


# 便捷函数
def save_graph(graph: KnowledgeGraph, filepath: str | Path = "knowledge_graph.json") -> bool:
    """保存图谱到文件"""
    storage = JSONStorage(filepath)
    return storage.save(graph)


def load_graph(filepath: str | Path = "knowledge_graph.json") -> Optional[KnowledgeGraph]:
    """从文件加载图谱"""
    storage = JSONStorage(filepath)
    return storage.load()
