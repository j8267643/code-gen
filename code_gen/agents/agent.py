"""
Agent definition for multi-agent system
"""
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import uuid


class AgentRole(str, Enum):
    """预定义的 Agent 角色"""
    RESEARCHER = "researcher"      # 研究员 - 收集信息
    ARCHITECT = "architect"        # 架构师 - 系统设计
    BUILDER = "builder"            # 构建者 - 代码实现
    VALIDATOR = "validator"        # 验证者 - 代码检查
    TESTER = "tester"              # 测试者 - 测试执行
    SCRIBE = "scribe"              # 文档员 - 文档编写
    REVIEWER = "reviewer"          # 审查员 - 代码审查
    ORCHESTRATOR = "orchestrator"  # 编排者 - 工作流管理
    ASSISTANT = "assistant"        # 助手 - 通用助手
    CUSTOM = "custom"              # 自定义


@dataclass
class Agent:
    """
    Agent 定义
    
    Attributes:
        name: Agent 名称
        role: Agent 角色
        goal: 工作目标
        backstory: 背景故事（用于构建个性）
        instructions: 具体指令
        model: 使用的 AI 模型
        tools: 可用工具列表
        memory: 是否启用记忆
        allow_delegation: 是否允许委托任务
    """
    name: str
    role: AgentRole
    goal: str
    backstory: str = ""
    instructions: str = ""
    model: str = "ollama/qwen2.5"
    tools: List[str] = field(default_factory=list)
    memory: bool = True
    allow_delegation: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后的处理"""
        if not self.backstory:
            self.backstory = self._generate_backstory()
        if not self.instructions:
            self.instructions = self._generate_instructions()
    
    def _generate_backstory(self) -> str:
        """根据角色生成背景故事"""
        backstories = {
            AgentRole.RESEARCHER: "你是一个专业的研究分析师，擅长收集和整理信息。你具有敏锐的洞察力，能够快速理解复杂的技术概念。",
            AgentRole.ARCHITECT: "你是一个经验丰富的系统架构师，擅长设计可扩展、可维护的系统架构。你注重代码质量和设计模式。",
            AgentRole.BUILDER: "你是一个高效的开发者，擅长将设计转化为高质量的代码。你熟悉多种编程语言和框架。",
            AgentRole.VALIDATOR: "你是一个严格的代码审查员，专注于代码质量、安全性和最佳实践。",
            AgentRole.TESTER: "你是一个全面的测试专家，擅长编写测试用例和执行各种测试。",
            AgentRole.SCRIBE: "你是一个技术文档专家，擅长编写清晰、准确的技术文档。",
            AgentRole.REVIEWER: "你是一个细致的代码审查员，专注于发现潜在问题和改进建议。",
            AgentRole.ORCHESTRATOR: "你是一个高效的项目协调员，擅长管理和协调多个 Agent 的工作。",
        }
        return backstories.get(self.role, "你是一个专业的 AI 助手。")
    
    def _generate_instructions(self) -> str:
        """根据角色生成指令"""
        instructions = {
            AgentRole.RESEARCHER: """你的任务是收集和整理信息。
- 使用搜索工具查找相关资料
- 总结关键信息点
- 提供信息来源
- 输出结构化的研究报告""",
            AgentRole.ARCHITECT: """你的任务是设计系统架构。
- 分析需求和约束
- 设计系统组件和接口
- 考虑可扩展性和可维护性
- 输出架构设计文档""",
            AgentRole.BUILDER: """你的任务是实现代码。
- 遵循架构设计
- 编写清晰、可维护的代码
- 添加必要的注释
- 确保代码符合最佳实践""",
            AgentRole.VALIDATOR: """你的任务是验证代码质量。
- 检查代码风格和规范
- 运行静态分析工具
- 检查安全漏洞
- 提供改进建议""",
            AgentRole.TESTER: """你的任务是执行测试。
- 编写测试用例
- 执行单元测试和集成测试
- 检查测试覆盖率
- 报告测试结果""",
            AgentRole.SCRIBE: """你的任务是编写文档。
