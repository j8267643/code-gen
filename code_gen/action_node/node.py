"""Action Node Core"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Callable, Union, TYPE_CHECKING
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from .parser import JSONParser, MarkdownParser


class ActionStatus(Enum):
    """动作状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class NodeOutput:
    """节点输出"""
    content: Any                              # 原始输出内容
    parsed_data: Optional[Dict[str, Any]] = None  # 解析后的数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 执行信息
    execution_time: float = 0.0               # 执行时间（秒）
    token_count: int = 0                      # Token 数量
    cost: float = 0.0                         # 成本
    
    # 错误信息
    error: Optional[str] = None
    
    def is_success(self) -> bool:
        """是否成功"""
        return self.error is None
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取解析后的数据"""
        if self.parsed_data:
            return self.parsed_data.get(key, default)
        return default
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "parsed_data": self.parsed_data,
            "metadata": self.metadata,
            "execution_time": self.execution_time,
            "token_count": self.token_count,
            "cost": self.cost,
            "error": self.error,
        }


@dataclass
class FieldDefinition:
    """字段定义"""
    name: str
    field_type: Type                           # 字段类型
    description: str = ""                      # 字段描述
    required: bool = True                      # 是否必填
    default: Any = None                        # 默认值
    example: Any = None                        # 示例值
    constraints: Dict[str, Any] = field(default_factory=dict)  # 约束条件
    
    def validate(self, value: Any) -> tuple:
        """验证值
        
        Returns:
            (is_valid, error_message)
        """
        # 检查必填
        if value is None:
            if self.required and self.default is None:
                return False, f"Field '{self.name}' is required"
            return True, None
        
        # 检查类型
        if not isinstance(value, self.field_type):
            try:
                value = self.field_type(value)
            except (ValueError, TypeError):
                return False, f"Field '{self.name}' should be of type {self.field_type.__name__}"
        
        # 检查约束
        if "min_length" in self.constraints and isinstance(value, (str, list)):
            if len(value) < self.constraints["min_length"]:
                return False, f"Field '{self.name}' should have at least {self.constraints['min_length']} items"
        
        if "max_length" in self.constraints and isinstance(value, (str, list)):
            if len(value) > self.constraints["max_length"]:
                return False, f"Field '{self.name}' should have at most {self.constraints['max_length']} items"
        
        if "min" in self.constraints and isinstance(value, (int, float)):
            if value < self.constraints["min"]:
                return False, f"Field '{self.name}' should be at least {self.constraints['min']}"
        
        if "max" in self.constraints and isinstance(value, (int, float)):
            if value > self.constraints["max"]:
                return False, f"Field '{self.name}' should be at most {self.constraints['max']}"
        
        return True, None


@dataclass
class ActionNode:
    """动作节点
    
    标准化的动作定义，包含输入输出模式、提示模板等
    """
    # 基本信息
    name: str
    description: str = ""
    instruction: str = ""                      # 执行指令
    
    # 输入定义
    input_fields: List[FieldDefinition] = field(default_factory=list)
    
    # 输出定义
    output_fields: List[FieldDefinition] = field(default_factory=list)
    
    # 提示模板
    prompt_template: str = ""                  # 提示模板
    system_prompt: str = ""                    # 系统提示
    
    # 执行配置
    model: Optional[str] = None                # 使用的模型
    temperature: float = 0.7                   # 温度
    max_tokens: Optional[int] = None           # 最大 token
    
    # 重试配置
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # 解析配置
    output_format: str = "json"                # 输出格式 (json, markdown, text)
    
    # 回调函数
    pre_process: Optional[Callable] = None     # 预处理
    post_process: Optional[Callable] = None    # 后处理
    validator: Optional[Callable] = None       # 自定义验证
    
    # 状态
    status: ActionStatus = ActionStatus.PENDING
    
    # 元数据
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.prompt_template and self.output_fields:
            self.prompt_template = self._generate_default_prompt()
    
    def _generate_default_prompt(self) -> str:
        """生成默认提示模板"""
        prompt = f"""# Task: {self.name}

