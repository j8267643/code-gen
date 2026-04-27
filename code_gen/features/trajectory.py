"""
Trajectory Recording - 轨迹记录系统

功能：详细记录 Agent 执行过程的所有信息
整合现有 History 和 Tool Tracker 功能
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import json
import uuid


class InteractionType(str, Enum):
    """交互类型"""
    LLM_REQUEST = "llm_request"         # LLM 请求
    LLM_RESPONSE = "llm_response"       # LLM 响应
    TOOL_CALL = "tool_call"             # 工具调用
    TOOL_RESULT = "tool_result"         # 工具结果
    USER_MESSAGE = "user_message"       # 用户消息
    AGENT_STEP = "agent_step"           # Agent 步骤
    REFLECTION = "reflection"           # 反思
    ERROR = "error"                     # 错误


class ToolStatus(str, Enum):
    """工具状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class LLMInteraction:
    """LLM 交互记录"""
    interaction_id: str
    type: InteractionType
    messages: List[Dict[str, Any]] = field(default_factory=list)
    response: Optional[str] = None
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "type": self.type.value,
            "messages": self.messages,
            "response": self.response,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms
        }


@dataclass
class ToolInteraction:
    """工具交互记录"""
    interaction_id: str
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    error: Optional[str] = None
    status: ToolStatus = ToolStatus.PENDING
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "error": self.error,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms
        }


@dataclass
class AgentStep:
    """Agent 执行步骤"""
    step_id: str
    step_number: int
    action: str
    reasoning: Optional[str] = None
    tool_calls: List[str] = field(default_factory=list)  # 关联的工具调用ID
    observations: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "action": self.action,
            "reasoning": self.reasoning,
            "tool_calls": self.tool_calls,
            "observations": self.observations,
            "timestamp": self.timestamp
        }


@dataclass
class Trajectory:
    """完整轨迹"""
    trajectory_id: str
    task: str
    start_time: str
    end_time: Optional[str] = None
    provider: str = "unknown"
    model: str = "unknown"
    max_steps: int = 100
    
    llm_interactions: List[LLMInteraction] = field(default_factory=list)
    tool_interactions: List[ToolInteraction] = field(default_factory=list)
    agent_steps: List[AgentStep] = field(default_factory=list)
    
    success: bool = False
    final_result: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trajectory_id": self.trajectory_id,
            "task": self.task,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "provider": self.provider,
            "model": self.model,
            "max_steps": self.max_steps,
            "llm_interactions": [i.to_dict() for i in self.llm_interactions],
            "tool_interactions": [i.to_dict() for i in self.tool_interactions],
            "agent_steps": [s.to_dict() for s in self.agent_steps],
            "success": self.success,
            "final_result": self.final_result,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata
        }


