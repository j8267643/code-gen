"""
Agent Step State Management - 步骤状态管理

参考 Trae Agent 的实现，为 CodeGen 添加清晰的状态机
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AgentStepState(Enum):
    """Agent 步骤状态"""
    THINKING = "thinking"           # 正在思考
    CALLING_TOOL = "calling_tool"   # 正在调用工具
    REFLECTING = "reflecting"       # 正在反思
    COMPLETED = "completed"         # 已完成
    ERROR = "error"                 # 出错


@dataclass
class ToolCall:
    """工具调用记录"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    error: Optional[str] = None
    success: bool = True


@dataclass
class AgentStep:
    """Agent 执行步骤"""
    step_number: int
    state: AgentStepState = field(default=AgentStepState.THINKING)
    thought: Optional[str] = None           # AI 的思考内容
    tool_calls: List[ToolCall] = field(default_factory=list)
    reflection: Optional[str] = None        # 反思结果
    error: Optional[str] = None             # 错误信息
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def set_thinking(self, thought: str):
        """设置思考内容"""
        self.state = AgentStepState.THINKING
        self.thought = thought
    
    def set_calling_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """设置正在调用工具"""
        self.state = AgentStepState.CALLING_TOOL
        self.tool_calls.append(ToolCall(
            tool_name=tool_name,
            arguments=arguments
        ))
    
    def set_tool_result(self, result: str, success: bool = True, error: Optional[str] = None):
        """设置工具调用结果"""
        if self.tool_calls:
            last_call = self.tool_calls[-1]
            last_call.result = result
            last_call.success = success
            last_call.error = error
    
    def set_reflecting(self, reflection: str):
        """设置反思内容"""
        self.state = AgentStepState.REFLECTING
        self.reflection = reflection
    
    def set_completed(self):
        """设置步骤完成"""
        self.state = AgentStepState.COMPLETED
    
    def set_error(self, error: str):
        """设置错误状态"""
        self.state = AgentStepState.ERROR
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "step_number": self.step_number,
            "state": self.state.value,
            "thought": self.thought,
            "tool_calls": [
                {
                    "tool_name": tc.tool_name,
                    "arguments": tc.arguments,
                    "result": tc.result,
                    "error": tc.error,
                    "success": tc.success
                }
                for tc in self.tool_calls
            ],
            "reflection": self.reflection,
            "error": self.error,
            "timestamp": self.timestamp
        }


class AgentStepManager:
    """Agent 步骤管理器"""
    
    def __init__(self):
        self.steps: List[AgentStep] = []
        self.current_step: Optional[AgentStep] = None
    
    def start_step(self, step_number: int) -> AgentStep:
        """开始新步骤"""
        step = AgentStep(step_number=step_number)
        self.current_step = step
        self.steps.append(step)
        return step
    
    def set_thinking(self, thought: str):
        """设置思考内容"""
        if self.current_step:
            self.current_step.state = AgentStepState.THINKING
            self.current_step.thought = thought
    
    def set_calling_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """设置正在调用工具"""
        if self.current_step:
            self.current_step.state = AgentStepState.CALLING_TOOL
            self.current_step.tool_calls.append(ToolCall(
                tool_name=tool_name,
                arguments=arguments
            ))
    
    def set_tool_result(self, result: str, success: bool = True, error: Optional[str] = None):
        """设置工具调用结果"""
        if self.current_step and self.current_step.tool_calls:
            last_call = self.current_step.tool_calls[-1]
            last_call.result = result
            last_call.success = success
            last_call.error = error
    
    def set_reflecting(self, reflection: str):
        """设置反思内容"""
        if self.current_step:
            self.current_step.state = AgentStepState.REFLECTING
            self.current_step.reflection = reflection
    
    def set_completed(self):
        """设置步骤完成"""
        if self.current_step:
            self.current_step.state = AgentStepState.COMPLETED
    
    def set_error(self, error: str):
        """设置错误状态"""
        if self.current_step:
            self.current_step.state = AgentStepState.ERROR
            self.current_step.error = error
    
    def get_current_step(self) -> Optional[AgentStep]:
        """获取当前步骤"""
        return self.current_step
    
    def get_all_steps(self) -> List[AgentStep]:
        """获取所有步骤"""
        return self.steps
    
    def reflect_on_results(self) -> Optional[str]:
        """
        反思工具执行结果
        参考 Trae Agent 的 reflect_on_result 方法
        """
        if not self.current_step or not self.current_step.tool_calls:
            return None
        
        failed_calls = [
            call for call in self.current_step.tool_calls 
            if not call.success
        ]
        
        if not failed_calls:
            return None
        
        reflections = []
        for call in failed_calls:
            reflections.append(
                f"工具 '{call.tool_name}' 执行失败: {call.error}. "
                f"请检查参数是否正确，或尝试使用不同的方法。"
            )
        
        return "\n".join(reflections)
    
    def reset(self):
        """重置所有步骤"""
        self.steps = []
        self.current_step = None
