"""
Workflow definitions for multi-agent system
预定义的工作流，对应 cc-godmode 技能
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from .agent import Agent, AgentRole, AgentTemplates
from .task import Task
from .team import AgentTeam, ProcessType


@dataclass
class WorkflowStep:
    """工作流步骤"""
    name: str
    agent_role: AgentRole
    description: str
    expected_output: str


class Workflow:
    """
    工作流定义
    
    提供预定义的工作流模板，对应 cc-godmode 的各种场景
    """
    
    @staticmethod
    def new_feature(feature_name: str, model: str = "ollama/qwen2.5") -> AgentTeam:
        """
        新功能开发工作流
        
        流程：Researcher -> Architect -> Builder -> (Validator + Tester) -> Scribe
        """
        # 创建 Agents
        researcher = AgentTemplates.researcher(model)
        architect = AgentTemplates.architect(model)
        builder = AgentTemplates.builder(model)
        validator = AgentTemplates.validator(model)
        tester = AgentTemplates.tester(model)
        scribe = AgentTemplates.scribe(model)
        
        agents = [researcher, architect, builder, validator, tester, scribe]
        
        # 创建任务
        task1 = Task(
            name="技术研究",
            description=f"研究实现 {feature_name} 所需的技术方案",
            expected_output="技术研究报告，包含可行方案对比",
            agent=researcher
        )
        
        task2 = Task(
            name="架构设计",
            description=f"设计 {feature_name} 的系统架构",
            expected_output="架构设计文档，包含组件图和接口定义",
            agent=architect,
            depends_on=[task1]
        )
        
        task3 = Task(
            name="代码实现",
            description=f"实现 {feature_name} 的核心代码",
            expected_output="可运行的代码实现",
            agent=builder,
            depends_on=[task2]
        )
        
        task4 = Task(
            name="代码验证",
            description="验证代码质量和规范性",
            expected_output="代码审查报告",
            agent=validator,
            depends_on=[task3]
        )
        
        task5 = Task(
            name="功能测试",
            description="测试功能是否正常工作",
            expected_output="测试报告",
            agent=tester,
            depends_on=[task3]
        )
        
        task6 = Task(
            name="文档编写",
            description="编写功能文档",
            expected_output="README 更新和 API 文档",
            agent=scribe,
            depends_on=[task4, task5]  # 依赖验证和测试都完成
        )
        
        tasks = [task1, task2, task3, task4, task5, task6]
        
        return AgentTeam(
            name=f"New Feature: {feature_name}",
            agents=agents,
            tasks=tasks,
            process=ProcessType.HYBRID
        )
    
    @staticmethod
    def bug_fix(bug_description: str, model: str = "ollama/qwen2.5") -> AgentTeam:
        """
        Bug 修复工作流
        
        流程：Builder -> (Validator + Tester)
        """
        builder = AgentTemplates.builder(model)
        validator = AgentTemplates.validator(model)
        tester = AgentTemplates.tester(model)
        
        agents = [builder, validator, tester]
        
        task1 = Task(
            name="Bug 修复",
            description=f"修复问题: {bug_description}",
            expected_output="修复后的代码",
            agent=builder
        )
        
        task2 = Task(
            name="修复验证",
            description="验证修复是否解决原问题",
            expected_output="验证报告",
            agent=validator,
            depends_on=[task1]
        )
        
        task3 = Task(
            name="回归测试",
            description="确保修复没有引入新问题",
            expected_output="回归测试报告",
            agent=tester,
            depends_on=[task1]
        )
        
        tasks = [task1, task2, task3]
        
        return AgentTeam(
            name=f"Bug Fix: {bug_description[:30]}",
            agents=agents,
            tasks=tasks,
            process=ProcessType.HYBRID
        )
    
    @staticmethod
    def research(topic: str, model: str = "ollama/qwen2.5") -> AgentTeam:
        """
        研究工作流
        
        流程：Researcher -> Scribe
        """
        researcher = AgentTemplates.researcher(model)
        scribe = AgentTemplates.scribe(model)
        
        agents = [researcher, scribe]
        
        task1 = Task(
            name="主题研究",
            description=f"研究主题: {topic}",
            expected_output="研究报告",
            agent=researcher
        )
        
        task2 = Task(
            name="报告整理",
            description="整理研究结果为文档",
            expected_output="结构化的研究文档",
            agent=scribe,
            depends_on=[task1]
        )
        
        tasks = [task1, task2]
        
        return AgentTeam(
            name=f"Research: {topic}",
            agents=agents,
            tasks=tasks,
            process=ProcessType.SEQUENTIAL
        )
    
    @staticmethod
    def code_review(code_path: str, model: str = "ollama/qwen2.5") -> AgentTeam:
        """
        代码审查工作流
        
        流程：Validator -> Reviewer -> Scribe
        """
        validator = AgentTemplates.validator(model)
        reviewer = Agent(
            name="代码审查员",
            role=AgentRole.REVIEWER,
            goal="审查代码质量",
            model=model
        )
        scribe = AgentTemplates.scribe(model)
        
        agents = [validator, reviewer, scribe]
        
        task1 = Task(
            name="静态分析",
            description=f"对 {code_path} 进行静态分析",
            expected_output="静态分析报告",
            agent=validator
        )
        
        task2 = Task(
            name="代码审查",
            description="审查代码逻辑和设计",
            expected_output="代码审查意见",
            agent=reviewer,
            depends_on=[task1]
        )
        
        task3 = Task(
            name="审查报告",
            description="整理审查报告",
            expected_output="完整的代码审查报告",
            agent=scribe,
            depends_on=[task2]
        )
        
        tasks = [task1, task2, task3]
        
        return AgentTeam(
            name=f"Code Review: {code_path}",
            agents=agents,
            tasks=tasks,
            process=ProcessType.SEQUENTIAL
        )
    
    @staticmethod
    def custom(
        name: str,
        steps: List[WorkflowStep],
        model: str = "ollama/qwen2.5"
    ) -> AgentTeam:
        """
        自定义工作流
        
        Args:
            name: 工作流名称
            steps: 工作流步骤列表
            model: 使用的模型
        """
        # 创建所需的 Agents
        role_to_template = {
            AgentRole.RESEARCHER: AgentTemplates.researcher,
            AgentRole.ARCHITECT: AgentTemplates.architect,
            AgentRole.BUILDER: AgentTemplates.builder,
            AgentRole.VALIDATOR: AgentTemplates.validator,
            AgentRole.TESTER: AgentTemplates.tester,
            AgentRole.SCRIBE: AgentTemplates.scribe,
        }
        
        agents = []
        tasks = []
        last_task = None
        
        for i, step in enumerate(steps):
            # 获取或创建 Agent
            template_func = role_to_template.get(step.agent_role)
            if template_func:
                agent = template_func(model)
            else:
                agent = Agent(
                    name=f"Agent-{i}",
                    role=step.agent_role,
                    goal=f"执行 {step.name}",
                    model=model
                )
            
            agents.append(agent)
            
            # 创建任务
            task = Task(
                name=step.name,
                description=step.description,
                expected_output=step.expected_output,
                agent=agent,
                depends_on=[last_task] if last_task else []
            )
            
            tasks.append(task)
            last_task = task
        
        return AgentTeam(
            name=name,
            agents=agents,
            tasks=tasks,
            process=ProcessType.SEQUENTIAL
        )


# 快捷函数
def new_feature(feature_name: str, model: str = "ollama/qwen2.5") -> AgentTeam:
    """创建新功能开发工作流"""
    return Workflow.new_feature(feature_name, model)


def bug_fix(bug_description: str, model: str = "ollama/qwen2.5") -> AgentTeam:
    """创建 Bug 修复工作流"""
    return Workflow.bug_fix(bug_description, model)


def research(topic: str, model: str = "ollama/qwen2.5") -> AgentTeam:
    """创建工作流研究工作流"""
    return Workflow.research(topic, model)


def code_review(code_path: str, model: str = "ollama/qwen2.5") -> AgentTeam:
    """创建代码审查工作流"""
    return Workflow.code_review(code_path, model)
