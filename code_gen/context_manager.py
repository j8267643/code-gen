"""
智能上下文管理模块
提供上下文窗口管理、消息压缩和重要性评分功能
"""
import json
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import tiktoken


@dataclass
class MessageImportance:
    """消息重要性评分"""
    score: float  # 0.0 - 1.0
    reasons: List[str] = field(default_factory=list)


@dataclass
class ContextMessage:
    """带元数据的消息"""
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    importance: MessageImportance = field(default_factory=lambda: MessageImportance(0.5))
    token_count: int = 0
    message_id: str = field(default_factory=lambda: hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8])
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "importance": self.importance.score,
            "token_count": self.token_count,
            "message_id": self.message_id
        }


class ContextWindowManager:
    """上下文窗口管理器"""
    
    def __init__(self, max_tokens: int = 8000, model: str = "gpt-4"):
        self.max_tokens = max_tokens
        self.model = model
        self.messages: List[ContextMessage] = []
        self.summary: Optional[str] = None
        self.total_tokens = 0
        
        # 尝试初始化 tokenizer
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except:
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """计算文本的 token 数量"""
        return len(self.encoding.encode(text))
    
    def add_message(self, role: str, content: str) -> ContextMessage:
        """添加新消息并计算重要性"""
        token_count = self.count_tokens(content)
        importance = self._calculate_importance(role, content)
        
        message = ContextMessage(
            role=role,
            content=content,
            importance=importance,
            token_count=token_count
        )
        
        self.messages.append(message)
        self.total_tokens += token_count
        
        # 检查是否需要压缩
        if self.total_tokens > self.max_tokens:
            self._compress_context()
        
        return message
    
    def _calculate_importance(self, role: str, content: str) -> MessageImportance:
        """计算消息重要性"""
        score = 0.5
        reasons = []
        
        # 系统消息重要性高
        if role == "system":
            score = 0.9
            reasons.append("system_message")
        
        # 包含代码块的消息重要性高
        if "```" in content:
            score += 0.15
            reasons.append("contains_code")
        
        # 包含错误信息的重要性高
        error_keywords = ["error", "exception", "failed", "traceback", "错误"]
        if any(keyword in content.lower() for keyword in error_keywords):
            score += 0.1
            reasons.append("contains_error")
        
        # 用户明确指令重要性高
        instruction_keywords = ["请", "需要", "必须", "应该", "please", "need", "must", "should"]
        if any(keyword in content.lower() for keyword in instruction_keywords):
            score += 0.05
            reasons.append("instruction")
        
        # 长消息适当降低重要性（除非包含代码）
        if len(content) > 1000 and "```" not in content:
            score -= 0.1
            reasons.append("long_message")
        
        return MessageImportance(min(1.0, max(0.0, score)), reasons)
    
    def _compress_context(self):
        """压缩上下文以符合 token 限制"""
        # 保留策略：
        # 1. 始终保留系统消息
        # 2. 保留最近的消息
        # 3. 根据重要性评分保留重要消息
        # 4. 对旧消息进行摘要
        
        target_tokens = int(self.max_tokens * 0.8)  # 保留 80% 空间
        
        # 分离系统消息和普通消息
        system_messages = [m for m in self.messages if m.role == "system"]
        other_messages = [m for m in self.messages if m.role != "system"]
        
        system_tokens = sum(m.token_count for m in system_messages)
        available_tokens = target_tokens - system_tokens
        
        if available_tokens <= 0:
            # 系统消息太多，需要摘要
            self._summarize_system_messages(system_messages)
            return
        
        # 按重要性排序（保留高重要性的）
        other_messages.sort(key=lambda m: (m.importance.score, m.timestamp), reverse=True)
        
        # 选择要保留的消息
        kept_messages = []
        current_tokens = 0
        
        # 始终保留最近的几条消息
        recent_messages = other_messages[-5:] if len(other_messages) > 5 else other_messages
        for msg in recent_messages:
            if current_tokens + msg.token_count <= available_tokens:
                kept_messages.append(msg)
                current_tokens += msg.token_count
        
        # 从重要性高的消息中选择
        for msg in other_messages:
            if msg in kept_messages:
                continue
            if msg.importance.score > 0.7 and current_tokens + msg.token_count <= available_tokens:
                kept_messages.append(msg)
                current_tokens += msg.token_count
        
        # 对丢弃的消息进行摘要
        discarded = [m for m in other_messages if m not in kept_messages]
        if discarded:
            self._create_summary(discarded)
        
        # 重新组装消息列表
        kept_messages.sort(key=lambda m: m.timestamp)
        self.messages = system_messages + kept_messages
        self.total_tokens = sum(m.token_count for m in self.messages)
        
        # 如果有摘要，添加为系统消息
        if self.summary:
            summary_msg = ContextMessage(
                role="system",
                content=f"[Context Summary] {self.summary}",
                importance=MessageImportance(0.95, ["summary"]),
                token_count=self.count_tokens(self.summary) + 20
            )
            self.messages.insert(len(system_messages), summary_msg)
            self.total_tokens += summary_msg.token_count
    
    def _summarize_system_messages(self, messages: List[ContextMessage]):
        """摘要系统消息"""
        # 简化处理：保留最重要的系统消息
        messages.sort(key=lambda m: m.importance.score, reverse=True)
        kept = messages[:2]  # 最多保留 2 条
        self.messages = kept
        self.total_tokens = sum(m.token_count for m in kept)
    
    def _create_summary(self, messages: List[ContextMessage]):
        """创建消息摘要"""
        # 提取关键信息
        topics = []
        code_blocks = []
        decisions = []
        
        for msg in messages:
            content = msg.content
            
            # 提取代码块
            if "```" in content:
                code_blocks.append("[code block]")
            
            # 提取决策/结论
            if any(keyword in content.lower() for keyword in ["decided", "conclusion", "确定", "决定"]):
                decisions.append(content[:100] + "..." if len(content) > 100 else content)
            
            # 提取主题（简化处理）
            if msg.importance.score > 0.7:
                topics.append(content[:50] + "..." if len(content) > 50 else content)
        
        summary_parts = []
        if topics:
            summary_parts.append(f"Discussed {len(topics)} key topics")
        if code_blocks:
            summary_parts.append(f"{len(code_blocks)} code exchanges")
        if decisions:
            summary_parts.append(f"{len(decisions)} decisions made")
        
        self.summary = "; ".join(summary_parts) if summary_parts else "Previous context summarized"
    
    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """获取用于 API 调用的消息列表"""
        return [{"role": m.role, "content": m.content} for m in self.messages]
    
    def get_context_stats(self) -> Dict[str, Any]:
        """获取上下文统计信息"""
        return {
            "total_messages": len(self.messages),
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "usage_percent": round(self.total_tokens / self.max_tokens * 100, 2),
            "has_summary": self.summary is not None,
            "message_breakdown": {
                "system": len([m for m in self.messages if m.role == "system"]),
                "user": len([m for m in self.messages if m.role == "user"]),
                "assistant": len([m for m in self.messages if m.role == "assistant"])
            }
        }
    
    def clear(self):
        """清空上下文"""
        self.messages = []
        self.summary = None
        self.total_tokens = 0


class ConversationMemory:
    """会话记忆管理"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.memory_file = work_dir / ".code_gen" / "conversation_memory.json"
        self.sessions: Dict[str, Any] = {}
        self._load_memory()
    
    def _load_memory(self):
        """加载历史会话记忆"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.sessions = json.load(f)
            except:
                self.sessions = {}
    
    def save_session(self, session_id: str, context_manager: ContextWindowManager):
        """保存会话"""
        self.sessions[session_id] = {
            "timestamp": datetime.now().isoformat(),
            "stats": context_manager.get_context_stats(),
            "messages": [m.to_dict() for m in context_manager.messages]
        }
        self._save()
    
    def _save(self):
        """保存到文件"""
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.sessions, f, ensure_ascii=False, indent=2)
    
    def get_session_summary(self, session_id: str) -> Optional[str]:
        """获取会话摘要"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            stats = session.get("stats", {})
            return f"Session with {stats.get('total_messages', 0)} messages, {stats.get('total_tokens', 0)} tokens"
        return None
