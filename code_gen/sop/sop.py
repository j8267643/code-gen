"""SOP Core Implementation"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
from datetime import datetime


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepType(Enum):
    """步骤类型"""
    SEQUENTIAL = "sequential"      # 顺序执行
    PARALLEL = "parallel"          # 并行执行
    CONDITIONAL = "conditional"    # 条件执行
    LOOP = "loop"                  # 循环执行
    HUMAN_IN_LOOP = "human_in_loop"  # 需要人工确认


@dataclass
class SOPStep:
    """SOP 步骤定义
    
    每个步骤代表 SOP 中的一个原子操作
    """
    name: str
    description: str
    action: str                      # 动作名称
    role: Optional[str] = None       # 执行角色
    step_type: StepType = StepType.SEQUENTIAL
    status: StepStatus = StepStatus.PENDING
    
    # 输入输出定义
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    
    # 依赖关系
    depends_on: List[str] = field(default_factory=list)  # 依赖的步骤名称
    
    # 条件执行
    condition: Optional[Callable[[SOPContext], bool]] = None
    
    # 重试配置
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # 超时配置
    timeout: Optional[float] = None
    
    # 元数据
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def can_execute(self, context: SOPContext) -> bool:
        """检查步骤是否可以执行"""
        if self.condition:
            return self.condition(context)
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "action": self.action,
            "role": self.role,
            "step_type": self.step_type.value,
            "status": self.status.value,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "depends_on": self.depends_on,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SOPContext:
    """SOP 执行上下文
    
    保存 SOP 执行过程中的状态和数据
    """
    sop_id: str
    sop_name: str
    
    # 输入数据
    inputs: Dict[str, Any] = field(default_factory=dict)
    
    # 步骤输出数据
    step_outputs: Dict[str, Any] = field(default_factory=dict)
    
    # 全局变量
    variables: Dict[str, Any] = field(default_factory=dict)
    
    # 执行状态
    current_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    
    # 执行历史
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 开始和结束时间
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_step_output(self, step_name: str) -> Any:
        """获取步骤输出"""
        return self.step_outputs.get(step_name)
    
    def set_step_output(self, step_name: str, output: Any):
        """设置步骤输出"""
        self.step_outputs[step_name] = output
        if step_name not in self.completed_steps:
            self.completed_steps.append(step_name)
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(name, default)
    
    def set_variable(self, name: str, value: Any):
        """设置变量"""
        self.variables[name] = value
    
    def add_execution_record(self, step_name: str, status: str, output: Any = None, error: str = None):
        """添加执行记录"""
        self.execution_history.append({
            "step_name": step_name,
            "status": status,
            "output": output,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "sop_id": self.sop_id,
            "sop_name": self.sop_name,
            "inputs": self.inputs,
            "step_outputs": self.step_outputs,
            "variables": self.variables,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "execution_history": self.execution_history,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class SOP:
    """标准作业程序
    
    定义一个完整的业务流程，包含多个步骤
    """
    name: str
    description: str
    version: str = "1.0.0"
    
    # 步骤定义
    steps: List[SOPStep] = field(default_factory=list)
    
    # 角色定义
    roles: List[str] = field(default_factory=list)
    
    # 输入输出定义
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    
    # 全局配置
    max_concurrent_steps: int = 1  # 最大并发步骤数
    fail_fast: bool = True         # 是否快速失败
    
    # 元数据
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_step(self, step: SOPStep) -> SOPStep:
        """添加步骤"""
        self.steps.append(step)
        self.updated_at = datetime.now()
        return step
    
    def get_step(self, name: str) -> Optional[SOPStep]:
        """获取步骤"""
        for step in self.steps:
            if step.name == name:
                return step
        return None
    
    def get_dependencies(self, step_name: str) -> List[SOPStep]:
        """获取步骤的依赖"""
        step = self.get_step(step_name)
        if not step:
            return []
        return [self.get_step(name) for name in step.depends_on if self.get_step(name)]
    
    def get_execution_order(self) -> List[List[str]]:
        """获取执行顺序（分层）
        
        返回分层的步骤名称列表，同层可以并行执行
        """
        executed = set()
        layers = []
        remaining = set(step.name for step in self.steps)
        
        while remaining:
            layer = []
            for step_name in list(remaining):
                step = self.get_step(step_name)
                if step:
                    deps = set(step.depends_on)
                    if deps <= executed:  # 所有依赖都已执行
                        layer.append(step_name)
            
            if not layer:
                # 存在循环依赖
                raise ValueError(f"Circular dependency detected in SOP: {remaining}")
            
            layers.append(layer)
            executed.update(layer)
            remaining -= set(layer)
        
        return layers
    
    def validate(self) -> List[str]:
        """验证 SOP 定义
        
        返回错误列表，空列表表示验证通过
        """
        errors = []
        
        # 检查步骤名称唯一性
        names = [step.name for step in self.steps]
        if len(names) != len(set(names)):
            errors.append("Duplicate step names found")
        
        # 检查依赖是否存在
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in names:
                    errors.append(f"Step '{step.name}' depends on non-existent step '{dep}'")
        
        # 检查循环依赖
        try:
            self.get_execution_order()
        except ValueError as e:
            errors.append(str(e))
        
        return errors
    
    def create_context(self, inputs: Dict[str, Any] = None) -> SOPContext:
        """创建执行上下文"""
        return SOPContext(
            sop_id=self.id,
            sop_name=self.name,
            inputs=inputs or {},
            started_at=datetime.now(),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [step.to_dict() for step in self.steps],
            "roles": self.roles,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "max_concurrent_steps": self.max_concurrent_steps,
            "fail_fast": self.fail_fast,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "author": self.author,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SOP:
        """从字典创建"""
        steps = [
            SOPStep(
                name=s["name"],
                description=s["description"],
                action=s["action"],
                role=s.get("role"),
                step_type=StepType(s.get("step_type", "sequential")),
                input_schema=s.get("input_schema", {}),
                output_schema=s.get("output_schema", {}),
                depends_on=s.get("depends_on", []),
                max_retries=s.get("max_retries", 3),
                timeout=s.get("timeout"),
            )
            for s in data.get("steps", [])
        ]
        
        return cls(
            name=data["name"],
            description=data["description"],
            version=data.get("version", "1.0.0"),
            steps=steps,
            roles=data.get("roles", []),
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {}),
            max_concurrent_steps=data.get("max_concurrent_steps", 1),
            fail_fast=data.get("fail_fast", True),
            author=data.get("author"),
            tags=data.get("tags", []),
        )


# 预定义的 SOP 模板

class SOPTemplates:
    """SOP 模板库"""
    
    @staticmethod
    def code_generation() -> SOP:
        """代码生成 SOP"""
        return SOP(
            name="code_generation",
            description="标准代码生成流程",
            roles=["product_manager", "architect", "engineer", "qa_engineer"],
            steps=[
                SOPStep(
                    name="analyze_requirement",
                    description="分析需求",
                    action="analyze_requirements",
                    role="product_manager",
                    output_schema={"requirements": "dict"},
                ),
                SOPStep(
                    name="design_architecture",
                    description="设计架构",
                    action="design_api",
                    role="architect",
                    depends_on=["analyze_requirement"],
                    output_schema={"design": "dict"},
                ),
                SOPStep(
                    name="write_code",
                    description="编写代码",
                    action="write_code",
                    role="engineer",
                    depends_on=["design_architecture"],
                    output_schema={"code": "str", "files": "list"},
                ),
                SOPStep(
                    name="review_code",
                    description="代码审查",
                    action="write_code_review",
                    role="engineer",
                    depends_on=["write_code"],
                    step_type=StepType.HUMAN_IN_LOOP,
                    output_schema={"review_result": "dict"},
                ),
                SOPStep(
                    name="write_tests",
                    description="编写测试",
                    action="write_test",
                    role="qa_engineer",
                    depends_on=["write_code"],
                    output_schema={"tests": "str"},
                ),
                SOPStep(
                    name="run_tests",
                    description="运行测试",
                    action="run_code",
                    role="qa_engineer",
                    depends_on=["write_tests"],
                    output_schema={"test_results": "dict"},
                ),
            ],
        )
    
    @staticmethod
    def bug_fix() -> SOP:
        """Bug 修复 SOP"""
        return SOP(
            name="bug_fix",
            description="标准 Bug 修复流程",
            roles=["engineer", "qa_engineer"],
            steps=[
                SOPStep(
                    name="analyze_bug",
                    description="分析 Bug",
                    action="debug_error",
                    role="engineer",
                    output_schema={"root_cause": "str", "analysis": "dict"},
                ),
                SOPStep(
                    name="fix_bug",
                    description="修复 Bug",
                    action="fix_bug",
                    role="engineer",
                    depends_on=["analyze_bug"],
                    output_schema={"fix": "str", "files_changed": "list"},
                ),
                SOPStep(
                    name="verify_fix",
                    description="验证修复",
                    action="run_code",
                    role="qa_engineer",
                    depends_on=["fix_bug"],
                    output_schema={"verification_result": "dict"},
                ),
            ],
        )
