"""SOP (Standard Operating Procedure) System

标准作业程序系统，用于定义和管理 AI Agent 的工作流程。
灵感来源于 MetaGPT 的 Code = SOP(Team) 理念。
"""

from .sop import SOP, SOPStep, SOPContext
from .registry import SOPRegistry
from .executor import SOPExecutor

__all__ = [
    "SOP",
    "SOPStep", 
    "SOPContext",
    "SOPRegistry",
    "SOPExecutor",
]
