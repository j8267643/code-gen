"""Graph Model - 知识图谱模型"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Iterator


class Language(Enum):
    """编程语言"""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    GO = "go"
    JAVA = "java"
    RUST = "rust"
    UNKNOWN = "unknown"


class NodeType(Enum):
    """节点类型"""
    # 文件系统
    FILE = "file"                    # 文件
    FOLDER = "folder"                # 文件夹

    # 通用代码结构
    MODULE = "module"                # 模块/命名空间
    CLASS = "class"                  # 类
    INTERFACE = "interface"          # 接口 (TS/Java)
    FUNCTION = "function"            # 函数
    METHOD = "method"                # 方法
    VARIABLE = "variable"            # 变量
    CONSTANT = "constant"            # 常量
    PARAMETER = "parameter"          # 参数
    PROPERTY = "property"            # 属性 (TS/JS)
    ENUM = "enum"                    # 枚举
    TYPE_ALIAS = "type_alias"        # 类型别名 (TS)

    # 导入
    IMPORT = "import"                # 导入
    EXPORT = "export"                # 导出

    # API
    ROUTE = "route"                  # 路由
    HANDLER = "handler"              # 处理器
    ENDPOINT = "endpoint"            # API 端点

    # 文档
    DOC = "doc"                      # 文档
    COMMENT = "comment"              # 注释


class EdgeType(Enum):
    """边类型"""
    # 包含关系
    CONTAINS = "contains"            # 包含
    DEFINED_IN = "defined_in"        # 定义在

    # 继承和实现
    EXTENDS = "extends"              # 继承
    IMPLEMENTS = "implements"        # 实现
    OVERRIDES = "overrides"          # 覆盖

    # 调用关系
    CALLS = "calls"                  # 调用
    CALLED_BY = "called_by"          # 被调用

    # 导入关系
    IMPORTS = "imports"              # 导入
    IMPORTED_BY = "imported_by"      # 被导入

    # 使用关系
    USES = "uses"                    # 使用
    USED_BY = "used_by"              # 被使用

    # 读写关系
    READS = "reads"                  # 读取
    WRITES = "writes"                # 写入

    # 参数关系
    HAS_PARAMETER = "has_parameter"  # 有参数
    RETURNS = "returns"              # 返回


@dataclass
class Node:
    """图节点"""
    # 基本信息
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""                   # 节点名称
    node_type: NodeType = NodeType.FILE
    language: Language = Language.UNKNOWN  # 编程语言

    # 位置信息
    file_path: Optional[str] = None  # 文件路径
    line_start: Optional[int] = None # 起始行
    line_end: Optional[int] = None   # 结束行
    column_start: Optional[int] = None  # 起始列
    column_end: Optional[int] = None    # 结束列

    # 代码内容
    source_code: Optional[str] = None  # 源代码
    signature: Optional[str] = None    # 签名
    documentation: Optional[str] = None  # 文档注释

    # 额外属性
    properties: Dict[str, Any] = field(default_factory=dict)

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.id == other.id

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "signature": self.signature,
            "properties": self.properties,
        }


@dataclass
class Edge:
    """图边"""
    # 基本信息
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_id: str = ""              # 源节点ID
    target_id: str = ""              # 目标节点ID
    edge_type: EdgeType = EdgeType.USES

    # 额外属性
    properties: Dict[str, Any] = field(default_factory=dict)

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return False
        return self.id == other.id

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "properties": self.properties,
        }


class KnowledgeGraph:
    """知识图谱

    存储代码的图结构，支持查询和分析
    """

    def __init__(self):
        self.nodes: Dict[str, Node] = {}           # 节点存储
        self.edges: Dict[str, Edge] = {}           # 边存储

        # 索引
        self._nodes_by_type: Dict[NodeType, Set[str]] = {}
        self._nodes_by_file: Dict[str, Set[str]] = {}
        self._edges_by_source: Dict[str, Set[str]] = {}
        self._edges_by_target: Dict[str, Set[str]] = {}
        self._edges_by_type: Dict[EdgeType, Set[str]] = {}

    def add_node(self, node: Node) -> Node:
        """添加节点"""
        self.nodes[node.id] = node

        # 更新索引
        if node.node_type not in self._nodes_by_type:
            self._nodes_by_type[node.node_type] = set()
        self._nodes_by_type[node.node_type].add(node.id)

        if node.file_path:
            if node.file_path not in self._nodes_by_file:
                self._nodes_by_file[node.file_path] = set()
            self._nodes_by_file[node.file_path].add(node.id)

        return node

    def add_edge(self, edge: Edge) -> Edge:
        """添加边"""
        self.edges[edge.id] = edge

        # 更新索引
        if edge.source_id not in self._edges_by_source:
            self._edges_by_source[edge.source_id] = set()
        self._edges_by_source[edge.source_id].add(edge.id)

        if edge.target_id not in self._edges_by_target:
            self._edges_by_target[edge.target_id] = set()
        self._edges_by_target[edge.target_id].add(edge.id)

        if edge.edge_type not in self._edges_by_type:
            self._edges_by_type[edge.edge_type] = set()
        self._edges_by_type[edge.edge_type].add(edge.id)

        return edge

    def get_node(self, node_id: str) -> Optional[Node]:
        """获取节点"""
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        """获取边"""
        return self.edges.get(edge_id)

    def get_nodes_by_type(self, node_type: NodeType) -> List[Node]:
        """按类型获取节点"""
        node_ids = self._nodes_by_type.get(node_type, set())
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def get_nodes_by_file(self, file_path: str) -> List[Node]:
        """按文件获取节点"""
        node_ids = self._nodes_by_file.get(file_path, set())
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def get_outgoing_edges(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[Edge]:
        """获取节点的出边"""
        edge_ids = self._edges_by_source.get(node_id, set())
        edges = [self.edges[eid] for eid in edge_ids if eid in self.edges]

        if edge_type:
            edges = [e for e in edges if e.edge_type == edge_type]

        return edges

    def get_incoming_edges(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[Edge]:
        """获取节点的入边"""
        edge_ids = self._edges_by_target.get(node_id, set())
        edges = [self.edges[eid] for eid in edge_ids if eid in self.edges]

        if edge_type:
            edges = [e for e in edges if e.edge_type == edge_type]

        return edges

    def get_neighbors(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[Node]:
        """获取邻居节点"""
        edges = self.get_outgoing_edges(node_id, edge_type)
        neighbor_ids = [e.target_id for e in edges]
        return [self.nodes[nid] for nid in neighbor_ids if nid in self.nodes]

    def find_node_by_name(self, name: str, node_type: Optional[NodeType] = None) -> Optional[Node]:
        """按名称查找节点"""
        for node in self.nodes.values():
            if node.name == name:
                if node_type is None or node.node_type == node_type:
                    return node
        return None

    def find_nodes_by_pattern(self, pattern: str) -> List[Node]:
        """按模式查找节点（模糊匹配）"""
        import re
        regex = re.compile(pattern, re.IGNORECASE)
        results = []
        for node in self.nodes.values():
            if regex.search(node.name):
                results.append(node)
        return results

    def get_call_graph(self, function_name: str) -> Dict[str, Any]:
        """获取函数的调用图"""
        function = self.find_node_by_name(function_name, NodeType.FUNCTION)
        if not function:
            return {}

        # 获取调用的函数
        calls_edges = self.get_outgoing_edges(function.id, EdgeType.CALLS)
        called_functions = [self.nodes[e.target_id] for e in calls_edges if e.target_id in self.nodes]

        # 获取被哪些函数调用
        called_by_edges = self.get_incoming_edges(function.id, EdgeType.CALLS)
        callers = [self.nodes[e.source_id] for e in called_by_edges if e.source_id in self.nodes]

        return {
            "function": function.to_dict(),
            "calls": [n.to_dict() for n in called_functions],
            "called_by": [n.to_dict() for n in callers],
        }

    def get_class_hierarchy(self, class_name: str) -> Dict[str, Any]:
        """获取类的继承层次"""
        class_node = self.find_node_by_name(class_name, NodeType.CLASS)
        if not class_node:
            return {}

        # 获取父类
        extends_edges = self.get_outgoing_edges(class_node.id, EdgeType.EXTENDS)
        parents = [self.nodes[e.target_id] for e in extends_edges if e.target_id in self.nodes]

        # 获取子类
        extended_by_edges = self.get_incoming_edges(class_node.id, EdgeType.EXTENDS)
        children = [self.nodes[e.source_id] for e in extended_by_edges if e.source_id in self.nodes]

        return {
            "class": class_node.to_dict(),
            "parents": [n.to_dict() for n in parents],
            "children": [n.to_dict() for n in children],
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges.values()],
            "stats": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "node_types": {t.value: len(ids) for t, ids in self._nodes_by_type.items()},
                "edge_types": {t.value: len(ids) for t, ids in self._edges_by_type.items()},
            }
        }

    def clear(self):
        """清空图谱"""
        self.nodes.clear()
        self.edges.clear()
        self._nodes_by_type.clear()
        self._nodes_by_file.clear()
        self._edges_by_source.clear()
        self._edges_by_target.clear()
        self._edges_by_type.clear()

    def __len__(self):
        return len(self.nodes)

    def __iter__(self) -> Iterator[Node]:
        return iter(self.nodes.values())
