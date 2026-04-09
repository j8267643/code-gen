"""
Protocol schemas for Claude Code
Based on controlSchemas.ts and coreSchemas.ts from TypeScript project
"""
from typing import Optional, Literal
from dataclasses import dataclass, field
from enum import Enum


class ControlRequestType(str, Enum):
    """Control request types"""
    INITIALIZE = "initialize"
    INTERRUPT = "interrupt"
    CAN_USE_TOOL = "can_use_tool"
    SET_PERMISSION_MODE = "set_permission_mode"
    SET_MODEL = "set_model"
    GET_CONTEXT_USAGE = "get_context_usage"
    RELOAD_PLUGINS = "reload_plugins"
    ELICITATION = "elicitation"
    KEEP_ALIVE = "keep_alive"


class ControlResponseType(str, Enum):
    """Control response types"""
    CONTROL_RESPONSE = "control_response"
    SYSTEM_POST_TURN_SUMMARY = "system.post_turn_summary"
    STREAMLINED_TEXT = "streamlined_text"
    STREAMLINED_TOOL_USE_SUMMARY = "streamlined_tool_use_summary"


@dataclass
class ControlRequest:
    """Control request"""
    type: ControlRequestType
    id: str
    payload: Optional[dict] = None


@dataclass
class ControlResponse:
    """Control response"""
    type: ControlResponseType
    id: str
    success: bool
    payload: Optional[dict] = None


@dataclass
class SDKMessage:
    """SDK message schema"""
    type: str
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: str
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ToolUse:
    """Tool use schema"""
    type: str = "tool_use"
    id: str = ""
    name: str = ""
    input: dict = None
    
    def __post_init__(self):
        if self.input is None:
            self.input = {}


@dataclass
class ToolResult:
    """Tool result schema"""
    type: str = "tool_result"
    id: str = ""
    content: str = ""
    success: bool = True
    error: Optional[str] = None


# Core schemas
SDK_MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "id": {"type": "string"},
        "role": {"type": "string", "enum": ["user", "assistant", "system"]},
        "content": {"type": "string"},
        "timestamp": {"type": "string"},
        "metadata": {"type": "object"}
    },
    "required": ["type", "id", "role", "content", "timestamp"]
}

TOOL_USE_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "id": {"type": "string"},
        "name": {"type": "string"},
        "input": {"type": "object"}
    },
    "required": ["type", "id", "name", "input"]
}

TOOL_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "id": {"type": "string"},
        "content": {"type": "string"},
        "success": {"type": "boolean"},
        "error": {"type": "string"}
    },
    "required": ["type", "id", "content", "success"]
}
