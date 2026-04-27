"""
Agent 增强功能整合模块

核心功能：
1. Lakeview - 智能步骤摘要
2. Sequential Thinking - 序列化思考
3. Trajectory Recording - 轨迹记录
4. Task Done Tool - 任务完成标记
5. Advanced Edit Tools - 高级编辑工具

使用方法:
    from code_gen.features import (
        Lakeview, LakeviewSummarizer,
        SequentialThinkingEngine, ThoughtType,
        TrajectoryRecorder,
        TaskDoneManager,
        AdvancedEdit
    )
    
    # 或者使用统一的 AgentFeatures 类
    from code_gen.features import AgentFeatures
    
    features = AgentFeatures()
    features.enable_all()
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

# 导入各个功能模块
from code_gen.features.lakeview import Lakeview, StepTag, LakeviewSummarizer
from code_gen.features.sequential_thinking import (
    SequentialThinkingEngine, ThoughtType, Thought, ThinkingSession
)
from code_gen.features.trajectory import TrajectoryRecorder
from code_gen.features.task_done import TaskDoneManager
from code_gen.features.advanced_edit import AdvancedEditTool


@dataclass
class AgentFeaturesConfig:
    """功能配置"""
    lakeview_enabled: bool = True
    sequential_thinking_enabled: bool = True
    trajectory_enabled: bool = True
    task_done_enabled: bool = True
    advanced_edit_enabled: bool = True
    
    # 配置参数
    trajectory_output_dir: str = "trajectories"
    max_thoughts: int = 20
    working_dir: str = "."


class LakeviewManager:
    """Lakeview 管理器"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.lakeview = Lakeview() if enabled else None
    
    def record_step(self, action: str, result: Optional[str] = None, 
                   tool_name: Optional[str] = None) -> Optional[str]:
        """记录步骤并返回摘要"""
        if not self.enabled or not self.lakeview:
            return None
        
        summary = self.lakeview.record_step(action, result, tool_name)
        if summary:
            return self.lakeview.summarizer.get_summary_text(summary, verbose=False)
        return None
    
    def get_summary(self) -> str:
        """获取完整摘要"""
        if not self.enabled or not self.lakeview:
            return "Lakeview 未启用"
        return self.lakeview.get_full_summary()
    
    def print_summary(self):
        """打印摘要"""
        print(self.get_summary())
    
    def reset(self):
        """重置 Lakeview 状态"""
        if self.enabled and self.lakeview:
            self.lakeview.reset()


class SequentialThinkingManager:
    """序列化思考管理器"""
    
    def __init__(self, enabled: bool = True, max_thoughts: int = 20):
        self.enabled = enabled
        self.engine = SequentialThinkingEngine(max_thoughts=max_thoughts) if enabled else None
        self.current_session = None
    
    def start(self, problem: str) -> str:
        """开始思考"""
        if not self.enabled or not self.engine:
            return "序列化思考未启用"
        import uuid
        session_id = str(uuid.uuid4())
        self.current_session = self.engine.create_session(session_id, problem)
        return f"开始思考问题: {problem}"
    
    def think(self, thought: str, thought_type: str = "analysis",
             next_needed: bool = True) -> str:
        """添加思考"""
        if not self.enabled or not self.engine or not self.current_session:
            return "序列化思考未启用或未开始"
        try:
            t_type = ThoughtType(thought_type.lower())
        except ValueError:
            t_type = ThoughtType.ANALYSIS
        
        thought_num = len(self.current_session.thoughts) + 1
        self.engine.add_thought(
            self.current_session.session_id,
            thought=thought,
            thought_number=thought_num,
            total_thoughts=thought_num + (1 if next_needed else 0),
            next_thought_needed=next_needed,
            thought_type=t_type
        )
        return f"思考 {thought_num} 已记录"
    
    def conclude(self, conclusion: str) -> str:
        """得出结论"""
        if not self.enabled or not self.engine or not self.current_session:
            return "序列化思考未启用或未开始"
        self.current_session.conclusion = conclusion
        self.current_session.completed = True
        return f"结论: {conclusion}"
    
    def get_summary(self) -> str:
        """获取思考摘要"""
        if not self.enabled or not self.engine or not self.current_session:
            return "序列化思考未启用"
        return self.engine.get_thinking_summary(self.current_session.session_id)


