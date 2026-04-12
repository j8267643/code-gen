"""
Workflow State Manager
支持工作流的断点续跑和状态恢复
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
import json
import hashlib


@dataclass
class StepState:
    """步骤执行状态"""
    step_id: str
    name: str
    status: str = "pending"  # pending, running, completed, failed, skipped
    agent_role: str = ""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    output: str = ""
    error: str = ""
    retry_count: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "StepState":
        return cls(**data)


@dataclass
class WorkflowState:
    """工作流状态"""
    workflow_name: str
    goal: str = ""
    status: str = "pending"  # pending, planning, running, paused, completed, failed
    current_step_id: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    step_states: Dict[str, StepState] = field(default_factory=dict)
    plan: Optional[Dict] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "workflow_name": self.workflow_name,
            "goal": self.goal,
            "status": self.status,
            "current_step_id": self.current_step_id,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "step_states": {k: v.to_dict() for k, v in self.step_states.items()},
            "plan": self.plan,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "WorkflowState":
        state = cls(
            workflow_name=data["workflow_name"],
            goal=data.get("goal", ""),
            status=data.get("status", "pending"),
            current_step_id=data.get("current_step_id"),
            completed_steps=data.get("completed_steps", []),
            failed_steps=data.get("failed_steps", []),
            plan=data.get("plan"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            metadata=data.get("metadata", {})
        )
        state.step_states = {
            k: StepState.from_dict(v) 
            for k, v in data.get("step_states", {}).items()
        }
        return state
    
    def get_pending_steps(self) -> List[str]:
        """获取待执行的步骤"""
        all_steps = list(self.step_states.keys())
        pending = []
        for step_id in all_steps:
            if step_id not in self.completed_steps and step_id not in self.failed_steps:
                step = self.step_states.get(step_id)
                if step and step.status in ["pending", "failed"]:
                    pending.append(step_id)
        return pending
    
    def can_retry(self, step_id: str, max_retries: int = 3) -> bool:
        """检查步骤是否可以重试"""
        step = self.step_states.get(step_id)
        if not step:
            return False
        return step.status == "failed" and step.retry_count < max_retries


class WorkflowStateManager:
    """工作流状态管理器"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.state_dir = work_dir / ".workflow_states"
        self.state_dir.mkdir(exist_ok=True)
    
    def _get_state_file(self, workflow_name: str) -> Path:
        """获取状态文件路径"""
        # 使用工作流名称的哈希作为文件名
        name_hash = hashlib.md5(workflow_name.encode()).hexdigest()[:8]
        return self.state_dir / f"{workflow_name}_{name_hash}.json"
    
    def save_state(self, state: WorkflowState):
        """保存工作流状态"""
        state_file = self._get_state_file(state.workflow_name)
        state.end_time = datetime.now().isoformat()
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        
        print(f"💾 工作流状态已保存: {state_file}")
    
    def load_state(self, workflow_name: str) -> Optional[WorkflowState]:
        """加载工作流状态"""
        state_file = self._get_state_file(workflow_name)
        
        if not state_file.exists():
            return None
        
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return WorkflowState.from_dict(data)
        except Exception as e:
            print(f"⚠️ 加载状态失败: {e}")
            return None
    
    def has_existing_state(self, workflow_name: str) -> bool:
        """检查是否存在现有状态"""
        state_file = self._get_state_file(workflow_name)
        return state_file.exists()
    
    def delete_state(self, workflow_name: str):
        """删除工作流状态"""
        state_file = self._get_state_file(workflow_name)
        if state_file.exists():
            state_file.unlink()
            print(f"🗑️ 工作流状态已删除: {state_file}")
    
    def list_saved_states(self) -> List[Dict]:
        """列出所有保存的状态"""
        states = []
        for state_file in self.state_dir.glob("*.json"):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                states.append({
                    "workflow_name": data.get("workflow_name"),
                    "status": data.get("status"),
                    "start_time": data.get("start_time"),
                    "file": str(state_file)
                })
            except:
                pass
        return states


# 全局状态管理器实例
_state_manager: Optional[WorkflowStateManager] = None


def get_state_manager(work_dir: Path) -> WorkflowStateManager:
    """获取或创建全局状态管理器"""
    global _state_manager
    if _state_manager is None or _state_manager.work_dir != work_dir:
        _state_manager = WorkflowStateManager(work_dir)
    return _state_manager
