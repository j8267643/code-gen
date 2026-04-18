"""TypeScript Parser - TypeScript/JavaScript 解析器

使用正则表达式和简单解析（轻量级方案）
实际生产环境建议使用 tree-sitter
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Any, Tuple
import logging

from .base import BaseParser, ParseResult
from ..graph import Node, Edge, NodeType, EdgeType, Language

logger = logging.getLogger(__name__)


class TypeScriptParser(BaseParser):
    """TypeScript/JavaScript 解析器"""

    extensions = ['.ts', '.tsx', '.js', '.jsx', '.mjs']
    language = Language.TYPESCRIPT

    def __init__(self):
        # 预编译正则表达式
        self.patterns = {
            # 导入语句
            'import': re.compile(
                r'^\s*import\s+(?:(\{[^}]*\})|(\*\s+as\s+\w+)|(\w+))\s+from\s+[\'"]([^\'"]+)[\'"]',
                re.MULTILINE
            ),
            # 导出语句
            'export': re.compile(
                r'^\s*export\s+(?:default\s+)?(?:const|let|var|function|class|interface|type|enum)?\s*(\w+)',
                re.MULTILINE
            ),
            # 接口定义
            'interface': re.compile(
                r'^\s*(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+([^{]+))?\s*\{',
                re.MULTILINE
            ),
            # 类型别名
            'type_alias': re.compile(
                r'^\s*(?:export\s+)?type\s+(\w+)\s*=',
                re.MULTILINE
            ),
            # 类定义
            'class': re.compile(
                r'^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?',
                re.MULTILINE
            ),
            # 枚举定义
            'enum': re.compile(
                r'^\s*(?:export\s+)?(?:const\s+)?enum\s+(\w+)',
                re.MULTILINE
            ),
            # 函数定义
            'function': re.compile(
                r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(',
                re.MULTILINE
            ),
            # 箭头函数/变量函数
            'arrow_function': re.compile(
                r'^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*[=:]\s*(?:async\s+)?(?:\([^)]*\)|\w+)\s*=>',
                re.MULTILINE
            ),
            # 方法定义
            'method': re.compile(
                r'^\s+(?:async\s+)?(?:private\s+|protected\s+|public\s+|static\s+)?(?!constructor)(\w+)\s*\([^)]*\)\s*[:{]',
                re.MULTILINE
            ),
            # 构造函数
            'constructor': re.compile(
                r'^\s+(?:private\s+|protected\s+|public\s+)?constructor\s*\(',
                re.MULTILINE
            ),
            # 属性定义
            'property': re.compile(
                r'^\s+(?:private\s+|protected\s+|public\s+|static\s+|readonly\s+)?(\w+)\s*[:=]',
                re.MULTILINE
            ),
            # 注释
            'doc_comment': re.compile(
                r'/\*\*[\s\S]*?\*/',
                re.MULTILINE
            ),
        }

    def parse(self, source: str, file_path: Optional[str] = None) -> ParseResult:
        """解析 TypeScript 源代码"""
        result = ParseResult()
        lines = source.split('\n')

        # 解析导入
        imports = self._parse_imports(source, file_path)
        result.nodes.extend(imports)

        # 解析导出
        exports = self._parse_exports(source, file_path)
        result.nodes.extend(exports)

        # 解析接口
        interfaces = self._parse_interfaces(source, file_path)
        result.nodes.extend(interfaces)

        # 解析类型别名
        type_aliases = self._parse_type_aliases(source, file_path)
        result.nodes.extend(type_aliases)

        # 解析类
        classes = self._parse_classes(source, file_path)
        result.nodes.extend(classes)

        # 解析枚举
        enums = self._parse_enums(source, file_path)
        result.nodes.extend(enums)

        # 解析函数
        functions = self._parse_functions(source, file_path)
        result.nodes.extend(functions)

        return result

    def _parse_imports(self, source: str, file_path: Optional[str]) -> List[Node]:
        """解析导入语句"""
        nodes = []

        for match in self.patterns['import'].finditer(source):
            named_imports = match.group(1)  # { foo, bar }
            namespace_import = match.group(2)  # * as name
            default_import = match.group(3)  # default import
            module_path = match.group(4)  # module path

            # 计算行号
            line_num = source[:match.start()].count('\n') + 1

            # 创建导入节点
            if default_import:
                node = self._create_node(
                    name=default_import,
                    node_type=NodeType.IMPORT,
                    file_path=file_path,
                    line_start=line_num,
                    properties={
                        'module_path': module_path,
                        'import_type': 'default',
                    }
                )
                nodes.append(node)

            if named_imports:
                # 解析命名导入
                imports = [s.strip() for s in named_imports.strip('{}').split(',')]
                for imp in imports:
                    # 处理别名：foo as bar
                    if ' as ' in imp:
                        original, alias = imp.split(' as ')
                        name = alias.strip()
                        original_name = original.strip()
                    else:
                        name = imp.strip()
                        original_name = name

                    if name:
                        node = self._create_node(
                            name=name,
                            node_type=NodeType.IMPORT,
                            file_path=file_path,
                            line_start=line_num,
                            properties={
                                'module_path': module_path,
                                'import_type': 'named',
                                'original_name': original_name,
                            }
                        )
                        nodes.append(node)

            if namespace_import:
                name = namespace_import.replace('* as', '').strip()
                node = self._create_node(
                    name=name,
                    node_type=NodeType.IMPORT,
                    file_path=file_path,
                    line_start=line_num,
                    properties={
                        'module_path': module_path,
                        'import_type': 'namespace',
                    }
                )
                nodes.append(node)

        return nodes

    def _parse_exports(self, source: str, file_path: Optional[str]) -> List[Node]:
        """解析导出语句"""
        nodes = []

        for match in self.patterns['export'].finditer(source):
            name = match.group(1)
            if name:
                line_num = source[:match.start()].count('\n') + 1
                node = self._create_node(
                    name=name,
                    node_type=NodeType.EXPORT,
                    file_path=file_path,
                    line_start=line_num,
                )
                nodes.append(node)

        return nodes

    def _parse_interfaces(self, source: str, file_path: Optional[str]) -> List[Node]:
        """解析接口定义"""
        nodes = []

        for match in self.patterns['interface'].finditer(source):
            name = match.group(1)
            extends = match.group(2)

            line_num = source[:match.start()].count('\n') + 1

            # 获取接口体
            body_start = match.end()
            body = self._extract_body(source, body_start)

            node = self._create_node(
                name=name,
                node_type=NodeType.INTERFACE,
                file_path=file_path,
                line_start=line_num,
                line_end=line_num + body.count('\n'),
                source_code=f"interface {name} {{...}}",
                signature=f"interface {name}",
                properties={
                    'extends': [e.strip() for e in extends.split(',')] if extends else [],
                }
            )
            nodes.append(node)

        return nodes

    def _parse_type_aliases(self, source: str, file_path: Optional[str]) -> List[Node]:
        """解析类型别名"""
        nodes = []

        for match in self.patterns['type_alias'].finditer(source):
            name = match.group(1)
            line_num = source[:match.start()].count('\n') + 1

            node = self._create_node(
                name=name,
                node_type=NodeType.TYPE_ALIAS,
                file_path=file_path,
                line_start=line_num,
                signature=f"type {name} = ...",
            )
            nodes.append(node)

        return nodes

    def _parse_classes(self, source: str, file_path: Optional[str]) -> List[Node]:
        """解析类定义"""
        nodes = []

        for match in self.patterns['class'].finditer(source):
            name = match.group(1)
            extends = match.group(2)
            implements = match.group(3)

            line_num = source[:match.start()].count('\n') + 1

            # 获取类体
            body_start = match.end()
            body = self._extract_body(source, body_start)

            # 提取方法和属性
            methods = self._extract_methods(body, name, file_path, line_num)
            properties = self._extract_properties(body, name, file_path, line_num)

            node = self._create_node(
                name=name,
                node_type=NodeType.CLASS,
                file_path=file_path,
                line_start=line_num,
                line_end=line_num + body.count('\n'),
                source_code=f"class {name} {{...}}",
                signature=f"class {name}",
                properties={
                    'extends': extends,
                    'implements': [i.strip() for i in implements.split(',')] if implements else [],
                    'method_count': len(methods),
                    'property_count': len(properties),
                }
            )
            nodes.append(node)
            nodes.extend(methods)
            nodes.extend(properties)

        return nodes

    def _parse_enums(self, source: str, file_path: Optional[str]) -> List[Node]:
        """解析枚举定义"""
        nodes = []

        for match in self.patterns['enum'].finditer(source):
            name = match.group(1)
            line_num = source[:match.start()].count('\n') + 1

            node = self._create_node(
                name=name,
                node_type=NodeType.ENUM,
                file_path=file_path,
                line_start=line_num,
                signature=f"enum {name}",
            )
            nodes.append(node)

        return nodes

    def _parse_functions(self, source: str, file_path: Optional[str]) -> List[Node]:
        """解析函数定义"""
        nodes = []

        # 普通函数
        for match in self.patterns['function'].finditer(source):
            name = match.group(1)
            line_num = source[:match.start()].count('\n') + 1

            # 获取函数签名
            sig_end = source.find('{', match.end())
            if sig_end == -1:
                sig_end = source.find('=>', match.end())
            if sig_end == -1:
                sig_end = len(source)

            signature = source[match.start():sig_end].strip()

            node = self._create_node(
                name=name,
                node_type=NodeType.FUNCTION,
                file_path=file_path,
                line_start=line_num,
                signature=signature,
            )
            nodes.append(node)

        # 箭头函数
        for match in self.patterns['arrow_function'].finditer(source):
            name = match.group(1)
            line_num = source[:match.start()].count('\n') + 1

            node = self._create_node(
                name=name,
                node_type=NodeType.FUNCTION,
                file_path=file_path,
                line_start=line_num,
                signature=f"const {name} = ...",
                properties={'is_arrow_function': True},
            )
            nodes.append(node)

        return nodes

    def _extract_methods(self, class_body: str, class_name: str, file_path: Optional[str], base_line: int) -> List[Node]:
        """从类体中提取方法"""
        methods = []

        for match in self.patterns['method'].finditer(class_body):
            name = match.group(1)
            line_num = base_line + class_body[:match.start()].count('\n')

            node = self._create_node(
                name=f"{class_name}.{name}",
                node_type=NodeType.METHOD,
                file_path=file_path,
                line_start=line_num,
                properties={'class_name': class_name, 'method_name': name},
            )
            methods.append(node)

        return methods

    def _extract_properties(self, class_body: str, class_name: str, file_path: Optional[str], base_line: int) -> List[Node]:
        """从类体中提取属性"""
        properties = []
        seen = set()

        for match in self.patterns['property'].finditer(class_body):
            name = match.group(1)

            # 跳过重复和关键字
            if name in seen or name in ('if', 'else', 'for', 'while', 'switch', 'case', 'return'):
                continue
            seen.add(name)

            line_num = base_line + class_body[:match.start()].count('\n')

            node = self._create_node(
                name=f"{class_name}.{name}",
                node_type=NodeType.PROPERTY,
                file_path=file_path,
                line_start=line_num,
                properties={'class_name': class_name, 'property_name': name},
            )
            properties.append(node)

        return properties

    def _extract_body(self, source: str, start: int) -> str:
        """提取代码块体（处理嵌套大括号）"""
        brace_count = 0
        i = start

        while i < len(source):
            char = source[i]

            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return source[start:i+1]
            elif char == '"' or char == "'" or char == '`':
                # 跳过字符串
                quote = char
                i += 1
                while i < len(source) and source[i] != quote:
                    if source[i] == '\\':
                        i += 1
                    i += 1

            i += 1

        return source[start:]
