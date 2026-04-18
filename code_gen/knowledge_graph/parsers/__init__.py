"""Parsers - 多语言代码解析器

支持多种编程语言的代码解析
"""

from .base import BaseParser, ParseResult
from .typescript_parser import TypeScriptParser

__all__ = [
    "BaseParser",
    "ParseResult",
    "TypeScriptParser",
]
