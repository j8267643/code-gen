"""
Dynamic Workflow - Agent 自主规划执行步骤

Agent 根据目标自主决定：
1. 需要哪些步骤
2. 使用哪些工具
3. 如何协作
"""
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import asyncio

from .agent import Agent, AgentRole
from .task import Task, TaskStatus
from .team import AgentTeam, ProcessType, TeamResult
from .executor import AgentExecutor


class PlanningStrategy(Enum):
    """规划策略"""
    SEQUENTIAL = "sequential"      # 顺序规划
    PARALLEL = "parallel"          # 并行规划
    ADAPTIVE = "adaptive"          # 自适应规划


@dataclass
class ExecutionPlan:
    """执行计划"""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: str = ""
    estimated_time: int = 0
    required_agents: List[str] = field(default_factory=list)


@dataclass
class DynamicWorkflowConfig:
    """动态工作流配置"""
    name: str
    description: str = ""
    goal: str = ""
    input: str = ""
    framework: str = "code_gen"
    strategy: str = "adaptive"
    max_iterations: int = 10
    
    # 可用的 Agents
    agents: Dict[str, Dict] = field(default_factory=dict)
    
    # 可用的工具
    tools: List[str] = field(default_factory=list)
    
    # 约束条件
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    # 回调
    callbacks: Dict[str, str] = field(default_factory=dict)


