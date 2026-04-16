"""Action Node System

动作节点系统，用于标准化 AI Agent 的动作定义。
灵感来源于 MetaGPT 的 ActionNode。
"""

from .node import ActionNode, NodeOutput, ActionTemplates, FieldDefinition
from .parser import OutputParser, JSONParser, MarkdownParser
from .registry import ActionRegistry
from .executor import ActionExecutor

__all__ = [
    "ActionNode",
    "NodeOutput",
    "ActionTemplates",
    "FieldDefinition",
    "OutputParser",
    "JSONParser",
    "MarkdownParser",
    "ActionRegistry",
    "ActionExecutor",
]
