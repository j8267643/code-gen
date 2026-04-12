"""
Dynamic YAML Workflow Loader
支持 Agent 自主规划的 YAML 格式
"""
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import yaml

from .dynamic_workflow import DynamicWorkflowConfig, DynamicWorkflow
from .executor import AgentExecutor


class DynamicWorkflowLoader:
    """
    动态工作流 YAML 加载器
    
    YAML 格式不需要预定义 steps，Agent 会自主规划
    """
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
    
    def load(self, yaml_path: Union[str, Path]) -> DynamicWorkflowConfig:
        """
        从 YAML 文件加载动态工作流配置
        
        Args:
            yaml_path: YAML 文件路径
            
        Returns:
            DynamicWorkflowConfig: 动态工作流配置
        """
        yaml_path = Path(yaml_path)
        
        if not yaml_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {yaml_path}")
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return self._parse_config(data)
    
    def _parse_config(self, data: Dict[str, Any]) -> DynamicWorkflowConfig:
        """解析 YAML 数据"""
        return DynamicWorkflowConfig(
            name=data.get('name', 'Unnamed Workflow'),
            description=data.get('description', ''),
            goal=data.get('goal', data.get('objective', '')),
            input=data.get('input', data.get('context', '')),
            framework=data.get('framework', 'code_gen'),
            strategy=data.get('strategy', 'adaptive'),
            max_iterations=data.get('max_iterations', 10),
            agents=data.get('agents', data.get('roles', {})),
            tools=data.get('tools', []),
            constraints=data.get('constraints', {}),
            callbacks=data.get('callbacks', {})
        )
    
    def create_workflow(
        self,
        config: DynamicWorkflowConfig,
        executor: AgentExecutor
    ) -> DynamicWorkflow:
        """
        从配置创建动态工作流
        
        Args:
            config: 动态工作流配置
            executor: Agent 执行器
            
        Returns:
            DynamicWorkflow: 动态工作流实例
        """
        return DynamicWorkflow(config, self.work_dir, executor)
    
    def validate(self, config: DynamicWorkflowConfig) -> List[str]:
        """
        验证工作流配置
        
        Returns:
            List[str]: 错误列表
        """
        errors = []
        
        if not config.name:
            errors.append("Workflow name is required")
        
        if not config.goal and not config.description:
            errors.append("Either goal or description is required")
        
        if not config.agents:
            errors.append("At least one agent must be defined")
        
        # 检查 Agent 定义
        for agent_id, agent_data in config.agents.items():
            if not agent_data.get('role') and not agent_data.get('goal'):
                errors.append(f"Agent '{agent_id}' must have either role or goal defined")
        
        # 检查策略
        valid_strategies = ['sequential', 'parallel', 'adaptive']
        if config.strategy not in valid_strategies:
            errors.append(f"Invalid strategy '{config.strategy}'. Must be one of: {valid_strategies}")
        
        return errors
