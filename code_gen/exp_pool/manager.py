"""Experience Manager - 经验管理器"""

from typing import Dict, List, Optional, Any, TYPE_CHECKING
from datetime import datetime
from pathlib import Path

from .experience import Experience, ExperienceType, ExperienceStatus
from .pool import ExperiencePool
from .scorer import ExperienceScorer, SimpleScorer
from .retriever import ExperienceRetriever, ExperienceAugmenter

if TYPE_CHECKING:
    from ..sop.sop import SOPContext


class ExperienceManager:
    """经验管理器
    
    统一管理经验的收集、评估、检索和应用
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        scorer: Optional[ExperienceScorer] = None,
    ):
        self.pool = ExperiencePool(storage_path)
        self.scorer = scorer or SimpleScorer()
        self.retriever = ExperienceRetriever(self.pool, self.scorer)
        self.augmenter = ExperienceAugmenter(self.retriever)
        
        # 加载已有经验
        self.pool.load()
    
    # ========== 经验收集 ==========
    
    def collect_from_execution(
        self,
        task_description: str,
        task_type: ExperienceType,
        input_context: Dict[str, Any],
        output_result: Dict[str, Any],
        steps: List[Dict[str, Any]],
        success: bool = True,
        lessons: List[str] = None,
        code_snippets: List[str] = None,
        tags: List[str] = None,
        source_sop: Optional[str] = None,
        source_agent: Optional[str] = None,
        source_project: Optional[str] = None,
        related_files: List[str] = None,
    ) -> Experience:
        """从执行中收集经验"""
        experience = Experience(
            task_description=task_description,
            experience_type=task_type,
            input_context=input_context,
            output_result=output_result,
            steps_taken=steps,
            lessons_learned=lessons or [],
            code_snippets=code_snippets or [],
            tags=tags or [],
            source_sop=source_sop,
            source_agent=source_agent,
            source_project=source_project,
            related_files=related_files or [],
        )
        
        # 初始评分
        experience.score = self.scorer.score(experience)
        
        # 添加到池
        exp_id = self.pool.add(experience)
        
        return self.pool.get(exp_id)
    
    def collect_from_sop_execution(
        self,
        sop_context: "SOPContext",
        success: bool = True,
        lessons: Optional[List[str]] = None,
    ) -> Optional[Experience]:
        """从 SOP 执行中收集经验

        Args:
            sop_context: SOP 执行上下文
            success: 执行是否成功
            lessons: 学到的教训

        Returns:
            收集到的经验，如果 sop_context 无效则返回 None
        """
        if not sop_context:
            return None

        # 验证必要的属性（检查属性存在且不为None）
        required_attrs = ["sop_name", "execution_history", "inputs",
                          "completed_steps", "failed_steps", "step_outputs"]
        for attr in required_attrs:
            if not hasattr(sop_context, attr):
                raise ValueError(f"SOPContext missing required attribute: {attr}")
            if getattr(sop_context, attr) is None:
                raise ValueError(f"SOPContext required attribute cannot be None: {attr}")
        
        # 提取步骤信息
        steps = []
        for record in sop_context.execution_history:
            steps.append({
                "step_name": record.get("step_name"),
                "status": record.get("status"),
                "timestamp": record.get("timestamp"),
            })
        
        # 收集输入
        input_context = {
            "sop_name": sop_context.sop_name,
            "inputs": sop_context.inputs,
        }
        
        # 收集输出
        output_result = {
            "completed_steps": sop_context.completed_steps,
            "failed_steps": sop_context.failed_steps,
            "step_outputs": sop_context.step_outputs,
        }
        
        # 确定经验类型
        exp_type = self._infer_experience_type(sop_context.sop_name)
        
        return self.collect_from_execution(
            task_description=f"执行 SOP: {sop_context.sop_name}",
            task_type=exp_type,
            input_context=input_context,
            output_result=output_result,
            steps=steps,
            success=success,
            lessons=lessons,
            source_sop=sop_context.sop_name,
        )
    
    # ========== 经验评估 ==========
    
    def evaluate_experience(self, exp_id: str) -> bool:
        """评估经验"""
        exp = self.pool.get(exp_id)
        if not exp:
            return False
        
        # 基础验证
        if not exp.validate():
            exp.status = ExperienceStatus.REJECTED
            return False
        
        # 质量评估
        exp.score = self.scorer.score(exp)
        
        # 根据评分决定状态
        if exp.score < 0.3:
            exp.status = ExperienceStatus.REJECTED
        else:
            exp.status = ExperienceStatus.VALIDATED
        
        exp.updated_at = datetime.now()
        return True
    
    def batch_evaluate(self, min_usage: int = 1) -> Dict[str, int]:
        """批量评估"""
        stats = {"validated": 0, "rejected": 0, "pending": 0}
        
        for exp in self.pool.list_by_status(ExperienceStatus.PENDING):
            if exp.usage_count >= min_usage:
                if self.evaluate_experience(exp.id):
                    stats["validated"] += 1
                else:
                    stats["rejected"] += 1
            else:
                stats["pending"] += 1
        
        return stats
    
    # ========== 经验检索 ==========
    
    def retrieve_experiences(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        exp_type: Optional[ExperienceType] = None,
        limit: int = 5,
    ) -> List[Any]:  # List[RetrievalResult]
        """检索经验"""
        return self.retriever.retrieve(
            query=query,
            context=context,
            exp_type=exp_type,
            limit=limit,
        )
    
    def get_relevant_experiences_for_task(
        self,
        task_description: str,
        task_type: ExperienceType,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 3,
    ) -> List[Any]:  # List[RetrievalResult]
        """获取任务相关经验"""
        return self.retriever.retrieve_for_task(
            task_description=task_description,
            task_type=task_type,
            context=context,
            limit=limit,
        )
    
    # ========== 经验应用 ==========
    
    def augment_prompt(
        self,
        base_prompt: str,
        task_description: str,
        task_type: ExperienceType,
        context: Optional[Dict[str, Any]] = None,
        max_experiences: int = 3,
    ) -> str:
        """增强提示"""
        return self.augmenter.augment_prompt(
            base_prompt=base_prompt,
            task_description=task_description,
            task_type=task_type,
            context=context,
            max_experiences=max_experiences,
        )
    
    def get_suggested_steps(
        self,
        task_description: str,
        task_type: ExperienceType,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """获取建议的步骤"""
        results = self.get_relevant_experiences_for_task(
            task_description=task_description,
            task_type=task_type,
            limit=limit,
        )
        
        suggested_steps = []
        for result in results:
            exp = result.experience
            for step in exp.steps_taken:
                if step not in suggested_steps:
                    suggested_steps.append(step)
        
        return suggested_steps
    
    def get_lessons_for_task(
        self,
        task_description: str,
        task_type: ExperienceType,
        limit: int = 10,
    ) -> List[str]:
        """获取任务相关的教训"""
        results = self.get_relevant_experiences_for_task(
            task_description=task_description,
            task_type=task_type,
            limit=limit,
        )
        
        lessons = []
        for result in results:
            for lesson in result.experience.lessons_learned:
                if lesson not in lessons:
                    lessons.append(lesson)
        
        return lessons
    
    # ========== 经验反馈 ==========
    
    def mark_experience_used(
        self,
        exp_id: str,
        success: bool = True,
    ) -> bool:
        """标记经验已使用"""
        exp = self.pool.get(exp_id)
        if not exp:
            return False
        
        exp.mark_used(success)
        return True
    
    def add_feedback(
        self,
        exp_id: str,
        helpful: bool,
        comment: Optional[str] = None,
    ) -> bool:
        """添加反馈"""
        exp = self.pool.get(exp_id)
        if not exp:
            return False
        
        # 更新评分
        if helpful:
            exp.score = min(exp.score + 0.05, 1.0)
        else:
            exp.score = max(exp.score - 0.05, 0.0)
        
        exp.updated_at = datetime.now()
        return True
    
    # ========== 维护 ==========
    
    def save(self):
        """保存经验池"""
        self.pool.save()
    
    def cleanup(self, days: int = 30) -> int:
        """清理过期经验"""
        return self.pool.cleanup_deprecated(days)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.pool.get_statistics()
    
    def _infer_experience_type(self, sop_name: str) -> ExperienceType:
        """推断经验类型"""
        sop_name_lower = sop_name.lower()
        
        if "code" in sop_name_lower or "write" in sop_name_lower:
            return ExperienceType.CODE_GENERATION
        elif "bug" in sop_name_lower or "fix" in sop_name_lower:
            return ExperienceType.BUG_FIX
        elif "review" in sop_name_lower:
            return ExperienceType.CODE_REVIEW
        elif "refactor" in sop_name_lower:
            return ExperienceType.REFACTORING
        elif "architect" in sop_name_lower or "design" in sop_name_lower:
            return ExperienceType.ARCHITECTURE
        elif "test" in sop_name_lower:
            return ExperienceType.TESTING
        elif "debug" in sop_name_lower:
            return ExperienceType.DEBUGGING
        elif "optim" in sop_name_lower:
            return ExperienceType.OPTIMIZATION
        else:
            return ExperienceType.GENERAL
