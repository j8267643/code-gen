"""Code Indexer - 代码索引器

解析多种语言代码，提取符号并构建知识图谱
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Type
import logging

from .graph import (
    Node, Edge, NodeType, EdgeType, KnowledgeGraph, Language
)
from .parsers.base import BaseParser
from .parsers.typescript_parser import TypeScriptParser

logger = logging.getLogger(__name__)


class CodeIndexer:
    """代码索引器

    解析多种语言代码文件，提取类、函数、变量等符号，
    并构建知识图谱
    """

    # 文件扩展名到解析器的映射
    PARSERS: Dict[str, Type[BaseParser]] = {
        '.ts': TypeScriptParser,
        '.tsx': TypeScriptParser,
        '.js': TypeScriptParser,
        '.jsx': TypeScriptParser,
        '.mjs': TypeScriptParser,
    }

    def __init__(self, graph: Optional[KnowledgeGraph] = None):
        self.graph = graph or KnowledgeGraph()
        self._current_file: Optional[str] = None
        self._current_module: Optional[Node] = None
        self._node_stack: List[Node] = []

    def index_directory(self, directory: str | Path) -> Dict[str, Any]:
        """索引整个目录"""
        directory = Path(directory)

        if not directory.exists():
            raise ValueError(f"Directory not found: {directory}")

        # 查找所有支持的文件
        all_files = []
        for ext in ['*.py', '*.ts', '*.tsx', '*.js', '*.jsx', '*.mjs']:
            all_files.extend(directory.rglob(ext))

        logger.info(f"Found {len(all_files)} files in {directory}")

        # 按语言分组统计
        py_files = [f for f in all_files if f.suffix == '.py']
        ts_files = [f for f in all_files if f.suffix in ('.ts', '.tsx')]
        js_files = [f for f in all_files if f.suffix in ('.js', '.jsx', '.mjs')]

        logger.info(f"  Python: {len(py_files)}, TypeScript: {len(ts_files)}, JavaScript: {len(js_files)}")

        # 索引每个文件
        for file_path in all_files:
            try:
                self.index_file(file_path)
            except Exception as e:
                logger.warning(f"Failed to index {file_path}: {e}")

        logger.info(f"Indexing complete. Total nodes: {len(self.graph)}")

        return self.get_statistics()

    def index_file(self, file_path: str | Path) -> Optional[Node]:
        """索引单个文件"""
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None

        # 跳过某些文件
        if self._should_skip(file_path):
            return None

        self._current_file = str(file_path)

        # 根据文件类型选择解析方式
        if file_path.suffix == '.py':
            return self._index_python_file(file_path)
        elif file_path.suffix in self.PARSERS:
            return self._index_with_parser(file_path)
        else:
            logger.debug(f"Unsupported file type: {file_path.suffix}")
            return None

    def _index_python_file(self, file_path: Path) -> Optional[Node]:
        """索引 Python 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            # 解析 AST
            tree = ast.parse(source)

            # 创建文件节点
            file_node = self._create_file_node(file_path, source)

            # 创建模块节点
            module_name = self._get_module_name(file_path)
            module_node = self._create_module_node(module_name, file_node)
            self._current_module = module_node

            # 处理 AST 节点
            self._process_ast(tree, file_node, source)

            logger.debug(f"Indexed Python file {file_path}: {module_name}")

            return module_node

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return None

    def _index_with_parser(self, file_path: Path) -> Optional[Node]:
        """使用专用解析器索引文件"""
        parser_class = self.PARSERS.get(file_path.suffix)
        if not parser_class:
            return None

        try:
            parser = parser_class()
            result = parser.parse_file(file_path)

            if result.errors:
                for error in result.errors:
                    logger.warning(f"Parse error in {file_path}: {error}")

            # 创建文件节点
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            file_node = self._create_file_node(file_path, source)

            # 添加解析的节点和边
            for node in result.nodes:
                self.graph.add_node(node)

            for edge in result.edges:
                self.graph.add_edge(edge)

            logger.debug(f"Indexed {parser.language.value} file {file_path}: "
                        f"{len(result.nodes)} nodes, {len(result.edges)} edges")

            return file_node

        except Exception as e:
            logger.warning(f"Failed to parse {file_path} with {parser_class.__name__}: {e}")
            return None

    def _should_skip(self, file_path: Path) -> bool:
        """检查是否应该跳过该文件"""
        # 跳过测试文件
        if "test" in file_path.name.lower():
            return True

        # 跳过 __pycache__
        if "__pycache__" in str(file_path):
            return True

        # 跳过 .venv
        if ".venv" in str(file_path) or "venv" in str(file_path):
            return True

        # 跳过太大的文件 (>100KB)
        if file_path.stat().st_size > 100 * 1024:
            logger.debug(f"Skipping large file: {file_path}")
            return True

        return False

    def _create_file_node(self, file_path: Path, source: str) -> Node:
        """创建文件节点"""
        node = Node(
            name=file_path.name,
            node_type=NodeType.FILE,
            file_path=str(file_path),
            line_start=1,
            line_end=len(source.splitlines()),
            source_code=source[:1000] if len(source) > 1000 else source,  # 限制大小
            properties={
                "full_path": str(file_path.absolute()),
                "size": len(source),
            }
        )
        return self.graph.add_node(node)

    def _create_module_node(self, module_name: str, file_node: Node) -> Node:
        """创建模块节点"""
        node = Node(
            name=module_name,
            node_type=NodeType.MODULE,
            file_path=file_node.file_path,
            line_start=1,
            properties={
                "file_id": file_node.id,
            }
        )
        module_node = self.graph.add_node(node)

        # 添加 DEFINED_IN 边
        self._add_edge(module_node.id, file_node.id, EdgeType.DEFINED_IN)

        return module_node

    def _process_ast(self, tree: ast.AST, file_node: Node, source: str):
        """处理 AST"""
        for node in ast.iter_child_nodes(tree):
            self._process_node(node, file_node, source)

    def _process_node(self, node: ast.AST, file_node: Node, source: str):
        """递归处理 AST 节点"""
        if isinstance(node, ast.ClassDef):
            self._process_class(node, file_node, source)
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            self._process_function(node, file_node, source)
        elif isinstance(node, ast.Import):
            self._process_import(node, file_node)
        elif isinstance(node, ast.ImportFrom):
            self._process_import_from(node, file_node)

    def _process_class(self, node: ast.ClassDef, file_node: Node, source: str):
        """处理类定义"""
        # 获取类源代码
        class_source = self._get_node_source(node, source)

        # 创建类节点
        class_node = Node(
            name=node.name,
            node_type=NodeType.CLASS,
            file_path=file_node.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
            source_code=class_source,
            signature=self._get_class_signature(node),
            properties={
                "bases": [self._get_name(base) for base in node.bases],
                "decorators": [self._get_name(d) for d in node.decorator_list],
            }
        )
        class_node = self.graph.add_node(class_node)

        # 添加 DEFINED_IN 边
        parent_node = self._current_module or file_node
        self._add_edge(class_node.id, parent_node.id, EdgeType.DEFINED_IN)

        # 处理继承关系
        for base in node.bases:
            base_name = self._get_name(base)
            # 先创建一个占位节点
            base_node = self.graph.find_node_by_name(base_name, NodeType.CLASS)
            if not base_node:
                base_node = Node(
                    name=base_name,
                    node_type=NodeType.CLASS,
                    properties={"is_external": True}
                )
                base_node = self.graph.add_node(base_node)
            self._add_edge(class_node.id, base_node.id, EdgeType.EXTENDS)

        # 处理类内部
        self._node_stack.append(class_node)
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._process_method(item, file_node, class_node, source)
            else:
                self._process_node(item, file_node, source)
        self._node_stack.pop()

    def _process_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef,
                         file_node: Node, source: str):
        """处理函数定义"""
        func_source = self._get_node_source(node, source)

        # 创建函数节点
        func_node = Node(
            name=node.name,
            node_type=NodeType.FUNCTION,
            file_path=file_node.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
            source_code=func_source,
            signature=self._get_function_signature(node),
            properties={
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "decorators": [self._get_name(d) for d in node.decorator_list],
            }
        )
        func_node = self.graph.add_node(func_node)

        # 添加 DEFINED_IN 边
        parent_node = self._current_module or file_node
        self._add_edge(func_node.id, parent_node.id, EdgeType.DEFINED_IN)

        # 处理参数
        self._process_parameters(node, func_node)

        # 分析函数调用
        self._analyze_calls(node, func_node)

    def _process_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef,
                       file_node: Node, class_node: Node, source: str):
        """处理方法定义"""
        func_source = self._get_node_source(node, source)

        # 创建方法节点
        method_node = Node(
            name=f"{class_node.name}.{node.name}",
            node_type=NodeType.METHOD,
            file_path=file_node.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
            source_code=func_source,
            signature=self._get_function_signature(node),
            properties={
                "class_name": class_node.name,
                "method_name": node.name,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "is_constructor": node.name == "__init__",
            }
        )
        method_node = self.graph.add_node(method_node)

        # 添加 DEFINED_IN 边
        self._add_edge(method_node.id, class_node.id, EdgeType.DEFINED_IN)

        # 处理参数
        self._process_parameters(node, method_node)

        # 分析方法调用
        self._analyze_calls(node, method_node)

    def _process_parameters(self, node: ast.FunctionDef | ast.AsyncFunctionDef,
                           func_node: Node):
        """处理函数参数"""
        args = node.args

        # 位置参数
        for arg in args.args:
            param_node = Node(
                name=arg.arg,
                node_type=NodeType.PARAMETER,
                file_path=func_node.file_path,
                line_start=arg.lineno if hasattr(arg, 'lineno') else func_node.line_start,
                properties={
                    "type": "positional",
                    "annotation": self._get_annotation(arg.annotation),
                }
            )
            param_node = self.graph.add_node(param_node)
            self._add_edge(func_node.id, param_node.id, EdgeType.HAS_PARAMETER)

        # 默认参数
        for arg in args.kwonlyargs:
            param_node = Node(
                name=arg.arg,
                node_type=NodeType.PARAMETER,
                file_path=func_node.file_path,
                properties={
                    "type": "keyword_only",
                    "annotation": self._get_annotation(arg.annotation),
                }
            )
            param_node = self.graph.add_node(param_node)
            self._add_edge(func_node.id, param_node.id, EdgeType.HAS_PARAMETER)

    def _analyze_calls(self, node: ast.FunctionDef | ast.AsyncFunctionDef,
                      func_node: Node):
        """分析函数调用"""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # 获取被调用的函数名
                func_name = self._get_call_name(child.func)
                if func_name:
                    # 查找或创建被调用函数节点
                    called_node = self.graph.find_node_by_name(func_name)
                    if not called_node:
                        called_node = Node(
                            name=func_name,
                            node_type=NodeType.FUNCTION,
                            properties={"is_external": True}
                        )
                        called_node = self.graph.add_node(called_node)

                    # 添加调用边
                    self._add_edge(func_node.id, called_node.id, EdgeType.CALLS)

    def _process_import(self, node: ast.Import, file_node: Node):
        """处理导入"""
        for alias in node.names:
            import_node = Node(
                name=alias.asname or alias.name,
                node_type=NodeType.IMPORT,
                file_path=file_node.file_path,
                line_start=node.lineno,
                properties={
                    "module": alias.name,
                    "alias": alias.asname,
                }
            )
            import_node = self.graph.add_node(import_node)
            self._add_edge(self._current_module.id, import_node.id, EdgeType.IMPORTS)

    def _process_import_from(self, node: ast.ImportFrom, file_node: Node):
        """处理 from import"""
        module = node.module or ""

        for alias in node.names:
            name = alias.asname or alias.name
            import_node = Node(
                name=name,
                node_type=NodeType.IMPORT,
                file_path=file_node.file_path,
                line_start=node.lineno,
                properties={
                    "module": module,
                    "name": alias.name,
                    "alias": alias.asname,
                    "is_from_import": True,
                }
            )
            import_node = self.graph.add_node(import_node)
            self._add_edge(self._current_module.id, import_node.id, EdgeType.IMPORTS)

    def _add_edge(self, source_id: str, target_id: str, edge_type: EdgeType,
                 properties: Optional[Dict[str, Any]] = None):
        """添加边"""
        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            properties=properties or {}
        )
        return self.graph.add_edge(edge)

    def _get_node_source(self, node: ast.AST, source: str) -> str:
        """获取节点的源代码"""
        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
            lines = source.splitlines()
            start = node.lineno - 1
            end = node.end_lineno if node.end_lineno else start + 1
            return '\n'.join(lines[start:end])
        return ""

    def _get_function_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """获取函数签名"""
        args = []

        # 普通参数
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._get_annotation(arg.annotation)}"
            args.append(arg_str)

        # 默认参数
        defaults_start = len(args) - len(node.args.defaults)
        for i, default in enumerate(node.args.defaults):
            args[defaults_start + i] += f" = {self._get_name(default)}"

        # 返回类型
        returns = ""
        if node.returns:
            returns = f" -> {self._get_annotation(node.returns)}"

        async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        return f"{async_prefix}def {node.name}({', '.join(args)}){returns}"

    def _get_class_signature(self, node: ast.ClassDef) -> str:
        """获取类签名"""
        bases = [self._get_name(base) for base in node.bases]
        base_str = f"({', '.join(bases)})" if bases else ""
        return f"class {node.name}{base_str}"

    def _get_annotation(self, node: Optional[ast.AST]) -> str:
        """获取类型注解"""
        if node is None:
            return ""
        return self._get_name(node)

    def _get_name(self, node: ast.AST) -> str:
        """从 AST 节点获取名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[{self._get_name(node.slice)}]"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Str):  # Python < 3.8
            return repr(node.s)
        elif isinstance(node, ast.Num):  # Python < 3.8
            return repr(node.n)
        elif isinstance(node, ast.List):
            return "[...]"
        elif isinstance(node, ast.Dict):
            return "{...}"
        elif isinstance(node, ast.Tuple):
            return "(...)"
        else:
            return ""

    def _get_call_name(self, node: ast.expr) -> str:
        """获取调用表达式的名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""

    def _get_module_name(self, file_path: Path) -> str:
        """从文件路径获取模块名"""
        # 尝试找到项目根目录
        parts = list(file_path.parts)

        # 移除文件扩展名
        if parts[-1].endswith('.py'):
            parts[-1] = parts[-1][:-3]

        # 如果文件名是 __init__，使用目录名
        if parts[-1] == '__init__':
            parts.pop()

        # 尝试找到 code_gen 或项目根目录
        for i, part in enumerate(parts):
            if part in ('code_gen', 'src'):
                return '.'.join(parts[i:])

        # 默认使用文件名
        return parts[-1] if parts else "unknown"

    def get_statistics(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        return {
            "total_files_indexed": len(self.graph._nodes_by_file),
            "total_nodes": len(self.graph),
            "total_edges": len(self.graph.edges),
            "node_types": {
                t.value: len(nodes)
                for t, nodes in self.graph._nodes_by_type.items()
            },
        }
