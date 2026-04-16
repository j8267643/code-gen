"""Experience Data Model"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import json


class ExperienceType(Enum):
    """经验类型"""
    CODE_GENERATION = "code_generation"      # 代码生成
    CODE_REVIEW = "code_review"              # 代码审查
    BUG_FIX = "bug_fix"                      # Bug 修复
    REFACTORING = "refactoring"              # 代码重构
    ARCHITECTURE = "architecture"            # 架构设计
    DEBUGGING = "debugging"                  # 调试
    TESTING = "testing"                      # 测试
    OPTIMIZATION = "optimization"            # 性能优化
    GENERAL = "general"                      # 通用经验


class ExperienceStatus(Enum):
    """经验状态"""
    PENDING = "pending"                      # 待评估
    VALIDATED = "validated"                  # 已验证
    REJECTED = "rejected"                    # 已拒绝
    DEPRECATED = "deprecated"                # 已弃用


@dataclass
class Experience:
    """经验条目
    
    记录一次成功的执行经验，用于未来复用
    """
    # 基本信息
    task_description: str                    # 任务描述
    experience_type: ExperienceType          # 经验类型
    
    # 输入输出
    input_context: Dict[str, Any] = field(default_factory=dict)   # 输入上下文
    output_result: Dict[str, Any] = field(default_factory=dict)   # 输出结果
    
    # 执行细节
    steps_taken: List[Dict[str, Any]] = field(default_factory=list)  # 执行步骤
    code_snippets: List[str] = field(default_factory=list)           # 代码片段
    lessons_learned: List[str] = field(default_factory=list)         # 学到的教训
    
    # 元数据
    tags: List[str] = field(default_factory=list)                    # 标签
    related_files: List[str] = field(default_factory=list)           # 相关文件
    dependencies: List[str] = field(default_factory=list)            # 依赖
    
    # 评估信息
    status: ExperienceStatus = ExperienceStatus.PENDING
    score: float = 0.0                       # 质量评分 (0-1)
    usage_count: int = 0                     # 使用次数
    success_count: int = 0                   # 成功次数
    
    # 来源信息
    source_sop: Optional[str] = None         # 来源 SOP
    source_agent: Optional[str] = None       # 来源 Agent
    source_project: Optional[str] = None     # 来源项目
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None
    
    # ID
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count
    
    @property
    def embedding_text(self) -> str:
        """用于嵌入的文本"""
        return f"""
Task: {self.task_description}
Type: {self.experience_type.value}
Steps: {' '.join([s.get('action', '') for s in self.steps_taken])}
Lessons: {' '.join(self.lessons_learned)}
Tags: {' '.join(self.tags)}
""".strip()
    
    def compute_hash(self) -> str:
        """计算经验哈希"""
        content = json.dumps({
            "task": self.task_description,
            "type": self.experience_type.value,
            "input": self.input_context,
            "output": self.output_result,
        }, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def validate(self) -> bool:
        """验证经验"""
        # 基本验证
        if not self.task_description:
            return False
        if not self.input_context:
            return False
        if not self.output_result:
            return False
        
        self.status = ExperienceStatus.VALIDATED
        self.updated_at = datetime.now()
        return True
    
    def mark_used(self, success: bool = True):
        """标记为已使用"""
        self.usage_count += 1
        if success:
            self.success_count += 1
        self.last_used_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "task_description": self.task_description,
            "experience_type": self.experience_type.value,
            "input_context": self.input_context,
            "output_result": self.output_result,
            "steps_taken": self.steps_taken,
            "code_snippets": self.code_snippets,
            "lessons_learned": self.lessons_learned,
            "tags": self.tags,
            "related_files": self.related_files,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "score": self.score,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "success_rate": self.success_rate,
            "source_sop": self.source_sop,
            "source_agent": self.source_agent,
            "source_project": self.source_project,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Experience:
        """从字典创建"""
        return cls(
            id=data.get("id"),
            task_description=data["task_description"],
            experience_type=ExperienceType(data.get("experience_type", "general")),
            input_context=data.get("input_context", {}),
            output_result=data.get("output_result", {}),
            steps_taken=data.get("steps_taken", []),
            code_snippets=data.get("code_snippets", []),
            lessons_learned=data.get("lessons_learned", []),
            tags=data.get("tags", []),
            related_files=data.get("related_files", []),
            dependencies=data.get("dependencies", []),
            status=ExperienceStatus(data.get("status", "pending")),
            score=data.get("score", 0.0),
            usage_count=data.get("usage_count", 0),
            success_count=data.get("success_count", 0),
            source_sop=data.get("source_sop"),
            source_agent=data.get("source_agent"),
            source_project=data.get("source_project"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            last_used_at=datetime.fromisoformat(data["last_used_at"]) if data.get("last_used_at") else None,
        )
    
    @classmethod
    def from_execution(
        cls,
        task_description: str,
        experience_type: ExperienceType,
        context: Dict[str, Any],
        result: Dict[str, Any],
        steps: List[Dict[str, Any]],
        lessons: List[str] = None,
        **kwargs
    ) -> Experience:
        """从执行记录创建经验"""
        return cls(
            task_description=task_description,
            experience_type=experience_type,
            input_context=context,
            output_result=result,
            steps_taken=steps,
            lessons_learned=lessons or [],
            **kwargs
        )
