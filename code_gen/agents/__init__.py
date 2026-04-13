"""
Multi-Agent System for Code Gen
基于 PraisonAI 架构设计，支持多 Agent 协作
"""
from .agent import Agent, AgentRole
from .task import Task, TaskStatus
from .team import AgentTeam, ProcessType
from .workflow import Workflow, WorkflowStep
from .executor import AgentExecutor

# Self-reflection support (PraisonAI-inspired)
from .reflection import (
    SelfReflection,
    ReflectionConfig,
    ReflectionResult,
    ReflectionStatus,
    ReflectAgentMixin
)
from .reflect_executor import (
    ReflectiveAgentExecutor,
    ReflectionPresets
)
from .enhanced_reflect_executor import (
    EnhancedReflectiveExecutor,
    ReflectiveEnhancedExecutor
)

__all__ = [
    'Agent',
    'AgentRole',
    'Task',
    'TaskStatus',
    'AgentTeam',
    'ProcessType',
    'Workflow',
    'WorkflowStep',
    'AgentExecutor',
    # Reflection
    'SelfReflection',
    'ReflectionConfig',
    'ReflectionResult',
    'ReflectionStatus',
    'ReflectAgentMixin',
    'ReflectiveAgentExecutor',
    'ReflectionPresets',
    'EnhancedReflectiveExecutor',
    'ReflectiveEnhancedExecutor',
]