class TrajectoryManager:
    """轨迹记录管理器"""
    
    def __init__(self, enabled: bool = True, output_dir: str = "trajectories"):
        self.enabled = enabled
        self.recorder = TrajectoryRecorder(output_dir=output_dir) if enabled else None
        self._current_trajectory = None
    
    def start_recording(self, task: str, provider: str = "unknown", 
                       model: str = "unknown", max_steps: int = 100):
        """开始记录"""
        if not self.enabled or not self.recorder:
            return
        
        self._current_trajectory = self.recorder.start_recording(
            task, provider, model, max_steps
        )
    
    def record_user_message(self, message: str):
        """记录用户消息"""
        if not self.enabled or not self.recorder:
            return
        self.recorder.record_interaction("user_message", {"content": message})
    
    def record_agent_response(self, response: str):
        """记录 Agent 响应"""
        if not self.enabled or not self.recorder:
            return
        self.recorder.record_interaction("agent_response", {"content": response})
    
    def record_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """记录工具调用"""
        if not self.enabled or not self.recorder:
            return ""
        return self.recorder.record_tool_call(tool_name, arguments)
    
    def record_tool_result(self, interaction_id: str, result: Optional[str] = None,
                          error: Optional[str] = None):
        """记录工具结果"""
        if not self.enabled or not self.recorder:
            return
        self.recorder.record_tool_result(interaction_id, result, error)
    
    def record_agent_step(self, action: str, reasoning: Optional[str] = None) -> str:
        """记录 Agent 步骤"""
        if not self.enabled or not self.recorder:
            return ""
        return self.recorder.record_agent_step(action, reasoning)
    
    def save(self) -> Optional[str]:
        """保存轨迹"""
        if not self.enabled or not self.recorder:
            return None
        return self.recorder.save()
    
    def finish(self, success: bool = False, result: Optional[str] = None,
              error: Optional[str] = None) -> str:
        """完成记录"""
        if not self.enabled or not self.recorder:
            return "轨迹记录未启用"
        
        self.recorder.finish_recording(success, result, error)
        filepath = self.recorder.save()
        summary = self.recorder.get_summary()
        
        return f"{summary}\n\n轨迹已保存: {filepath}"
    
    def get_summary(self) -> str:
        """获取摘要"""
        if not self.enabled or not self.recorder:
            return "轨迹记录未启用"
        return self.recorder.get_summary()