{self.instruction}

## Output Format
Please provide your response in the following format:

"""
        for field in self.output_fields:
            prompt += f"- **{field.name}** ({field.field_type.__name__}): {field.description}\n"
            if field.example is not None:
                prompt += f"  Example: {field.example}\n"
        
        prompt += "\n## Response\n"
        return prompt
    
    def build_prompt(self, inputs: Dict[str, Any]) -> str:
        """构建提示"""
        prompt = self.prompt_template
        
        # 替换输入变量
        for key, value in inputs.items():
            placeholder = f"{{{key}}}"
            if placeholder in prompt:
                prompt = prompt.replace(placeholder, str(value))
        
        return prompt
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> tuple:
        """验证输入
        
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        for field in self.input_fields:
            value = inputs.get(field.name)
            is_valid, error = field.validate(value)
            if not is_valid:
                errors.append(error)
        
        # 自定义验证
        if self.validator:
            try:
                custom_valid = self.validator(inputs)
                if not custom_valid:
                    errors.append("Custom validation failed")
            except Exception as e:
                errors.append(f"Custom validation error: {e}")
        
        return len(errors) == 0, errors
    
    def validate_outputs(self, outputs: Dict[str, Any]) -> tuple:
        """验证输出"""
        errors = []
        
        for field in self.output_fields:
            value = outputs.get(field.name)
            is_valid, error = field.validate(value)
            if not is_valid:
                errors.append(error)
        
        return len(errors) == 0, errors
    
    def parse_output(self, content: str) -> Dict[str, Any]:
        """解析输出"""
        # 延迟导入避免循环依赖
        from .parser import JSONParser, MarkdownParser
        
        if self.output_format == "json":
            parser = JSONParser()
        elif self.output_format == "markdown":
            parser = MarkdownParser()
        else:
            # 文本格式，直接返回
            return {"content": content}
        
        return parser.parse(content, self.output_fields)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "instruction": self.instruction,
            "input_fields": [
                {
                    "name": f.name,
                    "type": f.field_type.__name__,
                    "description": f.description,
                    "required": f.required,
                    "default": f.default,
                    "example": f.example,
                }
                for f in self.input_fields
            ],
            "output_fields": [
                {
                    "name": f.name,
                    "type": f.field_type.__name__,
                    "description": f.description,
                    "required": f.required,
                    "default": f.default,
                    "example": f.example,
                }
                for f in self.output_fields
            ],
            "prompt_template": self.prompt_template,
            "system_prompt": self.system_prompt,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "output_format": self.output_format,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ActionNode:
        """从字典创建"""
        # 基础类型映射
        base_type_mapping = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "any": Any,
        }

        # 复杂类型解析
        def parse_type(type_str: str) -> type:
            """解析类型字符串为类型对象"""
            if not type_str:
                return str

            type_str = type_str.strip()

            # 基础类型
            if type_str in base_type_mapping:
                return base_type_mapping[type_str]

            # 泛型类型：List[...], Dict[...], Optional[...]
            if "[" in type_str and type_str.endswith("]"):
                # 提取主类型和参数
                main_type = type_str[:type_str.index("[")]
                inner = type_str[type_str.index("[") + 1:-1]

                if main_type in ("List", "list"):
                    return list
                elif main_type in ("Dict", "dict"):
                    return dict
                elif main_type in ("Optional", "Union"):
                    # 取第一个类型
                    if "," in inner:
                        inner = inner.split(",")[0].strip()
                    return parse_type(inner)
                else:
                    # 其他泛型，返回主类型
                    return base_type_mapping.get(main_type.lower(), str)

            # 未知类型，返回字符串
            return str

        def parse_field(f_data: Dict) -> FieldDefinition:
            type_str = f_data.get("type", "str")
            return FieldDefinition(
                name=f_data["name"],
                field_type=parse_type(type_str),
                description=f_data.get("description", ""),
                required=f_data.get("required", True),
                default=f_data.get("default"),
                example=f_data.get("example"),
            )
        
        return cls(
            id=data.get("id"),
            name=data["name"],
            description=data.get("description", ""),
            instruction=data.get("instruction", ""),
            input_fields=[parse_field(f) for f in data.get("input_fields", [])],
            output_fields=[parse_field(f) for f in data.get("output_fields", [])],
            prompt_template=data.get("prompt_template", ""),
            system_prompt=data.get("system_prompt", ""),
            model=data.get("model"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens"),
            output_format=data.get("output_format", "json"),
            tags=data.get("tags", []),
        )


# 预定义的 ActionNode 模板

class ActionTemplates:
    """动作模板库"""
    
    @staticmethod
    def code_generation() -> ActionNode:
        """代码生成动作"""
        return ActionNode(
            name="code_generation",
            description="Generate code based on requirements",
            instruction="Generate high-quality, well-documented code based on the given requirements.",
            input_fields=[
                FieldDefinition(
                    name="requirements",
                    field_type=str,
                    description="The requirements for the code",
                    required=True,
                ),
                FieldDefinition(
                    name="language",
                    field_type=str,
                    description="Programming language",
                    default="python",
                ),
                FieldDefinition(
                    name="context",
                    field_type=str,
                    description="Additional context",
                    default="",
                ),
            ],
            output_fields=[
                FieldDefinition(
                    name="code",
                    field_type=str,
                    description="The generated code",
                    required=True,
                ),
                FieldDefinition(
                    name="explanation",
                    field_type=str,
                    description="Explanation of the code",
                    required=True,
                ),
                FieldDefinition(
                    name="dependencies",
                    field_type=list,
                    description="Required dependencies",
                    default=[],
                ),
            ],
            tags=["code", "generation"],
        )
    
    @staticmethod
    def code_review() -> ActionNode:
        """代码审查动作"""
        return ActionNode(
            name="code_review",
            description="Review code for quality and issues",
            instruction="Review the provided code for quality, bugs, security issues, and best practices.",
            input_fields=[
                FieldDefinition(
                    name="code",
                    field_type=str,
                    description="The code to review",
                    required=True,
                ),
                FieldDefinition(
                    name="language",
                    field_type=str,
                    description="Programming language",
                    default="python",
                ),
            ],
            output_fields=[
                FieldDefinition(
                    name="issues",
                    field_type=list,
                    description="List of issues found",
                    required=True,
                ),
                FieldDefinition(
                    name="suggestions",
                    field_type=list,
                    description="Improvement suggestions",
                    required=True,
                ),
                FieldDefinition(
                    name="score",
                    field_type=int,
                    description="Quality score (1-10)",
                    required=True,
                    constraints={"min": 1, "max": 10},
                ),
            ],
            tags=["code", "review"],
        )
    
    @staticmethod
    def test_generation() -> ActionNode:
        """测试生成动作"""
        return ActionNode(
            name="test_generation",
            description="Generate tests for code",
            instruction="Generate comprehensive unit tests for the provided code.",
            input_fields=[
                FieldDefinition(
                    name="code",
                    field_type=str,
                    description="The code to test",
                    required=True,
                ),
                FieldDefinition(
                    name="test_framework",
                    field_type=str,
                    description="Test framework to use",
                    default="pytest",
                ),
            ],
            output_fields=[
                FieldDefinition(
                    name="test_code",
                    field_type=str,
                    description="The generated test code",
                    required=True,
                ),
                FieldDefinition(
                    name="test_cases",
                    field_type=list,
                    description="List of test cases covered",
                    required=True,
                ),
                FieldDefinition(
                    name="coverage_estimate",
                    field_type=float,
                    description="Estimated code coverage",
                    required=True,
                ),
            ],
            tags=["test", "generation"],
        )