- 编写 API 文档
- 更新 README
- 编写使用指南
- 维护变更日志""",
            AgentRole.REVIEWER: """你的任务是审查代码。
- 检查代码逻辑
- 发现潜在问题
- 提供改进建议
- 确保代码符合标准""",
            AgentRole.ORCHESTRATOR: """你的任务是协调工作流。
- 分配任务给合适的 Agent
- 监控任务进度
- 处理依赖关系
- 汇总最终结果""",
        }
        return instructions.get(self.role, "完成分配给你的任务。")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "goal": self.goal,
            "backstory": self.backstory,
            "instructions": self.instructions,
            "model": self.model,
            "tools": self.tools,
            "memory": self.memory,
            "allow_delegation": self.allow_delegation,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Agent":
        """从字典创建"""
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data["name"],
            role=AgentRole(data["role"]),
            goal=data["goal"],
            backstory=data.get("backstory", ""),
            instructions=data.get("instructions", ""),
            model=data.get("model", "ollama/qwen2.5"),
            tools=data.get("tools", []),
            memory=data.get("memory", True),
            allow_delegation=data.get("allow_delegation", True),
            metadata=data.get("metadata", {})
        )
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        prompt = f"""# {self.name}

## 角色
{self.role.value}

## 目标
{self.goal}

## 背景
{self.backstory}

## 指令
{self.instructions}

## 工具
你可以使用以下工具：{', '.join(self.tools) if self.tools else '无特定工具'}

## 注意事项
- 专注于你的专业领域
- 如果任务超出你的能力范围，可以委托给其他 Agent
- 保持输出清晰、结构化
- 使用中文回复
"""
        return prompt


# 预定义的 Agent 模板
class AgentTemplates:
    """Agent 模板工厂"""
    
    @staticmethod
    def researcher(model: str = "ollama/qwen2.5") -> Agent:
        """创建研究员 Agent"""
        return Agent(
            name="研究员",
            role=AgentRole.RESEARCHER,
            goal="收集和整理技术信息",
            model=model,
            tools=["web_search", "file_read"]
        )
    
    @staticmethod
    def architect(model: str = "ollama/qwen2.5") -> Agent:
        """创建架构师 Agent"""
        return Agent(
            name="架构师",
            role=AgentRole.ARCHITECT,
            goal="设计系统架构",
            model=model,
            tools=["file_read", "file_write"]
        )
    
    @staticmethod
    def builder(model: str = "ollama/qwen2.5") -> Agent:
        """创建构建者 Agent"""
        return Agent(
            name="开发者",
            role=AgentRole.BUILDER,
            goal="实现代码功能",
            model=model,
            tools=["file_read", "file_write", "shell"]
        )
    
    @staticmethod
    def validator(model: str = "ollama/qwen2.5") -> Agent:
        """创建验证者 Agent"""
        return Agent(
            name="验证员",
            role=AgentRole.VALIDATOR,
            goal="验证代码质量",
            model=model,
            tools=["file_read", "shell"]
        )
    
    @staticmethod
    def tester(model: str = "ollama/qwen2.5") -> Agent:
        """创建测试者 Agent"""
        return Agent(
            name="测试员",
            role=AgentRole.TESTER,
            goal="执行测试并报告结果",
            model=model,
            tools=["file_read", "shell"]
        )
    
    @staticmethod
    def scribe(model: str = "ollama/qwen2.5") -> Agent:
        """创建文档员 Agent"""
        return Agent(
            name="文档员",
            role=AgentRole.SCRIBE,
            goal="编写技术文档",
            model=model,
            tools=["file_read", "file_write"]
        )
    
    @staticmethod
    def orchestrator(model: str = "ollama/qwen2.5") -> Agent:
        """创建编排者 Agent"""
        return Agent(
            name="编排者",
            role=AgentRole.ORCHESTRATOR,
            goal="协调多 Agent 工作流",
            model=model,
            allow_delegation=True
        )
