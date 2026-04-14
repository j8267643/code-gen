"""
AutoDev Models - 数据模型定义

避免循环导入，将数据模型集中定义
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PRDData:
    """PRD 数据结构"""
    project: str
    branch_name: str
    description: str
    user_stories: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "PRDData":
        return cls(
            project=data.get("project", "Unknown"),
            branch_name=data.get("branchName", "main"),
            description=data.get("description", ""),
            user_stories=data.get("userStories", []),
            metadata=data.get("metadata", {})
        )
    
    def to_json(self) -> Dict[str, Any]:
        return {
            "project": self.project,
            "branchName": self.branch_name,
            "description": self.description,
            "userStories": self.user_stories,
            "metadata": self.metadata
        }


@dataclass
class UserStory:
    """用户故事"""
    id: str
    title: str
    description: str
    acceptance_criteria: List[str] = field(default_factory=list)
    priority: int = 1
    passes: bool = False
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "acceptanceCriteria": self.acceptance_criteria,
            "priority": self.priority,
            "passes": self.passes,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserStory":
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            acceptance_criteria=data.get("acceptanceCriteria", []),
            priority=data.get("priority", 1),
            passes=data.get("passes", False),
            notes=data.get("notes", "")
        )


@dataclass
class ExecutionResult:
    """执行结果"""
    story_id: str
    success: bool
    output: str
    error: Optional[str] = None
    files_changed: List[str] = field(default_factory=list)
    learnings: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_id": self.story_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "files_changed": self.files_changed,
            "learnings": self.learnings,
            "execution_time": self.execution_time
        }