class TrajectoryRecorder:
    """轨迹记录器"""
    
    def __init__(self, output_dir: str = "trajectories"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_trajectory: Optional[Trajectory] = None
        self._step_counter: int = 0
        self._start_time: Optional[datetime] = None
    
    def start_recording(self, task: str, provider: str = "unknown", 
                       model: str = "unknown", max_steps: int = 100,
                       metadata: Optional[Dict[str, Any]] = None) -> Trajectory:
        """开始记录"""
        self._start_time = datetime.now()
        self._step_counter = 0
        
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4())[:8],
            task=task,
            start_time=self._start_time.isoformat(),
            provider=provider,
            model=model,
            max_steps=max_steps,
            metadata=metadata or {}
        )
        
        self.current_trajectory = trajectory
        return trajectory
    
    def record_llm_request(self, messages: List[Dict[str, Any]], 
                          model: Optional[str] = None) -> str:
        """记录 LLM 请求"""
        if not self.current_trajectory:
            return ""
        
        interaction_id = f"llm_req_{len(self.current_trajectory.llm_interactions)}"
        interaction = LLMInteraction(
            interaction_id=interaction_id,
            type=InteractionType.LLM_REQUEST,
            messages=messages,
            model=model
        )
        
        self.current_trajectory.llm_interactions.append(interaction)
        return interaction_id
    
    def record_llm_response(self, interaction_id: str, response: str,
                           tokens_used: Optional[int] = None,
                           duration_ms: Optional[float] = None):
        """记录 LLM 响应"""
        if not self.current_trajectory:
            return
        
        # 找到对应的请求并更新
        for interaction in self.current_trajectory.llm_interactions:
            if interaction.interaction_id == interaction_id:
                interaction.response = response
                interaction.tokens_used = tokens_used
                interaction.duration_ms = duration_ms
                break
    
    def record_interaction(self, interaction_type: str, data: Dict[str, Any]):
        """记录通用交互"""
        if not self.current_trajectory:
            return
        
        if interaction_type == "user_message":
            self.current_trajectory.metadata["user_messages"] = \
                self.current_trajectory.metadata.get("user_messages", []) + [data]
        elif interaction_type == "agent_response":
            self.current_trajectory.metadata["agent_responses"] = \
                self.current_trajectory.metadata.get("agent_responses", []) + [data]
    
    def record_tool_call(self, tool_name: str, 
                        arguments: Dict[str, Any]) -> str:
        """记录工具调用"""
        if not self.current_trajectory:
            return ""
        
        interaction_id = f"tool_{len(self.current_trajectory.tool_interactions)}"
        interaction = ToolInteraction(
            interaction_id=interaction_id,
            tool_name=tool_name,
            arguments=arguments,
            status=ToolStatus.RUNNING
        )
        
        self.current_trajectory.tool_interactions.append(interaction)
        return interaction_id
    
    def record_tool_result(self, interaction_id: str, result: Optional[str] = None,
                          error: Optional[str] = None,
                          duration_ms: Optional[float] = None):
        """记录工具结果"""
        if not self.current_trajectory:
            return
        
        for interaction in self.current_trajectory.tool_interactions:
            if interaction.interaction_id == interaction_id:
                interaction.result = result
                interaction.error = error
                interaction.duration_ms = duration_ms
                
                if error:
                    interaction.status = ToolStatus.FAILED
                else:
                    interaction.status = ToolStatus.SUCCESS
                break
    
    def record_agent_step(self, action: str, 
                         reasoning: Optional[str] = None,
                         tool_calls: Optional[List[str]] = None) -> str:
        """记录 Agent 步骤"""
        if not self.current_trajectory:
            return ""
        
        self._step_counter += 1
        step_id = f"step_{self._step_counter}"
        
        step = AgentStep(
            step_id=step_id,
            step_number=self._step_counter,
            action=action,
            reasoning=reasoning,
            tool_calls=tool_calls or []
        )
        
        self.current_trajectory.agent_steps.append(step)
        return step_id
    
    def add_observation(self, step_id: str, observation: str):
        """添加观察结果到步骤"""
        if not self.current_trajectory:
            return
        
        for step in self.current_trajectory.agent_steps:
            if step.step_id == step_id:
                step.observations.append(observation)
                break
    
    def finish_recording(self, success: bool = False, 
                        final_result: Optional[str] = None,
                        error_message: Optional[str] = None):
        """完成记录"""
        if not self.current_trajectory:
            return
        
        end_time = datetime.now()
        self.current_trajectory.end_time = end_time.isoformat()
        self.current_trajectory.success = success
        self.current_trajectory.final_result = final_result
        self.current_trajectory.error_message = error_message
        
        if self._start_time:
            duration = (end_time - self._start_time).total_seconds() * 1000
            self.current_trajectory.execution_time_ms = duration
    
    def save(self, filename: Optional[str] = None) -> str:
        """保存轨迹到文件"""
        if not self.current_trajectory:
            return ""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trajectory_{timestamp}_{self.current_trajectory.trajectory_id}.json"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.current_trajectory.to_dict(), f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def get_summary(self) -> str:
        """获取轨迹摘要"""
        if not self.current_trajectory:
            return "没有活动的轨迹记录"
        
        t = self.current_trajectory
        lines = [
            f"📊 轨迹摘要: {t.trajectory_id}",
            f"任务: {t.task}",
            f"模型: {t.provider}/{t.model}",
            f"步骤数: {len(t.agent_steps)}",
            f"LLM 交互: {len(t.llm_interactions)}",
            f"工具调用: {len(t.tool_interactions)}",
            f"状态: {'✅ 成功' if t.success else '❌ 失败'}",
        ]
        
        if t.execution_time_ms:
            lines.append(f"执行时间: {t.execution_time_ms/1000:.2f}s")
        
        return "\n".join(lines)
    
    def load_trajectory(self, filepath: str) -> Optional[Trajectory]:
        """加载轨迹"""
        path = Path(filepath)
        if not path.exists():
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 这里简化处理，实际应该完整解析
        return None


class TrajectoryAnalyzer:
    """轨迹分析器"""
    
    def __init__(self, trajectory: Trajectory):
        self.trajectory = trajectory
    
    def analyze_tool_usage(self) -> Dict[str, Any]:
        """分析工具使用情况"""
        tool_counts = {}
        tool_durations = {}
        
        for interaction in self.trajectory.tool_interactions:
            name = interaction.tool_name
            tool_counts[name] = tool_counts.get(name, 0) + 1
            
            if interaction.duration_ms:
                if name not in tool_durations:
                    tool_durations[name] = []
                tool_durations[name].append(interaction.duration_ms)
        
        avg_durations = {
            name: sum(durations) / len(durations)
            for name, durations in tool_durations.items()
        }
        
        return {
            "tool_counts": tool_counts,
            "avg_durations_ms": avg_durations,
            "total_tools": len(self.trajectory.tool_interactions)
        }
    
    def analyze_success_rate(self) -> Dict[str, Any]:
        """分析成功率"""
        total = len(self.trajectory.tool_interactions)
        if total == 0:
            return {"success_rate": 0, "total": 0}
        
        successful = sum(1 for t in self.trajectory.tool_interactions 
                        if t.status == ToolStatus.SUCCESS)
        
        return {
            "success_rate": successful / total,
            "successful": successful,
            "failed": total - successful,
            "total": total
        }
    
    def get_token_usage(self) -> Dict[str, Any]:
        """获取 Token 使用情况"""
        total_tokens = 0
        interactions_with_tokens = 0
        
        for interaction in self.trajectory.llm_interactions:
            if interaction.tokens_used:
                total_tokens += interaction.tokens_used
                interactions_with_tokens += 1
        
        return {
            "total_tokens": total_tokens,
            "interactions_with_tokens": interactions_with_tokens,
            "avg_tokens_per_interaction": total_tokens / interactions_with_tokens if interactions_with_tokens > 0 else 0
        }


# 便捷函数
def create_trajectory_recorder(output_dir: str = "trajectories") -> TrajectoryRecorder:
    """创建轨迹记录器"""
    return TrajectoryRecorder(output_dir=output_dir)
