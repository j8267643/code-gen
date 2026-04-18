"""Base Parser - 解析器基类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..graph import Node, Edge, Language


@dataclass
class ParseResult:
    """解析结果"""
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def merge(self, other: ParseResult) -> ParseResult:
        """合并另一个解析结果"""
        self.nodes.extend(other.nodes)
        self.edges.extend(other.edges)
        self.errors.extend(other.errors)
        return self


class BaseParser(ABC):
    """代码解析器基类"""

    # 支持的文件扩展名
    extensions: List[str] = []

    # 编程语言
    language: Language = Language.UNKNOWN

    @abstractmethod
    def parse(self, source: str, file_path: Optional[str] = None) -> ParseResult:
        """解析源代码

        Args:
            source: 源代码字符串
            file_path: 文件路径（用于错误报告）

        Returns:
            解析结果，包含节点和边
        """
        pass

    def parse_file(self, file_path: str | Path) -> ParseResult:
        """解析文件"""
        file_path = Path(file_path)

        if not file_path.exists():
            return ParseResult(errors=[f"File not found: {file_path}"])

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            return self.parse(source, str(file_path))
        except Exception as e:
            return ParseResult(errors=[f"Failed to parse {file_path}: {e}"])

    @classmethod
    def supports_file(cls, file_path: str | Path) -> bool:
        """检查是否支持该文件"""
        file_path = Path(file_path)
        return file_path.suffix in cls.extensions

    def _create_node(
        self,
        name: str,
        node_type: Any,
        file_path: Optional[str] = None,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        source_code: Optional[str] = None,
        signature: Optional[str] = None,
        **properties
    ) -> Node:
        """创建节点的辅助方法"""
        from ..graph import NodeType

        return Node(
            name=name,
            node_type=node_type if isinstance(node_type, NodeType) else NodeType.FILE,
            language=self.language,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            source_code=source_code,
            signature=signature,
            properties=properties
        )

    def _create_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: Any,
        **properties
    ) -> Edge:
        """创建边的辅助方法"""
        from ..graph import EdgeType

        return Edge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type if isinstance(edge_type, EdgeType) else EdgeType.USES,
            properties=properties
        )
