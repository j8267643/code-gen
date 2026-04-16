"""Experience Scorer - 经验评分器"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from .experience import Experience


class ExperienceScorer(ABC):
    """经验评分器基类"""
    
    @abstractmethod
    def score(self, experience: Experience, context: Dict[str, Any] = None) -> float:
        """评分经验
        
        Args:
            experience: 要评分的经验
            context: 可选的上下文信息
        
        Returns:
            评分 (0-1)
        """
        pass


class SimpleScorer(ExperienceScorer):
    """简单评分器"""
    
    def __init__(
        self,
        success_weight: float = 0.4,
        usage_weight: float = 0.2,
        recency_weight: float = 0.2,
        complexity_weight: float = 0.2,
    ):
        self.success_weight = success_weight
        self.usage_weight = usage_weight
        self.recency_weight = recency_weight
        self.complexity_weight = complexity_weight
    
    def score(self, experience: Experience, context: Dict[str, Any] = None) -> float:
        """评分"""
        from datetime import datetime
        
        # 成功率评分
        success_score = experience.success_rate
        
        # 使用频率评分（归一化）
        usage_score = min(experience.usage_count / 50, 1.0)
        
        # 时效性评分
        recency_score = 0.5
        if experience.last_used_at:
            days_since = (datetime.now() - experience.last_used_at).days
            recency_score = max(0, 1 - days_since / 30)  # 30天内满分
        
        # 复杂度评分（基于步骤数）
        complexity_score = min(len(experience.steps_taken) / 10, 1.0)
        
        # 加权总分
        total_score = (
            success_score * self.success_weight +
            usage_score * self.usage_weight +
            recency_score * self.recency_weight +
            complexity_score * self.complexity_weight
        )
        
        return min(max(total_score, 0.0), 1.0)


class ContextualScorer(ExperienceScorer):
    """上下文感知评分器"""
    
    def __init__(self):
        self.simple_scorer = SimpleScorer()
    
    def score(self, experience: Experience, context: Dict[str, Any] = None) -> float:
        """基于上下文的评分"""
        base_score = self.simple_scorer.score(experience)
        
        if not context:
            return base_score
        
        # 项目匹配度
        project_match = 0.0
        if context.get("project") and experience.source_project:
            if context["project"] == experience.source_project:
                project_match = 0.1
        
        # 文件匹配度
        file_match = 0.0
        if context.get("files") and experience.related_files:
            common_files = set(context["files"]) & set(experience.related_files)
            if common_files:
                file_match = len(common_files) / len(context["files"]) * 0.1
        
        # 任务相似度
        task_similarity = 0.0
        if context.get("task"):
            # 简单的关键词匹配
            task_words = set(context["task"].lower().split())
            exp_words = set(experience.task_description.lower().split())
            if task_words and exp_words:
                common = task_words & exp_words
                task_similarity = len(common) / len(task_words) * 0.1
        
        return min(base_score + project_match + file_match + task_similarity, 1.0)


class FeedbackScorer(ExperienceScorer):
    """基于反馈的评分器"""
    
    def __init__(self):
        self.feedbacks: Dict[str, list] = {}
    
    def add_feedback(self, exp_id: str, rating: float, comment: str = None):
        """添加反馈"""
        if exp_id not in self.feedbacks:
            self.feedbacks[exp_id] = []
        self.feedbacks[exp_id].append({
            "rating": rating,
            "comment": comment,
        })
    
    def score(self, experience: Experience, context: Dict[str, Any] = None) -> float:
        """基于反馈的评分"""
        feedbacks = self.feedbacks.get(experience.id, [])
        
        if not feedbacks:
            # 没有反馈时使用基础评分
            return experience.success_rate
        
        # 计算平均评分
        avg_rating = sum(f["rating"] for f in feedbacks) / len(feedbacks)
        
        # 结合成功率
        combined = (avg_rating + experience.success_rate) / 2
        
        return combined