class TaskDoneToolManager:
    """任务完成管理器"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.manager = TaskDoneManager() if enabled else None
    
    def start(self, task_description: str, 
             verification_template: Optional[str] = None) -> str:
        """开始任务"""
        if not self.enabled or not self.manager:
            return "任务完成工具未启用"
        return self.manager.start_task(task_description, verification_template)
    
    def verify(self, step_name: str, result: str) -> str:
        """验证步骤"""
        if not self.enabled or not self.manager:
            return "任务完成工具未启用"
        return self.manager.verify_step(step_name, result)
    
    def done(self, summary: str, artifacts: Optional[str] = None,
            test_results: Optional[str] = None, force: bool = False) -> str:
        """完成任务"""
        if not self.enabled or not self.manager:
            return "任务完成工具未启用"
        return self.manager.complete_task(summary, artifacts, test_results, force)
    
    def status(self) -> str:
        """获取状态"""
        if not self.enabled or not self.manager:
            return "任务完成工具未启用"
        return self.manager.get_status()


class AdvancedEditManager:
    """高级编辑管理器"""
    
    def __init__(self, enabled: bool = True, working_dir: str = "."):
        self.enabled = enabled
        self.edit_tool = AdvancedEditTool(working_dir) if enabled else None
    
    def view(self, path: str, view_range: Optional[str] = None) -> str:
        """查看文件"""
        if not self.enabled or not self.edit_tool:
            return "高级编辑工具未启用"
        return self.edit_tool.view_file(path, view_range)
    
    def create(self, path: str, content: str) -> str:
        """创建文件"""
        if not self.enabled or not self.edit_tool:
            return "高级编辑工具未启用"
        return self.edit_tool.create_file(path, content)
    
    def str_replace(self, path: str, old_str: str, new_str: str) -> str:
        """字符串替换"""
        if not self.enabled or not self.edit_tool:
            return "高级编辑工具未启用"
        return self.edit_tool.str_replace(path, old_str, new_str)
    
    def insert(self, path: str, insert_line: int, new_str: str) -> str:
        """插入内容"""
        if not self.enabled or not self.edit_tool:
            return "高级编辑工具未启用"
        return self.edit_tool.insert(path, insert_line, new_str)


class AgentFeatures:
    """
    Agent 功能整合类
    
    统一管理所有增强功能
    """
    
    def __init__(self, config: Optional[AgentFeaturesConfig] = None):
        self.config = config or AgentFeaturesConfig()
        
        # 初始化各个管理器
        self.lakeview = LakeviewManager(self.config.lakeview_enabled)
        self.sequential_thinking = SequentialThinkingManager(
            self.config.sequential_thinking_enabled,
            self.config.max_thoughts
        )
        self.trajectory = TrajectoryManager(
            self.config.trajectory_enabled,
            self.config.trajectory_output_dir
        )
        self.task_done = TaskDoneToolManager(self.config.task_done_enabled)
        self.advanced_edit = AdvancedEditManager(
            self.config.advanced_edit_enabled,
            self.config.working_dir
        )
    
    def enable_all(self):
        """启用所有功能"""
        self.config.lakeview_enabled = True
        self.config.sequential_thinking_enabled = True
        self.config.trajectory_enabled = True
        self.config.task_done_enabled = True
        self.config.advanced_edit_enabled = True
        
        # 重新初始化
        self.lakeview = LakeviewManager(True)
        self.sequential_thinking = SequentialThinkingManager(True, self.config.max_thoughts)
        self.trajectory = TrajectoryManager(True, self.config.trajectory_output_dir)
        self.task_done = TaskDoneToolManager(True)
        self.advanced_edit = AdvancedEditManager(True, self.config.working_dir)
    
    def disable_all(self):
        """禁用所有功能"""
        self.config.lakeview_enabled = False
        self.config.sequential_thinking_enabled = False
        self.config.trajectory_enabled = False
        self.config.task_done_enabled = False
        self.config.advanced_edit_enabled = False
        
        # 重新初始化
        self.lakeview = LakeviewManager(False)
        self.sequential_thinking = SequentialThinkingManager(False)
        self.trajectory = TrajectoryManager(False)
        self.task_done = TaskDoneToolManager(False)
        self.advanced_edit = AdvancedEditManager(False)
    
    def get_summary(self) -> str:
        """获取所有功能的摘要"""
        summaries = [
            "=== Agent Features Summary ===",
            f"Lakeview: {'enabled' if self.config.lakeview_enabled else 'disabled'}",
            f"Sequential Thinking: {'enabled' if self.config.sequential_thinking_enabled else 'disabled'}",
            f"Trajectory: {'enabled' if self.config.trajectory_enabled else 'disabled'}",
            f"Task Done: {'enabled' if self.config.task_done_enabled else 'disabled'}",
            f"Advanced Edit: {'enabled' if self.config.advanced_edit_enabled else 'disabled'}",
        ]
        return "\n".join(summaries)
