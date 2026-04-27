"""
Enhanced memory integration for conversations
主动在对话中使用记忆系统
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta

from code_gen.memory.memory_system import AdvancedMemorySystem, MemoryCategory, MemoryEntry


class ConversationMemory:
    """
    增强对话记忆系统
    在对话中主动检索和使用相关记忆
    """
    
    def __init__(self, work_dir: Path, memory_system: AdvancedMemorySystem = None):
        self.work_dir = work_dir
        self.memory = memory_system or AdvancedMemorySystem(work_dir)
        self.session_memories: List[str] = []  # 当前会话涉及的记忆ID
        self.last_retrieval_time: Optional[datetime] = None
    
    def on_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        用户输入时触发，保存记忆并检索相关记忆
        
        Returns:
            {
                "saved_memory_id": str,
                "relevant_memories": List[MemoryEntry],
                "context_prompt": str
            }
        """
        # 1. 保存用户输入为记忆
        saved_memory = self.memory.add_memory(
            content=user_input,
            category=MemoryCategory.CONVERSATION,
            tags=["user_input", "conversation"],
            importance=5
        )
        self.session_memories.append(saved_memory.id)
        
        # 2. 检索相关记忆
        relevant = self._retrieve_relevant_memories(user_input)
        
        # 3. 生成上下文提示
        context_prompt = self._build_context_prompt(relevant)
        
        return {
            "saved_memory_id": saved_memory.id,
            "relevant_memories": relevant,
            "context_prompt": context_prompt
        }
    
    def on_ai_response(self, response: str, related_memory_id: str = None):
        """
        AI 回复时触发，保存回复并建立关联
        """
        # 保存 AI 回复
        ai_memory = self.memory.add_memory(
            content=response,
            category=MemoryCategory.CONVERSATION,
            tags=["ai_response", "conversation"],
            importance=5
        )
        self.session_memories.append(ai_memory.id)
        
        # 关联到用户输入
        if related_memory_id:
            self.memory.link_memories(related_memory_id, ai_memory.id)
    
    def _retrieve_relevant_memories(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        """
        检索与当前查询相关的记忆
        多维度检索策略
        """
        relevant = []
        seen_ids = set()
        
        # 1. 全文搜索
        search_results = self.memory.search_memories(query, limit=limit)
        for mem in search_results:
            if mem.id not in seen_ids:
                relevant.append(mem)
                seen_ids.add(mem.id)
        
        # 2. 检索用户偏好（高优先级）
        user_prefs = self.memory.get_memories_by_category(MemoryCategory.USER_PREF, limit=3)
        for mem in user_prefs:
            if mem.id not in seen_ids:
                relevant.append(mem)
                seen_ids.add(mem.id)
        
        # 3. 检索项目信息
        project_info = self.memory.get_memories_by_category(MemoryCategory.PROJECT, limit=2)
        for mem in project_info:
            if mem.id not in seen_ids:
                relevant.append(mem)
                seen_ids.add(mem.id)
        
        # 4. 检索最近的知识
        knowledge = self.memory.get_memories_by_category(MemoryCategory.KNOWLEDGE, limit=3)
        for mem in knowledge:
            if mem.id not in seen_ids and self._is_relevant_to_query(mem, query):
                relevant.append(mem)
                seen_ids.add(mem.id)
        
        # 5. 检索当前会话的记忆
        for mem_id in self.session_memories[-5:]:  # 最近5条
            if mem_id not in seen_ids:
                mem = self.memory.get_memory(mem_id)
                if mem:
                    relevant.append(mem)
                    seen_ids.add(mem_id)
        
        # 按重要性排序
        relevant.sort(key=lambda m: m.importance, reverse=True)
        
        return relevant[:limit]
    
    def _is_relevant_to_query(self, memory: MemoryEntry, query: str) -> bool:
        """判断记忆是否与查询相关"""
        query_lower = query.lower()
        
        # 检查标签匹配
        for tag in memory.tags:
            if tag.lower() in query_lower:
                return True
        
        # 检查内容匹配（简单版本）
        if any(word in memory.content.lower() for word in query_lower.split()):
            return True
        
        return False
    
    def _build_context_prompt(self, memories: List[MemoryEntry]) -> str:
        """
        构建记忆上下文提示
        将相关记忆格式化为提示文本
        """
        if not memories:
            return ""
        
        prompt_parts = ["\n<memory_context>"]
        prompt_parts.append("以下是与当前对话相关的记忆信息：\n")
        
        # 分类显示记忆
        categories = {
            MemoryCategory.USER_PREF: "📌 用户偏好",
            MemoryCategory.PROJECT: "📁 项目信息",
            MemoryCategory.KNOWLEDGE: "💡 相关知识",
            MemoryCategory.CONVERSATION: "💬 对话历史",
            MemoryCategory.REFLECTION: "🤔 反思总结"
        }
        
        for category, label in categories.items():
            category_memories = [m for m in memories if m.category == category]
            if category_memories:
                prompt_parts.append(f"\n{label}:")
                for mem in category_memories[:2]:  # 每类最多2条
                    content = mem.summary if mem.summary else mem.content[:200]
                    prompt_parts.append(f"  • {content}")
        
        prompt_parts.append("\n</memory_context>\n")
        
        return "\n".join(prompt_parts)
    
    def extract_knowledge(self, conversation_summary: str):
        """
        从对话中提取知识
        在对话结束后调用
        """
        # 保存为知识记忆
        self.memory.add_memory(
            content=conversation_summary,
            category=MemoryCategory.KNOWLEDGE,
            tags=["extracted", "conversation"],
            importance=7
        )
    
    def save_user_preference(self, preference: str, importance: int = 8):
        """
        保存用户偏好
        高重要性，长期保留
        """
        self.memory.add_memory(
            content=preference,
            category=MemoryCategory.USER_PREF,
            tags=["preference", "user_profile"],
            importance=importance
        )
    
    def save_project_info(self, info: str, tags: List[str] = None):
        """
        保存项目信息
        """
        if tags is None:
            tags = []
        tags.append("project")
        
        self.memory.add_memory(
            content=info,
            category=MemoryCategory.PROJECT,
            tags=tags,
            importance=6
        )
    
    def get_session_summary(self) -> str:
        """
        获取当前会话摘要
        """
        if not self.session_memories:
            return "无会话记忆"
        
        memories = []
        for mem_id in self.session_memories:
            mem = self.memory.get_memory(mem_id)
            if mem:
                memories.append(mem)
        
        summary = f"当前会话共有 {len(memories)} 条记忆\n"
        for mem in memories:
            content = mem.summary if mem.summary else mem.content[:100]
            summary += f"  [{mem.category.value}] {content}...\n"
        
        return summary
    
    def run_maintenance(self):
        """
        运行记忆维护
        - 合并相似记忆
        - 清理低重要性旧记忆
        - 更新关联
        """
        stats = self.memory.get_memory_stats()
        print(f"维护前统计: {stats}")
        
        # TODO: 实现记忆合并和清理逻辑
        
        return stats


# 全局实例
conversation_memory: Optional[ConversationMemory] = None


def init_conversation_memory(work_dir: Path) -> ConversationMemory:
    """初始化对话记忆系统"""
    global conversation_memory
    conversation_memory = ConversationMemory(work_dir)
    return conversation_memory


def get_conversation_memory() -> Optional[ConversationMemory]:
    """获取对话记忆系统实例"""
    return conversation_memory
