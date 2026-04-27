"""
Features module - Advanced features from Hermes/Trae
"""
from .lakeview import Lakeview, LakeviewSummarizer
from .sequential_thinking import (
    SequentialThinkingEngine, ThoughtType, Thought, ThinkingSession
)
from .trajectory import TrajectoryRecorder
from .task_done import TaskDoneManager
from .agent_features import AgentFeatures
from .advanced_edit import AdvancedEditTool
from .parallel_tools import ParallelToolExecutor
from .resilient_executor import ResilientExecutor
from .resilient_tools import ResilientToolCaller
from .error_recovery import ResilientClient, ErrorClassifier, RecoveryStrategy
from .file_changes import FileChangeManager
from .dream import DreamMemorySystem as DreamCoder

__all__ = [
    'Lakeview',
    'LakeviewSummarizer',
    'SequentialThinkingEngine',
    'ThoughtType',
    'Thought',
    'ThinkingSession',
    'TrajectoryRecorder',
    'TaskDoneManager',
    'AgentFeatures',
    'AdvancedEditTool',
    'ParallelToolExecutor',
    'ResilientExecutor',
    'ResilientToolCaller',
    'ResilientClient',
    'ErrorClassifier',
    'RecoveryStrategy',
    'FileChangeManager',
    'DreamCoder',
]
