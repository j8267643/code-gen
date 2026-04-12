"""
YAML Workflow Loader
支持 PraisonAI 风格的 YAML 工作流定义
"""
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import yaml
import re

from .agent import Agent, AgentRole
from .task import Task
from .team import AgentTeam, ProcessType


@dataclass
class WorkflowStep:
    """工作流步骤"""
    name: Optional[str] = None
    agent: Optional[str] = None
    action: Optional[str] = None
    parallel: Optional[List[Dict]] = None
    route: Optional[Dict[str, List[str]]] = None
    loop: Optional[Dict] = None
    repeat: Optional[Dict] = None
    depends_on: List[str] = field(default_factory=list)


@dataclass
class WorkflowConfig:
    """工作流配置"""
    name: str
    description: str = ""
    input: str = ""
    framework: str = "code_gen"
    process: str = "sequential"
    workflow: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    agents: Dict[str, Dict] = field(default_factory=dict)
    steps: List[WorkflowStep] = field(default_factory=list)
    callbacks: Dict[str, str] = field(default_factory=dict)


class WorkflowLoader:
    """
    YAML 工作流加载器
    
    支持 PraisonAI 风格的 YAML 格式
    """
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
    
    def load(self, yaml_path: Union[str, Path]) -> WorkflowConfig:
        """
        从 YAML 文件加载工作流
        
        Args:
            yaml_path: YAML 文件路径
            
        Returns:
            WorkflowConfig: 工作流配置
        """
        yaml_path = Path(yaml_path)
        
        if not yaml_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {yaml_path}")
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return self._parse_config(data)
    
    def _parse_config(self, data: Dict[str, Any]) -> WorkflowConfig:
        """解析 YAML 数据"""
        config = WorkflowConfig(
            name=data.get('name', 'Unnamed Workflow'),
            description=data.get('description', ''),
            input=data.get('input', ''),
            framework=data.get('framework', 'code_gen'),
            process=data.get('process', 'sequential'),
            workflow=data.get('workflow', {}),
            variables=data.get('variables', {}),
            agents=data.get('agents', data.get('roles', {})),
            callbacks=data.get('callbacks', {})
        )
        
        # 解析步骤
        steps_data = data.get('steps', [])
        for step_data in steps_data:
            step = self._parse_step(step_data)
            config.steps.append(step)
        
        return config
    
    def _parse_step(self, data: Dict[str, Any]) -> WorkflowStep:
        """解析单个步骤"""
        return WorkflowStep(
            name=data.get('name'),
            agent=data.get('agent'),
            action=data.get('action'),
            parallel=data.get('parallel'),
            route=data.get('route'),
            loop=data.get('loop'),
            repeat=data.get('repeat'),
            depends_on=data.get('depends_on', [])
        )
    
    def create_team(self, config: WorkflowConfig) -> AgentTeam:
        """
        从配置创建 Agent 团队
        
        Args:
            config: 工作流配置
            
        Returns:
            AgentTeam: Agent 团队
        """
        # 创建 Agents
        agents = {}
        for agent_id, agent_data in config.agents.items():
            agent = self._create_agent(agent_id, agent_data)
            agents[agent_id] = agent
        
        # 创建 Tasks
        tasks = []
        task_map = {}  # 用于依赖关系
        
        for i, step in enumerate(config.steps):
            if step.parallel:
                # 并行步骤
                parallel_tasks = []
                for parallel_step in step.parallel:
                    task = self._create_task_from_step(
                        parallel_step, agents, config.variables, config.input
                    )
                    parallel_tasks.append(task)
                    tasks.append(task)
                    task_map[f"step_{i}_{parallel_step.get('agent', 'unknown')}"] = task
                    
            elif step.route:
                # 路由步骤 - 创建条件任务
                # 简化处理：创建多个可能的任务，根据条件选择
                for route_key, agent_list in step.route.items():
                    if route_key == 'default':
                        continue
                    for agent_id in agent_list:
                        if agent_id in agents:
                            task = Task(
                                name=f"Route: {route_key}",
                                description=f"Handle {route_key} route",
                                expected_output="Route result",
                                agent=agents[agent_id]
                            )
                            tasks.append(task)
                            task_map[f"step_{i}_{route_key}"] = task
                            
            elif step.loop:
                # 循环步骤
                loop_var = step.loop.get('over', [])
                if isinstance(loop_var, str):
                    # 从 variables 获取
                    loop_items = config.variables.get(loop_var, [])
                else:
                    loop_items = loop_var
                
                for item in loop_items:
                    task = self._create_task_from_step(
                        {'agent': step.agent, 'action': step.action},
                        agents,
                        {**config.variables, 'item': item},
                        config.input
                    )
                    task.name = f"Loop: {item}"
                    tasks.append(task)
                    
            elif step.agent:
                # 普通步骤
                task = self._create_task_from_step(
                    {'agent': step.agent, 'action': step.action},
                    agents,
                    config.variables,
                    config.input
                )
                tasks.append(task)
                task_map[f"step_{i}"] = task
                
                # 处理依赖
                if step.depends_on:
                    for dep in step.depends_on:
                        if dep in task_map:
                            task.depends_on.append(task_map[dep])
        
        # 确定执行模式
        process_map = {
            'sequential': ProcessType.SEQUENTIAL,
            'parallel': ProcessType.PARALLEL,
            'hybrid': ProcessType.HYBRID,
            'workflow': ProcessType.HYBRID,
        }
        process = process_map.get(config.process, ProcessType.HYBRID)
        
        return AgentTeam(
            name=config.name,
            agents=list(agents.values()),
            tasks=tasks,
            process=process
        )
    
    def _create_agent(self, agent_id: str, data: Dict[str, Any]) -> Agent:
        """从配置创建 Agent"""
        # 映射 role 到 AgentRole
        role_str = data.get('role', 'assistant').lower()
        role_map = {
            'research': AgentRole.RESEARCHER,
            'researcher': AgentRole.RESEARCHER,
            'research analyst': AgentRole.RESEARCHER,
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
        
        # 获取 LLM 配置
        llm_config = data.get('llm', {})
        model = llm_config.get('model', 'ollama/qwen2.5')
        
        return Agent(
            name=data.get('name', agent_id),
            role=role,
            goal=data.get('goal', data.get('instructions', '')),
            backstory=data.get('backstory', ''),
            instructions=data.get('instructions', ''),
            model=model,
            allow_delegation=data.get('allow_delegation', False),
            tools=data.get('tools', [])
        )
    
    def _create_task_from_step(
        self,
        step_data: Dict[str, Any],
        agents: Dict[str, Agent],
        variables: Dict[str, Any],
        input_text: str
    ) -> Task:
        """从步骤数据创建任务"""
        agent_id = step_data.get('agent', 'default')
        agent = agents.get(agent_id)
        
        if not agent:
            # 创建默认 Agent
            agent = Agent(
                name=agent_id,
                role=AgentRole.ASSISTANT,
                goal="Complete assigned tasks"
            )
            agents[agent_id] = agent
        
        # 渲染模板
        action_template = step_data.get('action', '')
        action = self._render_template(action_template, variables, input_text)
        
        return Task(
            name=f"Task: {agent.name}",
            description=action,
            expected_output="Task completion",
            agent=agent
        )
    
    def _render_template(
        self,
        template: str,
        variables: Dict[str, Any],
        input_text: str
    ) -> str:
        """渲染模板变量"""
        if not template:
            return ""
        
        result = template
        
        # 替换 {{input}}
        result = result.replace('{{input}}', input_text)
        
        # 替换 {{variable}}
        for key, value in variables.items():
            placeholder = f'{{{{{key}}}}}'
            if isinstance(value, str):
                result = result.replace(placeholder, value)
            elif isinstance(value, (list, dict)):
                result = result.replace(placeholder, str(value))
        
        # 替换 {{previous_output}}（简化处理）
        result = result.replace('{{previous_output}}', '[Previous step output]')
        
        return result
    
    def validate(self, config: WorkflowConfig) -> List[str]:
        """
        验证工作流配置
        
        Returns:
            List[str]: 错误列表
        """
        errors = []
        
        # 检查必需的 Agents
        for step in config.steps:
            if step.agent and step.agent not in config.agents:
                errors.append(f"Agent '{step.agent}' not defined")
            
            if step.parallel:
                for parallel_step in step.parallel:
                    agent_id = parallel_step.get('agent')
                    if agent_id and agent_id not in config.agents:
                        errors.append(f"Agent '{agent_id}' in parallel step not defined")
            
            if step.route:
                for agent_list in step.route.values():
                    for agent_id in agent_list:
                        if agent_id not in config.agents:
                            errors.append(f"Agent '{agent_id}' in route not defined")
        
        return errors
