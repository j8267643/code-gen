"""Experience Pool Implementation"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta

from .experience import Experience, ExperienceType, ExperienceStatus


class ExperiencePool:
    """经验池
    
    存储和管理经验条目
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.experiences: Dict[str, Experience] = {}
        self.storage_path = storage_path or Path(".exp_pool")
        self._type_index: Dict[ExperienceType, List[str]] = {}
        self._tag_index: Dict[str, List[str]] = {}
    
    def add(self, experience: Experience) -> str:
        """添加经验"""
        # 检查重复
        exp_hash = experience.compute_hash()
        for existing in self.experiences.values():
            if existing.compute_hash() == exp_hash:
                # 更新现有经验
                existing.usage_count += experience.usage_count
                existing.success_count += experience.success_count
                existing.updated_at = datetime.now()
                return existing.id
        
        # 添加新经验
        self.experiences[experience.id] = experience
        self._update_indexes(experience)
        return experience.id
    
    def get(self, exp_id: str) -> Optional[Experience]:
        """获取经验"""
        return self.experiences.get(exp_id)
    
    def remove(self, exp_id: str) -> bool:
        """移除经验"""
        if exp_id in self.experiences:
            exp = self.experiences[exp_id]
            del self.experiences[exp_id]
            self._remove_from_indexes(exp)
            return True
        return False
    
    def list_all(self) -> List[Experience]:
        """列出所有经验"""
        return list(self.experiences.values())
    
    def list_by_type(self, exp_type: ExperienceType) -> List[Experience]:
        """按类型列出"""
        ids = self._type_index.get(exp_type, [])
        return [self.experiences[i] for i in ids if i in self.experiences]
    
    def list_by_tag(self, tag: str) -> List[Experience]:
        """按标签列出"""
        ids = self._tag_index.get(tag, [])
        return [self.experiences[i] for i in ids if i in self.experiences]
    
    def list_by_status(self, status: ExperienceStatus) -> List[Experience]:
        """按状态列出"""
        return [e for e in self.experiences.values() if e.status == status]
    
    def search(
        self,
        query: str,
        exp_type: Optional[ExperienceType] = None,
        tags: Optional[List[str]] = None,
        min_score: float = 0.0,
        limit: int = 10,
    ) -> List[Experience]:
        """搜索经验
        
        简单的关键词搜索，实际使用时应结合向量检索
        """
        results = []
        query_lower = query.lower()
        
        for exp in self.experiences.values():
            # 类型过滤
            if exp_type and exp.experience_type != exp_type:
                continue
            
            # 标签过滤
            if tags and not any(t in exp.tags for t in tags):
                continue
            
            # 评分过滤
            if exp.score < min_score:
                continue
            
            # 关键词匹配
            score = 0
            if query_lower in exp.task_description.lower():
                score += 10
            if any(query_lower in tag.lower() for tag in exp.tags):
                score += 5
            if any(query_lower in lesson.lower() for lesson in exp.lessons_learned):
                score += 3
            
            if score > 0:
                results.append((exp, score))
        
        # 按评分排序
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:limit]]
    
    def get_top_experiences(
        self,
        exp_type: Optional[ExperienceType] = None,
        limit: int = 10,
        min_usage: int = 1,
    ) -> List[Experience]:
        """获取最佳经验"""
        experiences = list(self.experiences.values())
        
        if exp_type:
            experiences = [e for e in experiences if e.experience_type == exp_type]
        
        # 过滤使用次数
        experiences = [e for e in experiences if e.usage_count >= min_usage]
        
        # 按综合评分排序
        def score_key(e: Experience):
            # 综合评分 = 质量评分 * 0.4 + 成功率 * 0.4 + 使用次数归一化 * 0.2
            usage_score = min(e.usage_count / 100, 1.0)  # 归一化到 0-1
            return e.score * 0.4 + e.success_rate * 0.4 + usage_score * 0.2
        
        experiences.sort(key=score_key, reverse=True)
        return experiences[:limit]
    
    def get_similar_experiences(
        self,
        experience: Experience,
        limit: int = 5,
    ) -> List[Experience]:
        """获取相似经验"""
        # 基于类型和标签的相似度
        candidates = self.list_by_type(experience.experience_type)
        candidates = [c for c in candidates if c.id != experience.id]
        
        def similarity(e: Experience) -> float:
            score = 0.0
            # 标签相似度
            if e.tags and experience.tags:
                common_tags = set(e.tags) & set(experience.tags)
                score += len(common_tags) / max(len(e.tags), len(experience.tags))
            # 任务描述相似度（简单实现）
            common_words = set(e.task_description.lower().split()) & set(experience.task_description.lower().split())
            score += len(common_words) / 10  # 归一化
            return score
        
        candidates.sort(key=similarity, reverse=True)
        return candidates[:limit]
    
    def merge_experiences(self, exp_ids: List[str]) -> Optional[Experience]:
        """合并多个经验"""
        experiences = [self.get(i) for i in exp_ids]
        experiences = [e for e in experiences if e]
        
        if len(experiences) < 2:
            return None
        
        # 创建合并后的经验
        merged = Experience(
            task_description=experiences[0].task_description,
            experience_type=experiences[0].experience_type,
            input_context=experiences[0].input_context,
            output_result=experiences[0].output_result,
            tags=list(set(sum([e.tags for e in experiences], []))),
            lessons_learned=list(set(sum([e.lessons_learned for e in experiences], []))),
            usage_count=sum(e.usage_count for e in experiences),
            success_count=sum(e.success_count for e in experiences),
            score=sum(e.score for e in experiences) / len(experiences),
        )
        
        return merged
    
    def cleanup_deprecated(self, days: int = 30) -> int:
        """清理过期经验"""
        cutoff = datetime.now() - timedelta(days=days)
        to_remove = []
        
        for exp_id, exp in self.experiences.items():
            if exp.status == ExperienceStatus.DEPRECATED:
                if exp.updated_at < cutoff:
                    to_remove.append(exp_id)
        
        for exp_id in to_remove:
            self.remove(exp_id)
        
        return len(to_remove)
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        total = len(self.experiences)
        by_type = {}
        by_status = {}
        
        for exp in self.experiences.values():
            by_type[exp.experience_type.value] = by_type.get(exp.experience_type.value, 0) + 1
            by_status[exp.status.value] = by_status.get(exp.status.value, 0) + 1
        
        total_usage = sum(e.usage_count for e in self.experiences.values())
        total_success = sum(e.success_count for e in self.experiences.values())
        avg_score = sum(e.score for e in self.experiences.values()) / total if total > 0 else 0
        
        return {
            "total_experiences": total,
            "by_type": by_type,
            "by_status": by_status,
            "total_usage": total_usage,
            "total_success": total_success,
            "overall_success_rate": total_success / total_usage if total_usage > 0 else 0,
            "average_score": avg_score,
        }
    
    def save(self, path: Optional[Path] = None):
        """保存到文件"""
        save_path = path or self.storage_path / "experiences.json"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "experiences": {k: v.to_dict() for k, v in self.experiences.items()},
            "saved_at": datetime.now().isoformat(),
        }
        
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, path: Optional[Path] = None):
        """从文件加载"""
        load_path = path or self.storage_path / "experiences.json"
        
        if not load_path.exists():
            return
        
        with open(load_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for exp_id, exp_data in data.get("experiences", {}).items():
            try:
                exp = Experience.from_dict(exp_data)
                self.experiences[exp_id] = exp
                self._update_indexes(exp)
            except Exception as e:
                print(f"Failed to load experience {exp_id}: {e}")
    
    def _update_indexes(self, experience: Experience):
        """更新索引"""
        # 类型索引
        if experience.experience_type not in self._type_index:
            self._type_index[experience.experience_type] = []
        if experience.id not in self._type_index[experience.experience_type]:
            self._type_index[experience.experience_type].append(experience.id)
        
        # 标签索引
        for tag in experience.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            if experience.id not in self._tag_index[tag]:
                self._tag_index[tag].append(experience.id)
    
    def _remove_from_indexes(self, experience: Experience):
        """从索引中移除"""
        # 类型索引
        if experience.experience_type in self._type_index:
            if experience.id in self._type_index[experience.experience_type]:
                self._type_index[experience.experience_type].remove(experience.id)
        
        # 标签索引
        for tag in experience.tags:
            if tag in self._tag_index:
                if experience.id in self._tag_index[tag]:
                    self._tag_index[tag].remove(experience.id)