class DynamicWorkflow:
    """
    动态工作流
    
    Agent 自主规划执行步骤，而不是预定义
    """
    
    def __init__(
        self,
        config: DynamicWorkflowConfig,
        work_dir: Path,
        executor: AgentExecutor
    ):
        self.config = config
        self.work_dir = work_dir
        self.executor = executor
        self.plan: Optional[ExecutionPlan] = None
        self.execution_history: List[Dict] = field(default_factory=list)
        self.team: Optional[AgentTeam] = None
    
    async def run(self) -> TeamResult:
        """
        运行动态工作流
        
        流程：
        1. 规划阶段：Agent 分析目标并制定执行计划
        2. 执行阶段：按照计划执行各个步骤
        3. 评估阶段：评估结果并决定是否需要调整
        """
        print(f"\n{'='*60}")
        print(f"🎯 启动动态工作流: {self.config.name}")
        print(f"{'='*60}")
        print(f"目标: {self.config.goal}")
        print(f"策略: {self.config.strategy}")
        print(f"\n")
        
        # 阶段 1: 规划
        print("📋 阶段 1: 制定执行计划...")
        self.plan = await self._create_plan()
        
        if not self.plan or not self.plan.steps:
            return TeamResult(
                success=False,
                tasks_completed=0,
                tasks_failed=1,
                tasks_skipped=0,
                total_time=0,
                errors=["无法创建执行计划"]
            )
        
        print(f"✅ 计划制定完成")
        print(f"   步骤数: {len(self.plan.steps)}")
        print(f"   预计时间: {self.plan.estimated_time} 分钟")
        print(f"   推理: {self.plan.reasoning[:100]}...")
        print()
        
        # 显示计划
        self._display_plan()
        
        # 阶段 2: 执行
        print("\n🚀 阶段 2: 执行计划...")
        result = await self._execute_plan()
        
        # 阶段 3: 总结
        print("\n📊 阶段 3: 执行总结...")
        self._display_summary(result)
        
        return result
    
    async def _create_plan(self) -> ExecutionPlan:
        """
        创建执行计划
        
        使用 Orchestrator Agent 分析目标并制定计划
        """
        # 创建规划 Agent
        planner = Agent(
            name="规划师",
            role=AgentRole.ORCHESTRATOR,
            goal="制定最优执行计划",
            instructions="""你是一个任务规划专家。

请分析给定的目标，制定详细的执行计划。

你需要：
1. 分析目标需要哪些步骤
2. 为每个步骤分配合适的 Agent 角色
3. 确定步骤之间的依赖关系
4. 估算执行时间

可用 Agent 角色：
- researcher: 研究员，收集和分析信息
- architect: 架构师，系统设计
- builder: 开发者，代码实现
- validator: 验证者，代码检查
- tester: 测试者，功能测试
- scribe: 文档员，文档编写

请以 JSON 格式返回计划：
{
    "reasoning": "规划思路...",
    "estimated_time": 30,
    "steps": [
        {
            "id": "step_1",
            "name": "步骤名称",
            "description": "步骤描述",
            "agent_role": "researcher",
            "estimated_minutes": 10,
            "depends_on": []
        }
    ]
}""",
            model="ollama/qwen2.5"
        )
        
        # 构建规划提示
        agents_info = "\n".join([
            f"- {aid}: {adata.get('role', 'unknown')} - {adata.get('goal', '')}"
            for aid, adata in self.config.agents.items()
        ])
        
        tools_info = "\n".join([f"- {tool}" for tool in self.config.tools]) if self.config.tools else "无"
        
        prompt = f"""请为以下目标制定执行计划：

目标: {self.config.goal}
输入: {self.config.input}
描述: {self.config.description}

可用 Agents:
{agents_info}

可用工具:
{tools_info}

约束条件:
- 最大迭代次数: {self.config.max_iterations}
- 策略: {self.config.strategy}

请制定一个详细的执行计划。"""

        # 调用 AI 制定计划
        messages = [
            {"role": "system", "content": planner.instructions},
            {"role": "user", "content": prompt}
        ]
        
        # 使用模拟响应（实际应调用 AI）
        # response = await self.executor._call_ai(messages)
        
        # 模拟规划结果
        return self._generate_mock_plan()
    
    def _generate_mock_plan(self) -> ExecutionPlan:
        """生成模拟执行计划（用于测试）"""
        goal_lower = self.config.goal.lower()
        
        if "feature" in goal_lower or "功能" in goal_lower:
            return ExecutionPlan(
                reasoning="新功能开发需要研究、设计、实现、验证和文档编写",
                estimated_time=60,
                steps=[
                    {
                        "id": "research",
                        "name": "技术研究",
                        "description": f"研究 {self.config.input} 相关技术",
                        "agent_role": "researcher",
                        "estimated_minutes": 15,
                        "depends_on": []
                    },
                    {
                        "id": "design",
                        "name": "架构设计",
                        "description": f"设计 {self.config.input} 架构",
                        "agent_role": "architect",
                        "estimated_minutes": 15,
                        "depends_on": ["research"]
                    },
                    {
                        "id": "implement",
                        "name": "代码实现",
                        "description": f"实现 {self.config.input}",
                        "agent_role": "builder",
                        "estimated_minutes": 20,
                        "depends_on": ["design"]
                    },
                    {
                        "id": "validate",
                        "name": "代码验证",
                        "description": "验证代码质量",
                        "agent_role": "validator",
                        "estimated_minutes": 5,
                        "depends_on": ["implement"]
                    },
                    {
                        "id": "test",
                        "name": "功能测试",
                        "description": "测试功能正确性",
                        "agent_role": "tester",
                        "estimated_minutes": 5,
                        "depends_on": ["implement"]
                    },
                    {
                        "id": "document",
                        "name": "文档编写",
                        "description": "编写技术文档",
                        "agent_role": "scribe",
                        "estimated_minutes": 10,
                        "depends_on": ["validate", "test"]
                    }
                ]
            )
        elif "bug" in goal_lower or "fix" in goal_lower or "修复" in goal_lower:
            return ExecutionPlan(
                reasoning="Bug 修复需要快速定位、修复和验证",
                estimated_time=30,
                steps=[
                    {
                        "id": "analyze",
                        "name": "问题分析",
                        "description": f"分析 {self.config.input}",
                        "agent_role": "researcher",
                        "estimated_minutes": 10,
                        "depends_on": []
                    },
                    {
                        "id": "fix",
                        "name": "Bug 修复",
                        "description": "修复问题",
                        "agent_role": "builder",
                        "estimated_minutes": 10,
                        "depends_on": ["analyze"]
                    },
                    {
                        "id": "verify",
                        "name": "修复验证",
                        "description": "验证修复效果",
                        "agent_role": "validator",
                        "estimated_minutes": 5,
                        "depends_on": ["fix"]
                    },
                    {
                        "id": "test",
                        "name": "回归测试",
                        "description": "确保没有引入新问题",
                        "agent_role": "tester",
                        "estimated_minutes": 5,
                        "depends_on": ["fix"]
                    }
                ]
            )
        else:
            # 默认计划
            return ExecutionPlan(
                reasoning="通用任务处理流程",
                estimated_time=30,
                steps=[
                    {
                        "id": "research",
                        "name": "信息收集",
                        "description": f"收集关于 {self.config.input} 的信息",
                        "agent_role": "researcher",
                        "estimated_minutes": 15,
                        "depends_on": []
                    },
                    {
                        "id": "process",
                        "name": "处理分析",
                        "description": "处理收集的信息",
                        "agent_role": "architect",
                        "estimated_minutes": 10,
                        "depends_on": ["research"]
                    },
                    {
                        "id": "document",
                        "name": "结果整理",
                        "description": "整理最终结果",
                        "agent_role": "scribe",
                        "estimated_minutes": 5,
                        "depends_on": ["process"]
                    }
                ]
            )
    
    def _display_plan(self):
        """显示执行计划"""
        print("📋 执行计划:")
        print("-" * 60)
        
        for i, step in enumerate(self.plan.steps, 1):
            deps = f" [依赖: {', '.join(step.get('depends_on', []))}]" if step.get('depends_on') else ""
            print(f"  {i}. [{step.get('agent_role', 'unknown')}] {step.get('name', 'unnamed')}")
            print(f"     描述: {step.get('description', '')[:50]}...")
            print(f"     预计时间: {step.get('estimated_minutes', 0)} 分钟{deps}")
            print()
    
    async def _execute_plan(self) -> TeamResult:
        """执行计划"""
        # 从配置创建 Agents
        agents = {}
        for agent_id, agent_data in self.config.agents.items():
            agent = self._create_agent(agent_id, agent_data)
            agents[agent_id] = agent
        
        # 根据计划创建 Tasks
        tasks = []
        task_map = {}
        
        for step in self.plan.steps:
            agent_role = step.get('agent_role', 'assistant')
            
            # 找到对应角色的 Agent
            agent = None
            for a in agents.values():
                if a.role.value == agent_role:
                    agent = a
                    break
            
            if not agent:
                # 创建临时 Agent
                agent = Agent(
                    name=f"Agent-{agent_role}",
                    role=AgentRole(agent_role) if agent_role in [r.value for r in AgentRole] else AgentRole.ASSISTANT,
                    goal=f"执行 {step.get('name', 'task')}"
                )
            
            task = Task(
                name=step.get('name', 'unnamed'),
                description=step.get('description', ''),
                expected_output="完成",
                agent=agent
            )
            
            tasks.append(task)
            task_map[step.get('id', f"step_{len(tasks)}")] = task
        
        # 设置依赖关系
        for step in self.plan.steps:
            step_id = step.get('id', '')
            if step_id in task_map:
                task = task_map[step_id]
                for dep_id in step.get('depends_on', []):
                    if dep_id in task_map:
                        task.depends_on.append(task_map[dep_id])
        
        # 确定执行模式
        strategy_map = {
            'sequential': ProcessType.SEQUENTIAL,
            'parallel': ProcessType.PARALLEL,
            'adaptive': ProcessType.HYBRID,
        }
        process = strategy_map.get(self.config.strategy, ProcessType.HYBRID)
        
        # 创建团队并执行
        self.team = AgentTeam(
            name=self.config.name,
            agents=list(agents.values()),
            tasks=tasks,
            process=process
        )
        
        return await self.team.run(self.executor)
    
    def _create_agent(self, agent_id: str, data: Dict[str, Any]) -> Agent:
        """创建 Agent"""
        role_str = data.get('role', 'assistant').lower()
        role_map = {
            'research': AgentRole.RESEARCHER,
            'researcher': AgentRole.RESEARCHER,
            'architect': AgentRole.ARCHITECT,
            'builder': AgentRole.BUILDER,
            'developer': AgentRole.BUILDER,
            'validator': AgentRole.VALIDATOR,
            'tester': AgentRole.TESTER,
            'scribe': AgentRole.SCRIBE,
            'writer': AgentRole.SCRIBE,
            'reviewer': AgentRole.REVIEWER,
            'orchestrator': AgentRole.ORCHESTRATOR,
        }
        role = role_map.get(role_str, AgentRole.ASSISTANT)
        
        return Agent(
            name=data.get('name', agent_id),
            role=role,
            goal=data.get('goal', data.get('instructions', '')),
            backstory=data.get('backstory', ''),
            instructions=data.get('instructions', ''),
            model=data.get('model', 'ollama/qwen2.5'),
            allow_delegation=data.get('allow_delegation', False),
            tools=data.get('tools', [])
        )
    
    def _display_summary(self, result: TeamResult):
        """显示执行总结"""
        print(f"\n{'='*60}")
        print("📊 执行总结")
        print(f"{'='*60}")
        print(f"✅ 完成任务: {result.tasks_completed}")
        print(f"❌ 失败任务: {result.tasks_failed}")
        print(f"⏭️ 跳过任务: {result.tasks_skipped}")
        print(f"⏱️ 总耗时: {result.total_time:.2f} 秒")
        print(f"{'='*60}")
        
        if result.success:
            print("\n🎉 所有任务执行成功！")
        else:
            print("\n⚠️ 部分任务执行失败")
            for error in result.errors[:5]:
                print(f"  - {error}")
