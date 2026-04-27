"""
Task management system for CodeGen - Similar to Claude's TodoWrite workflow
"""
import json
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    id: str
    content: str
    status: TaskStatus
    priority: str  # "high", "medium", "low"
    dependencies: List[str] = None  # List of task IDs that must be completed first
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "status": self.status.value,
            "priority": self.priority,
            "dependencies": self.dependencies
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data["id"],
            content=data["content"],
            status=TaskStatus(data["status"]),
            priority=data["priority"],
            dependencies=data.get("dependencies", [])
        )


class TaskManager:
    """
    Manages tasks for complex multi-step operations
    Similar to how Claude uses TodoWrite for task tracking
    """
    
    def __init__(self):
        self.tasks: List[Task] = []
        self.current_task_index: int = -1
        self.on_task_status_change: Optional[Callable[[Task], None]] = None
    
    def create_plan(self, task_descriptions: List[Dict[str, str]]) -> List[Task]:
        """
        Create a task plan from descriptions
        
        Args:
            task_descriptions: List of dicts with "content" and optionally "priority", "dependencies"
        
        Returns:
            List of created tasks
        """
        self.tasks = []
        for i, desc in enumerate(task_descriptions):
            task = Task(
                id=f"task_{i+1}",
                content=desc["content"],
                status=TaskStatus.PENDING,
                priority=desc.get("priority", "medium"),
                dependencies=desc.get("dependencies", [])
            )
            self.tasks.append(task)
        return self.tasks
    
    def get_next_task(self) -> Optional[Task]:
        """Get the next pending task that has all dependencies completed"""
        for task in self.tasks:
            if task.status == TaskStatus.PENDING:
                # Check if all dependencies are completed
                deps_completed = all(
                    self.get_task_by_id(dep_id).status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                )
                if deps_completed:
                    return task
        return None
    
    def start_task(self, task_id: str) -> bool:
        """Mark a task as in_progress"""
        task = self.get_task_by_id(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.IN_PROGRESS
            self.current_task_index = self.tasks.index(task)
            if self.on_task_status_change:
                self.on_task_status_change(task)
            return True
        return False
    
    def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed"""
        task = self.get_task_by_id(task_id)
        if task and task.status == TaskStatus.IN_PROGRESS:
            task.status = TaskStatus.COMPLETED
            if self.on_task_status_change:
                self.on_task_status_change(task)
            return True
        return False
    
    def fail_task(self, task_id: str) -> bool:
        """Mark a task as failed"""
        task = self.get_task_by_id(task_id)
        if task:
            task.status = TaskStatus.FAILED
            if self.on_task_status_change:
                self.on_task_status_change(task)
            return True
        return False
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get a task by its ID"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_current_task(self) -> Optional[Task]:
        """Get the currently active task"""
        if 0 <= self.current_task_index < len(self.tasks):
            return self.tasks[self.current_task_index]
        return None
    
    def is_plan_complete(self) -> bool:
        """Check if all tasks are completed"""
        return all(task.status == TaskStatus.COMPLETED for task in self.tasks)
    
    def get_progress(self) -> Dict[str, int]:
        """Get completion statistics"""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        in_progress = sum(1 for t in self.tasks if t.status == TaskStatus.IN_PROGRESS)
        pending = sum(1 for t in self.tasks if t.status == TaskStatus.PENDING)
        failed = sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)
        
        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "failed": failed,
            "percentage": (completed / total * 100) if total > 0 else 0
        }
    
    def to_json(self) -> str:
        """Serialize tasks to JSON"""
        return json.dumps([task.to_dict() for task in self.tasks], indent=2)
    
    def from_json(self, json_str: str):
        """Load tasks from JSON"""
        data = json.loads(json_str)
        self.tasks = [Task.from_dict(t) for t in data]
    
    def clear(self):
        """Clear all tasks"""
        self.tasks = []
        self.current_task_index = -1
    
    def format_plan(self) -> str:
        """Format the task plan for display"""
        lines = ["📋 Task Plan:"]
        for task in self.tasks:
            status_icon = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌"
            }.get(task.status, "⏳")
            
            priority_icon = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢"
            }.get(task.priority, "⚪")
            
            lines.append(f"  {status_icon} {priority_icon} {task.id}: {task.content}")
        
        progress = self.get_progress()
        lines.append(f"\n📊 Progress: {progress['completed']}/{progress['total']} ({progress['percentage']:.0f}%)")
        
        return "\n".join(lines)


# Global task manager instance
task_manager = TaskManager()
