"""
Task definition for multi-agent system
"""
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from .agent import Agent


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"          # 等待中
    RUNNING = "running"          # 执行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    BLOCKED = "blocked"          # 被阻塞（依赖未完成）
    SKIPPED = "skipped"          # 已跳过


@dataclass
class Task:
    """
    任务定义
    
    Attributes:
        name: 任务名称
        description: 任务描述
        expected_output: 期望输出
        agent: 执行任务的 Agent
        depends_on: 依赖的任务
        status: 任务状态
        context: 任务上下文（从前序任务传递）
        output: 任务输出
        metadata: 元数据
    """
    name: str
    description: str
    expected_output: str
    agent: Optional["Agent"] = None
    depends_on: List["Task"] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    context: Dict[str, Any] = field(default_factory=dict)
    output: str = ""
    error: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        """初始化后的处理"""
        # 确保 depends_on 是列表
        if self.depends_on is None:
            self.depends_on = []
    
    def is_ready(self) -> bool:
        """检查任务是否准备好执行（所有依赖已完成）"""
        if not self.depends_on:
            return True
        return all(
            dep.status == TaskStatus.COMPLETED 
            for dep in self.depends_on
        )
    
    def is_blocked(self) -> bool:
        """检查任务是否被阻塞"""
        if not self.depends_on:
            return False
        return any(
            dep.status in [TaskStatus.FAILED, TaskStatus.SKIPPED]
            for dep in self.depends_on
        )
    
    def start(self):
        """开始执行任务"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
    
    def complete(self, output: str):
        """完成任务"""
        self.status = TaskStatus.COMPLETED
        self.output = output
        self.completed_at = datetime.now()
    
    def fail(self, error: str):
        """标记任务失败"""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()
    
    def skip(self):
        """跳过任务"""
        self.status = TaskStatus.SKIPPED
        self.completed_at = datetime.now()
    
    def get_execution_time(self) -> Optional[float]:
        """获取执行时间（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def build_prompt(self) -> str:
        """构建任务提示词"""
        prompt = f"""# 任务: {self.name}

## 描述
{self.description}

## 期望输出
{self.expected_output}
"""
        
        # 添加上下文（来自依赖任务的输出）
        if self.context:
            prompt += "\n## 上下文信息\n"
            for key, value in self.context.items():
                if isinstance(value, str) and len(value) > 500:
                    value = value[:500] + "..."
                prompt += f"\n### {key}\n{value}\n"
        
        # 添加依赖任务的输出
        if self.depends_on:
            prompt += "\n## 前置任务输出\n"
            for dep in self.depends_on:
                if dep.output:
                    prompt += f"\n### 来自 {dep.name}\n"
                    output = dep.output[:1000] if len(dep.output) > 1000 else dep.output
                    prompt += f"{output}\n"
        
        return prompt
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "expected_output": self.expected_output,
            "agent_id": self.agent.id if self.agent else None,
            "depends_on": [dep.id for dep in self.depends_on],
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata
        }


class TaskBuilder:
    """任务构建器 - 用于链式创建任务"""
    
    def __init__(self):
        self.tasks: List[Task] = []
        self.last_task: Optional[Task] = None
    
    def add_task(
        self,
        name: str,
        description: str,
        expected_output: str,
        agent: Optional["Agent"] = None
    ) -> "TaskBuilder":
        """添加任务"""
        task = Task(
            name=name,
            description=description,
            expected_output=expected_output,
            agent=agent,
            depends_on=[self.last_task] if self.last_task else []
        )
        self.tasks.append(task)
        self.last_task = task
        return self
    
    def parallel(self, *tasks: Task) -> "TaskBuilder":
        """添加并行任务（依赖同一个前置任务）"""
        for task in tasks:
            if self.last_task and task not in self.tasks:
                task.depends_on.append(self.last_task)
                self.tasks.append(task)
        return self
    
    def build(self) -> List[Task]:
        """构建任务列表"""
        return self.tasks
