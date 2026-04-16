"""Experience Retriever - 经验检索器"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .experience import Experience, ExperienceType
from .pool import ExperiencePool
from .scorer import ExperienceScorer, ContextualScorer


@dataclass
class RetrievalResult:
    """检索结果"""
    experience: Experience
    score: float
    relevance: float
    context_match: float


class ExperienceRetriever:
    """经验检索器
    
    根据查询检索相关经验
    """
    
    def __init__(
        self,
        pool: ExperiencePool,
        scorer: Optional[ExperienceScorer] = None,
    ):
        self.pool = pool
        self.scorer = scorer or ContextualScorer()
    
    def retrieve(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        exp_type: Optional[ExperienceType] = None,
        limit: int = 5,
        min_score: float = 0.3,
    ) -> List[RetrievalResult]:
        """检索经验
        
        Args:
            query: 查询字符串
            context: 上下文信息
            exp_type: 经验类型过滤
            limit: 返回数量限制
            min_score: 最低评分
        
        Returns:
            检索结果列表
        """
        # 初步筛选
        candidates = self.pool.search(
            query=query,
            exp_type=exp_type,
            limit=limit * 3,  # 获取更多候选
        )
        
        # 评分和排序
        results = []
        for exp in candidates:
            score = self.scorer.score(exp, context)
            if score >= min_score:
                relevance = self._calculate_relevance(exp, query)
                context_match = self._calculate_context_match(exp, context)
                results.append(RetrievalResult(
                    experience=exp,
                    score=score,
                    relevance=relevance,
                    context_match=context_match,
                ))
        
        # 综合排序
        results.sort(
            key=lambda r: r.score * 0.5 + r.relevance * 0.3 + r.context_match * 0.2,
            reverse=True,
        )
        
        return results[:limit]
    
    def retrieve_for_task(
        self,
        task_description: str,
        task_type: ExperienceType,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 3,
    ) -> List[RetrievalResult]:
        """为任务检索经验"""
        # 构建上下文
        retrieval_context = context or {}
        retrieval_context["task"] = task_description
        
        return self.retrieve(
            query=task_description,
            context=retrieval_context,
            exp_type=task_type,
            limit=limit,
            min_score=0.2,  # 任务检索使用较低阈值
        )
    
    def retrieve_similar_cases(
        self,
        experience: Experience,
        limit: int = 3,
    ) -> List[RetrievalResult]:
        """检索相似案例"""
        similar = self.pool.get_similar_experiences(experience, limit=limit * 2)
        
        results = []
        for exp in similar:
            score = self.scorer.score(exp)
            relevance = self._calculate_similarity(exp, experience)
            results.append(RetrievalResult(
                experience=exp,
                score=score,
                relevance=relevance,
                context_match=1.0 if exp.source_project == experience.source_project else 0.5,
            ))
        
        results.sort(key=lambda r: r.relevance, reverse=True)
        return results[:limit]
    
    def get_best_practices(
        self,
        exp_type: ExperienceType,
        limit: int = 5,
    ) -> List[RetrievalResult]:
        """获取最佳实践"""
        top_exp = self.pool.get_top_experiences(
            exp_type=exp_type,
            limit=limit,
            min_usage=3,  # 至少使用3次
        )
        
        results = []
        for exp in top_exp:
            score = self.scorer.score(exp)
            results.append(RetrievalResult(
                experience=exp,
                score=score,
                relevance=1.0,
                context_match=1.0,
            ))
        
        return results
    
    def _calculate_relevance(self, exp: Experience, query: str) -> float:
        """计算相关性"""
        query_words = set(query.lower().split())
        if not query_words:
            return 0.0
        
        # 任务描述匹配
        task_words = set(exp.task_description.lower().split())
        task_match = len(query_words & task_words) / len(query_words)
        
        # 标签匹配
        tag_match = 0.0
        for tag in exp.tags:
            tag_words = set(tag.lower().split())
            tag_match = max(tag_match, len(query_words & tag_words) / len(query_words))
        
        # 教训匹配
        lesson_match = 0.0
        for lesson in exp.lessons_learned:
            lesson_words = set(lesson.lower().split())
            lesson_match = max(lesson_match, len(query_words & lesson_words) / len(query_words))
        
        return max(task_match, tag_match * 0.8, lesson_match * 0.6)
    
    def _calculate_context_match(self, exp: Experience, context: Optional[Dict]) -> float:
        """计算上下文匹配度"""
        if not context:
            return 0.5
        
        matches = 0
        total = 0
        
        # 项目匹配
        if context.get("project"):
            total += 1
            if exp.source_project == context["project"]:
                matches += 1
        
        # 文件匹配
        if context.get("files"):
            total += 1
            if exp.related_files:
                common = set(context["files"]) & set(exp.related_files)
                if common:
                    matches += len(common) / len(context["files"])
        
        # Agent 匹配
        if context.get("agent"):
            total += 1
            if exp.source_agent == context["agent"]:
                matches += 1
        
        return matches / total if total > 0 else 0.5
    
    def _calculate_similarity(self, exp1: Experience, exp2: Experience) -> float:
        """计算两个经验的相似度"""
        scores = []
        
        # 类型相同
        if exp1.experience_type == exp2.experience_type:
            scores.append(1.0)
        
        # 任务描述相似度
        words1 = set(exp1.task_description.lower().split())
        words2 = set(exp2.task_description.lower().split())
        if words1 and words2:
            jaccard = len(words1 & words2) / len(words1 | words2)
            scores.append(jaccard)
        
        # 标签相似度
        if exp1.tags and exp2.tags:
            common_tags = set(exp1.tags) & set(exp2.tags)
            tag_sim = len(common_tags) / max(len(exp1.tags), len(exp2.tags))
            scores.append(tag_sim)
        
        # 项目相同
        if exp1.source_project and exp2.source_project:
            if exp1.source_project == exp2.source_project:
                scores.append(1.0)
        
        return sum(scores) / len(scores) if scores else 0.0


class ExperienceAugmenter:
    """经验增强器
    
    使用检索到的经验增强提示
    """
    
    def __init__(self, retriever: ExperienceRetriever):
        self.retriever = retriever
    
    def augment_prompt(
        self,
        base_prompt: str,
        task_description: str,
        task_type: ExperienceType,
        context: Optional[Dict[str, Any]] = None,
        max_experiences: int = 3,
    ) -> str:
        """增强提示"""
        # 检索相关经验
        results = self.retriever.retrieve_for_task(
            task_description=task_description,
            task_type=task_type,
            context=context,
            limit=max_experiences,
        )
        
        if not results:
            return base_prompt
        
        # 构建经验提示
        exp_sections = []
        for i, result in enumerate(results, 1):
            exp = result.experience
            section = f"""
