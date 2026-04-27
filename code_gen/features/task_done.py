"""
Task Done Tool - 任务完成标记工具

功能：明确标记任务完成，强制要求验证后才能调用
防止 AI 过早结束任务
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import json


class VerificationStatus(str, Enum):
    """验证状态"""
    UNVERIFIED = "unverified"       # 未验证
    PARTIAL = "partial"             # 部分验证
    VERIFIED = "verified"           # 已验证
    FAILED = "failed"               # 验证失败


class CompletionStatus(str, Enum):
    """完成状态"""
    IN_PROGRESS = "in_progress"     # 进行中
    READY_TO_COMPLETE = "ready"     # 准备完成
    COMPLETED = "completed"         # 已完成
    REJECTED = "rejected"           # 被拒绝


@dataclass
class VerificationStep:
    """验证步骤"""
    step_name: str                  # 步骤名称
    description: str                # 描述
    status: VerificationStatus      # 状态
    result: Optional[str] = None    # 结果
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_name": self.step_name,
            "description": self.description,
            "status": self.status.value,
            "result": self.result,
            "timestamp": self.timestamp
        }


@dataclass
class TaskCompletion:
    """任务完成记录"""
    task_id: str
    task_description: str
    completion_status: CompletionStatus = CompletionStatus.IN_PROGRESS
    
    # 验证相关
    verification_steps: List[VerificationStep] = field(default_factory=list)
    verification_required: bool = True  # 是否需要验证
    
    # 完成信息
    summary: Optional[str] = None       # 完成摘要
    artifacts: List[str] = field(default_factory=list)  # 生成的文件/产物
    test_results: Optional[str] = None  # 测试结果
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "completion_status": self.completion_status.value,
            "verification_steps": [s.to_dict() for s in self.verification_steps],
            "verification_required": self.verification_required,
            "summary": self.summary,
            "artifacts": self.artifacts,
            "test_results": self.test_results,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }


class TaskDoneManager:
    """任务完成管理器"""
    
    # 预定义的验证步骤模板
    VERIFICATION_TEMPLATES = {
        "code_fix": [
            VerificationStep("reproduce_bug", "复现原始 bug", VerificationStatus.UNVERIFIED),
            VerificationStep("apply_fix", "应用修复", VerificationStatus.UNVERIFIED),
            VerificationStep("test_fix", "测试修复是否有效", VerificationStatus.UNVERIFIED),
            VerificationStep("check_regression", "检查是否引入新问题", VerificationStatus.UNVERIFIED),
        ],
        "feature_implementation": [
            VerificationStep("implement_feature", "实现功能", VerificationStatus.UNVERIFIED),
            VerificationStep("test_feature", "测试功能", VerificationStatus.UNVERIFIED),
            VerificationStep("check_integration", "检查集成", VerificationStatus.UNVERIFIED),
        ],
        "refactoring": [
            VerificationStep("refactor_code", "重构代码", VerificationStatus.UNVERIFIED),
            VerificationStep("run_tests", "运行测试", VerificationStatus.UNVERIFIED),
            VerificationStep("check_behavior", "检查行为一致性", VerificationStatus.UNVERIFIED),
        ],
        "documentation": [
            VerificationStep("write_docs", "编写文档", VerificationStatus.UNVERIFIED),
            VerificationStep("review_docs", "审查文档", VerificationStatus.UNVERIFIED),
        ]
    }
    
    def __init__(self):
        self.tasks: Dict[str, TaskCompletion] = {}
        self.current_task: Optional[TaskCompletion] = None
        self._on_complete_callbacks: List[Callable[[TaskCompletion], None]] = []
    
    def start_task(self, task_id: str, task_description: str,
                  verification_template: Optional[str] = None,
                  custom_verifications: Optional[List[VerificationStep]] = None,
                  verification_required: bool = True) -> TaskCompletion:
        """开始一个任务"""
        task = TaskCompletion(
            task_id=task_id,
            task_description=task_description,
            verification_required=verification_required
        )
        
        # 添加验证步骤
        if custom_verifications:
            task.verification_steps = custom_verifications
        elif verification_template and verification_template in self.VERIFICATION_TEMPLATES:
            task.verification_steps = [
                VerificationStep(v.step_name, v.description, v.status)
                for v in self.VERIFICATION_TEMPLATES[verification_template]
            ]
        
        self.tasks[task_id] = task
        self.current_task = task
        return task
    
    def add_verification_step(self, step_name: str, description: str,
                             task_id: Optional[str] = None) -> VerificationStep:
        """添加验证步骤"""
        task = self._get_task(task_id)
        
        step = VerificationStep(
            step_name=step_name,
            description=description,
            status=VerificationStatus.UNVERIFIED
        )
        task.verification_steps.append(step)
        return step
    
    def mark_step_complete(self, step_name: str, result: Optional[str] = None,
                          status: VerificationStatus = VerificationStatus.VERIFIED,
                          task_id: Optional[str] = None):
        """标记验证步骤完成"""
        task = self._get_task(task_id)
        
        for step in task.verification_steps:
            if step.step_name == step_name:
                step.status = status
                step.result = result
                step.timestamp = datetime.now().isoformat()
                break
    
    def can_complete(self, task_id: Optional[str] = None) -> tuple[bool, str]:
        """检查是否可以完成任务"""
        task = self._get_task(task_id)
        
        if not task.verification_required:
            return True, "验证已跳过"
        
        if not task.verification_steps:
            return True, "没有验证步骤"
        
        unverified = [s for s in task.verification_steps 
                     if s.status == VerificationStatus.UNVERIFIED]
        
        if unverified:
            steps_str = ", ".join([s.step_name for s in unverified])
            return False, f"还有未完成的验证步骤: {steps_str}"
        
        failed = [s for s in task.verification_steps 
                 if s.status == VerificationStatus.FAILED]
        
        if failed:
            steps_str = ", ".join([s.step_name for s in failed])
            return False, f"有验证失败的步骤: {steps_str}"
        
        return True, "所有验证步骤已完成"
    
    def complete_task(self, summary: str, artifacts: Optional[List[str]] = None,
                     test_results: Optional[str] = None,
                     task_id: Optional[str] = None,
                     force: bool = False) -> tuple[bool, str]:
        """完成任务"""
        task = self._get_task(task_id)
        
        # 检查是否可以完成
        if not force:
            can_complete, message = self.can_complete(task_id)
            if not can_complete:
                return False, f"❌ 无法完成任务: {message}\n\n请完成所有验证步骤后再调用 complete_task，或使用 force=True 强制完成。"
        
        # 完成任务
        task.completion_status = CompletionStatus.COMPLETED
        task.summary = summary
        task.artifacts = artifacts or []
        task.test_results = test_results
        task.completed_at = datetime.now().isoformat()
        
        # 触发回调
        for callback in self._on_complete_callbacks:
            try:
                callback(task)
            except Exception:
                pass
        
        return True, f"✅ 任务完成: {task.task_id}\n摘要: {summary}"
    
    def get_verification_status(self, task_id: Optional[str] = None) -> str:
        """获取验证状态摘要"""
        task = self._get_task(task_id)
        
        lines = [f"📋 任务: {task.task_description}", ""]
        
        if not task.verification_steps:
            lines.append("没有验证步骤")
            return "\n".join(lines)
        
        lines.append("验证步骤:")
        for step in task.verification_steps:
            emoji = {
                VerificationStatus.UNVERIFIED: "⬜",
                VerificationStatus.PARTIAL: "🟡",
                VerificationStatus.VERIFIED: "✅",
                VerificationStatus.FAILED: "❌"
            }.get(step.status, "⬜")
            
            lines.append(f"  {emoji} {step.description}")
            if step.result:
                lines.append(f"     结果: {step.result}")
        
        can_complete, message = self.can_complete(task_id)
        lines.append(f"\n{'✅' if can_complete else '❌'} {message}")
        
        return "\n".join(lines)
    
    def get_task_summary(self, task_id: Optional[str] = None) -> str:
        """获取任务摘要"""
        task = self._get_task(task_id)
        
        lines = [
            f"📝 任务: {task.task_description}",
            f"状态: {task.completion_status.value}",
            f"验证: {'需要' if task.verification_required else '不需要'}",
        ]
        
        if task.summary:
            lines.append(f"\n摘要: {task.summary}")
        
        if task.artifacts:
            lines.append(f"\n产物: {', '.join(task.artifacts)}")
        
        if task.test_results:
            lines.append(f"\n测试结果:\n{task.test_results}")
        
        return "\n".join(lines)
    
    def on_complete(self, callback: Callable[[TaskCompletion], None]):
        """注册完成回调"""
        self._on_complete_callbacks.append(callback)
    
    def _get_task(self, task_id: Optional[str] = None) -> TaskCompletion:
        """获取任务"""
        if task_id:
            if task_id not in self.tasks:
                raise ValueError(f"Task not found: {task_id}")
            return self.tasks[task_id]
        
        if self.current_task is None:
            raise ValueError("No active task")
        
        return self.current_task
    
    def save_task(self, filepath: str, task_id: Optional[str] = None):
        """保存任务"""
        task = self._get_task(task_id)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)


class TaskDoneTool:
    """Task Done Tool - 供 Agent 直接使用"""
    
    def __init__(self):
        self.manager = TaskDoneManager()
        self._current_task_id: Optional[str] = None
    
    def start(self, task_description: str, 
             verification_template: Optional[str] = None,
             verification_required: bool = True) -> str:
        """开始任务"""
        import uuid
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        self.manager.start_task(
            task_id=task_id,
            task_description=task_description,
            verification_template=verification_template,
            verification_required=verification_required
        )
        self._current_task_id = task_id
        
        result = f"开始任务: {task_description}\n任务ID: {task_id}"
        if verification_required:
            result += "\n\n请完成以下验证步骤后再标记完成:"
            result += f"\n{self.manager.get_verification_status(task_id)}"
        
        return result
    
    def verify(self, step_name: str, result: str, 
              status: str = "verified") -> str:
        """验证步骤"""
        if not self._current_task_id:
            return "错误: 没有活动的任务，请先调用 start()"
        
        try:
            status_enum = VerificationStatus(status)
        except ValueError:
            status_enum = VerificationStatus.VERIFIED
        
        self.manager.mark_step_complete(
            step_name=step_name,
            result=result,
            status=status_enum,
            task_id=self._current_task_id
        )
        
        return f"步骤 '{step_name}' 已标记为 {status}\n\n{self.manager.get_verification_status(self._current_task_id)}"
    
    def done(self, summary: str, artifacts: Optional[str] = None,
            test_results: Optional[str] = None, force: bool = False) -> str:
        """完成任务"""
        if not self._current_task_id:
            return "错误: 没有活动的任务，请先调用 start()"
        
        artifact_list = artifacts.split(",") if artifacts else None
        
        success, message = self.manager.complete_task(
            summary=summary,
            artifacts=artifact_list,
            test_results=test_results,
            task_id=self._current_task_id,
            force=force
        )
        
        if success:
            self._current_task_id = None
        
        return message
    
    def status(self) -> str:
        """获取状态"""
        if not self._current_task_id:
            return "没有活动的任务"
        
        return self.manager.get_verification_status(self._current_task_id)


# 便捷函数
def create_task_done_tool() -> TaskDoneTool:
    """创建任务完成工具"""
    return TaskDoneTool()
