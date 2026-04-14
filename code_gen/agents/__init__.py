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

# Advanced Workflow (PraisonAI-inspired)
from .advanced_workflow import (
    AdvancedWorkflowExecutor,
    AdvancedTask,
    TaskContext,
    TaskType,
    ManagerAgent,
    WorkflowManager,
    Route,
    create_decision_task,
    create_loop_task,
    route
)

# Agent Handoffs (PraisonAI-inspired)
from .handoff import (
    HandoffManager,
    HandoffConfig,
    HandoffAgentMixin,
    create_handoff,
    handoff
)

# Memory System (PraisonAI-inspired)
from .memory import (
    AgentMemory,
    MemoryConfig,
    MemoryEntry,
    MemoryType,
    StorageBackend,
    create_memory
)

# Guardrails (PraisonAI-inspired)
from .guardrails import (
    Guardrails,
    GuardrailResult,
    BaseValidator,
    JSONValidator,
    CodeSyntaxValidator,
    SecurityValidator,
    LengthValidator,
    KeywordValidator,
    RegexValidator,
    QualityValidator,
    CustomValidator,
    GuardrailPresets,
    validate_json,
    validate_code,
    validate_safe
)

# Human-in-the-loop (PraisonAI-inspired)
from .human_in_loop import (
    HumanInTheLoop,
    HITLConfig,
    HITLRequest,
    HITLResponse,
    HITLMode,
    HITLResponseType,
    HITLHandler,
    ConsoleHITLHandler,
    AutoHITLHandler,
    create_hitl,
    create_disabled_hitl,
    create_manual_hitl
)

# Evaluator-Optimizer (PraisonAI-inspired)
from .evaluator_optimizer import (
    EvaluatorOptimizer,
    OptimizationResult,
    OptimizationIteration,
    EvaluationResult,
    OptimizationStatus,
    BaseGenerator,
    BaseEvaluator,
    LLMGenerator,
    LLMEvaluator,
    CodeEvaluator,
    optimize_solution,
    create_code_optimizer,
    create_content_optimizer
)

# Prompt Chaining (PraisonAI-inspired)
from .prompt_chaining import (
    PromptChain,
    ChainStep,
    FunctionStep,
    LLMStep,
    ConditionalStep,
    ParallelStep,
    ChainContext,
    ChainResult,
    StepResult,
    ChainStatus,
    ChainPresets,
    run_chain,
    create_step,
    create_llm_step,
    create_parallel_step
)

# Unified Agent (整合所有功能)
from .unified_agent import (
    UnifiedAgent,
    UnifiedAgentConfig,
    create_unified_agent
)

# Utilities (工具函数)
from .utils import (
    PerformanceMonitor,
    PerformanceMetrics,
    SimpleCache,
    RetryManager,
    RateLimiter,
    performance_monitor,
    cache,
    retry_manager,
    timing_decorator,
    async_batch_process,
    safe_json_loads,
    truncate_string,
    generate_id
)

# Context Window Management (上下文管理)
from .context_manager import (
    ContextWindow,
    ContextManager,
    ContextBudget,
    ContextSummary,
    ContextCompressor,
    CompressionLevel,
    MessageRole,
    Message,
    create_context_window,
    compact_context
)

# Git Integration (Git 集成)
from .git_integration import (
    GitIntegration,
    GitConfig,
    GitAutoCommitMode,
    GitOperationStatus,
    GitOperationResult,
    ChangeInfo,
    create_git_integration,
    quick_commit,
    get_repo_status
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
    # Advanced Workflow
    'AdvancedWorkflowExecutor',
    'AdvancedTask',
    'TaskContext',
    'TaskType',
    'ManagerAgent',
    'WorkflowManager',
    'Route',
    'create_decision_task',
    'create_loop_task',
    'route',
    # Agent Handoffs
    'HandoffManager',
    'HandoffConfig',
    'HandoffAgentMixin',
    'create_handoff',
    'handoff',
    # Memory System
    'AgentMemory',
    'MemoryConfig',
    'MemoryEntry',
    'MemoryType',
    'StorageBackend',
    'create_memory',
    # Guardrails
    'Guardrails',
    'GuardrailResult',
    'BaseValidator',
    'JSONValidator',
    'CodeSyntaxValidator',
    'SecurityValidator',
    'LengthValidator',
    'KeywordValidator',
    'RegexValidator',
    'QualityValidator',
    'CustomValidator',
    'GuardrailPresets',
    'validate_json',
    'validate_code',
    'validate_safe',
    # Human-in-the-loop
    'HumanInTheLoop',
    'HITLConfig',
    'HITLRequest',
    'HITLResponse',
    'HITLMode',
    'HITLResponseType',
    'HITLHandler',
    'ConsoleHITLHandler',
    'AutoHITLHandler',
    'create_hitl',
    'create_disabled_hitl',
    'create_manual_hitl',
    # Evaluator-Optimizer
    'EvaluatorOptimizer',
    'OptimizationResult',
    'OptimizationIteration',
    'EvaluationResult',
    'OptimizationStatus',
    'BaseGenerator',
    'BaseEvaluator',
    'LLMGenerator',
    'LLMEvaluator',
    'CodeEvaluator',
    'optimize_solution',
    'create_code_optimizer',
    'create_content_optimizer',
    # Prompt Chaining
    'PromptChain',
    'ChainStep',
    'FunctionStep',
    'LLMStep',
    'ConditionalStep',
    'ParallelStep',
    'ChainContext',
    'ChainResult',
    'StepResult',
    'ChainStatus',
    'ChainPresets',
    'run_chain',
    'create_step',
    'create_llm_step',
    'create_parallel_step',
    # Unified Agent
    'UnifiedAgent',
    'UnifiedAgentConfig',
    'create_unified_agent',
    # Utilities
    'PerformanceMonitor',
    'PerformanceMetrics',
    'SimpleCache',
    'RetryManager',
    'RateLimiter',
    'performance_monitor',
    'cache',
    'retry_manager',
    'timing_decorator',
    'async_batch_process',
    'safe_json_loads',
    'truncate_string',
    'generate_id',
    # Context Window Management
    'ContextWindow',
    'ContextManager',
    'ContextBudget',
    'ContextSummary',
    'ContextCompressor',
    'CompressionLevel',
    'MessageRole',
    'Message',
    'create_context_window',
    'compact_context',
    # Git Integration
    'GitIntegration',
    'GitConfig',
    'GitAutoCommitMode',
    'GitOperationStatus',
    'GitOperationResult',
    'ChangeInfo',
    'create_git_integration',
    'quick_commit',
    'get_repo_status',
]