### 经验案例 {i} (相关度: {result.relevance:.2f})
**任务**: {exp.task_description}
**关键步骤**:
"""
            for step in exp.steps_taken[:5]:  # 最多5个步骤
                section += f"- {step.get('action', 'unknown')}: {step.get('description', '')}\n"
            
            if exp.lessons_learned:
                section += "**经验教训**:\n"
                for lesson in exp.lessons_learned[:3]:
                    section += f"- {lesson}\n"
            
            if exp.code_snippets:
                section += "**参考代码**:\n```\n"
                section += exp.code_snippets[0][:500]  # 限制长度
                section += "\n```\n"
            
            exp_sections.append(section)
        
        # 组合提示
        augmented = f"""{base_prompt}

## 相关经验参考
以下是从历史执行中提取的相关经验，供你参考：
{''.join(exp_sections)}

请基于以上经验，结合当前任务要求，给出最佳解决方案。
"""
        return augmented
    
    def augment_with_best_practices(
        self,
        base_prompt: str,
        exp_type: ExperienceType,
        max_practices: int = 3,
    ) -> str:
        """使用最佳实践增强提示"""
        results = self.retriever.get_best_practices(exp_type, limit=max_practices)
        
        if not results:
            return base_prompt
        
        practices = []
        for i, result in enumerate(results, 1):
            exp = result.experience
            practice = f"""
### 最佳实践 {i} (评分: {result.score:.2f}, 使用{exp.usage_count}次)
**场景**: {exp.task_description}
**成功要点**:
"""
            for lesson in exp.lessons_learned[:3]:
                practice += f"- {lesson}\n"
            
            practices.append(practice)
        
        return f"""{base_prompt}

## 最佳实践指南
{''.join(practices)}

请遵循以上最佳实践，确保高质量的输出。
"""
