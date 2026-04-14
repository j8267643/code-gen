"""
Context Window Management - 上下文窗口管理
Inspired by Claude Code's context compression

解决长对话内存问题：
1. 三层压缩策略：微压缩 → Session Memory → 全量压缩
2. Token 计数和预算管理
3. 智能上下文选择
4. 摘要生成和恢复
5. 按需压缩 (/compact 命令)

适用于：长对话、大代码库处理、多轮迭代开发
"""
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import hashlib
import re


class CompressionLevel(str, Enum):
    """压缩级别"""
    NONE = "none"           # 无压缩
    LIGHT = "light"         # 微压缩 - 移除冗余
    MEDIUM = "medium"       # 中等 - 摘要保留
    HEAVY = "heavy"         # 重度 - 仅保留关键
    AGGRESSIVE = "aggressive"  # 激进 - 最大压缩


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """对话消息"""
    role: MessageRole
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: hashlib.md5(
        datetime.now().isoformat().encode()).hexdigest()[:12])
    compressed: bool = False
    original_length: int = 0
    
    def __post_init__(self):
        if self.original_length == 0:
            self.original_length = len(self.content)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "compressed": self.compressed,
            "original_length": self.original_length
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        return cls(
            id=data.get("id", ""),
            role=MessageRole(data.get("role", "user")),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
            compressed=data.get("compressed", False),
            original_length=data.get("original_length", 0)
        )
    
    @property
    def token_count(self) -> int:
        """估算 token 数（简化计算）"""
        # 中文按字，英文按词
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', self.content))
        english_words = len(re.findall(r'[a-zA-Z]+', self.content))
        return chinese_chars + english_words


@dataclass
class ContextSummary:
    """上下文摘要"""
    summary: str
    key_points: List[str]
    important_decisions: List[str]
    action_items: List[str]
    compressed_from: int  # 原始消息数
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "key_points": self.key_points,
            "important_decisions": self.important_decisions,
            "action_items": self.action_items,
            "compressed_from": self.compressed_from,
            "timestamp": self.timestamp
        }


@dataclass
class ContextBudget:
    """上下文预算配置"""
    max_tokens: int = 8000
    warning_threshold: float = 0.8  # 80% 警告
    critical_threshold: float = 0.95  # 95% 强制压缩
    reserve_tokens: int = 500  # 预留空间
    
    @property
    def effective_max(self) -> int:
        """有效最大 token 数"""
        return self.max_tokens - self.reserve_tokens
    
    @property
    def warning_limit(self) -> int:
        """警告阈值"""
        return int(self.effective_max * self.warning_threshold)
    
    @property
    def critical_limit(self) -> int:
        """临界阈值"""
        return int(self.effective_max * self.critical_threshold)


class ContextCompressor:
    """上下文压缩器"""
    
    def __init__(self):
        self.compression_stats: List[Dict[str, Any]] = []
    
    def light_compress(self, message: Message) -> Message:
        """
        微压缩 - 移除冗余信息
        - 删除多余空白
        - 简化格式标记
        """
        if message.compressed:
            return message
        
        content = message.content
        
        # 删除多余空白
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        # 简化代码块标记
        content = re.sub(r'```\w+\n', '```\n', content)
        
        return Message(
            role=message.role,
            content=content.strip(),
            metadata={**message.metadata, "compression": "light"},
            compressed=True,
            original_length=message.original_length
        )
    
    def medium_compress(self, messages: List[Message]) -> ContextSummary:
        """
        中等压缩 - 生成摘要
        保留关键信息，生成结构化摘要
        """
        # 提取关键信息
        key_points = []
        decisions = []
        actions = []
        
        for msg in messages:
            content = msg.content
            
            # 提取代码块
            code_blocks = re.findall(r'```[\s\S]*?```', content)
            for block in code_blocks[:2]:  # 最多保留2个代码块引用
                key_points.append(f"代码: {block[:50]}...")
            
            # 提取决策（包含"决定"、"使用"等关键词）
            if any(kw in content for kw in ["决定", "选择", "使用", "采用"]):
                sentences = re.split(r'[。！？\n]', content)
                for sent in sentences:
                    if any(kw in sent for kw in ["决定", "选择", "使用"]):
                        decisions.append(sent.strip()[:100])
            
            # 提取行动项
            if msg.role == MessageRole.ASSISTANT:
                actions.append(f"AI: {content[:80]}...")
        
        # 去重和限制
        key_points = list(dict.fromkeys(key_points))[:10]
        decisions = list(dict.fromkeys(decisions))[:5]
        actions = actions[-5:]  # 最近5个
        
        summary = f"对话摘要: 共 {len(messages)} 条消息，关键决策 {len(decisions)} 个"
        
        return ContextSummary(
            summary=summary,
            key_points=key_points,
            important_decisions=decisions,
            action_items=actions,
            compressed_from=len(messages)
        )
    
    def heavy_compress(self, messages: List[Message]) -> Message:
        """
        重度压缩 - 仅保留关键
        将多条消息压缩为一条系统消息
        """
        summary = self.medium_compress(messages)
        
        content = f"""[上下文摘要]
{summary.summary}

关键要点:
"""
        for i, point in enumerate(summary.key_points[:5], 1):
            content += f"{i}. {point}\n"
        
        if summary.important_decisions:
            content += "\n重要决策:\n"
            for dec in summary.important_decisions[:3]:
                content += f"- {dec}\n"
        
        return Message(
            role=MessageRole.SYSTEM,
            content=content,
            metadata={
                "type": "context_summary",
                "compressed_from": summary.compressed_from,
                "compression_level": "heavy"
            },
            compressed=True,
            original_length=sum(m.original_length for m in messages)
        )
    
    def aggressive_compress(self, context: 'ContextWindow') -> Message:
        """
        激进压缩 - 最大压缩率
        仅保留最核心信息
        """
        messages = context.messages
        
        # 提取最后一条用户消息和助手回复
        last_user = None
        last_assistant = None
        
        for msg in reversed(messages):
            if not last_user and msg.role == MessageRole.USER:
                last_user = msg
            if not last_assistant and msg.role == MessageRole.ASSISTANT:
                last_assistant = msg
            if last_user and last_assistant:
                break
        
        # 提取所有文件修改
        files_modified = []
        for msg in messages:
            if "文件" in msg.content or "File" in msg.content:
                files = re.findall(r'[\w/]+\.(py|js|ts|java|cpp|h|json|yaml|yml)', msg.content)
                files_modified.extend(files)
        
        content = "[压缩上下文]\n"
        content += f"当前任务: {last_user.content[:100] if last_user else 'N/A'}...\n"
        content += f"最近回复: {last_assistant.content[:100] if last_assistant else 'N/A'}...\n"
        
        if files_modified:
            content += f"相关文件: {', '.join(set(files_modified))}\n"
        
        return Message(
            role=MessageRole.SYSTEM,
            content=content,
            metadata={
                "type": "aggressive_summary",
                "original_count": len(messages),
                "compression_level": "aggressive"
            },
            compressed=True,
            original_length=sum(m.original_length for m in messages)
        )


class ContextWindow:
    """
    上下文窗口管理器
    
    管理对话上下文，自动处理压缩和预算
    """
    
    def __init__(
        self,
        budget: Optional[ContextBudget] = None,
        system_prompt: Optional[str] = None
    ):
        self.budget = budget or ContextBudget()
        self.messages: List[Message] = []
        self.compressor = ContextCompressor()
        self.compression_history: List[Dict[str, Any]] = []
        
        # 添加系统提示
        if system_prompt:
            self.add_system_message(system_prompt)
    
    @property
    def total_tokens(self) -> int:
        """当前总 token 数"""
        return sum(msg.token_count for msg in self.messages)
    
    @property
    def usage_ratio(self) -> float:
        """使用率"""
        return self.total_tokens / self.budget.effective_max
    
    @property
    def status(self) -> str:
        """当前状态"""
        ratio = self.usage_ratio
        if ratio >= 1.0:
            return "overflow"
        elif ratio >= self.budget.critical_threshold:
            return "critical"
        elif ratio >= self.budget.warning_threshold:
            return "warning"
        return "normal"
    
    def add_message(
        self,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """添加消息"""
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        
        # 检查是否需要自动压缩
        self._check_and_compress()
        
        return message
    
    def add_system_message(self, content: str) -> Message:
        """添加系统消息"""
        return self.add_message(MessageRole.SYSTEM, content)
    
    def add_user_message(self, content: str) -> Message:
        """添加用户消息"""
        return self.add_message(MessageRole.USER, content)
    
    def add_assistant_message(self, content: str) -> Message:
        """添加助手消息"""
        return self.add_message(MessageRole.ASSISTANT, content)
    
    def _check_and_compress(self):
        """检查并执行自动压缩"""
        if self.status == "overflow":
            # 强制压缩
            self.compact(level=CompressionLevel.HEAVY)
        elif self.status == "critical":
            # 建议压缩
            pass  # 留给外部处理
    
    def compact(
        self,
        level: CompressionLevel = CompressionLevel.MEDIUM,
        preserve_recent: int = 2
    ) -> Dict[str, Any]:
        """
        压缩上下文 (/compact 命令)
        
        Args:
            level: 压缩级别
            preserve_recent: 保留最近 N 条消息不压缩
        """
        if len(self.messages) <= preserve_recent + 1:
            return {"status": "skipped", "reason": "消息太少"}
        
        # 保留系统消息和最近消息
        system_msgs = [m for m in self.messages if m.role == MessageRole.SYSTEM]
        recent_msgs = self.messages[-preserve_recent:] if preserve_recent > 0 else []
        compressible = self.messages[len(system_msgs):-preserve_recent] if preserve_recent > 0 else self.messages[len(system_msgs):]
        
        if not compressible:
            return {"status": "skipped", "reason": "无可压缩消息"}
        
        original_count = len(self.messages)
        original_tokens = self.total_tokens
        
        # 根据级别执行压缩
        if level == CompressionLevel.LIGHT:
            compressed = [self.compressor.light_compress(m) for m in compressible]
            self.messages = system_msgs + compressed + recent_msgs
            
        elif level == CompressionLevel.MEDIUM:
            summary = self.compressor.medium_compress(compressible)
            summary_msg = Message(
                role=MessageRole.SYSTEM,
                content=f"[历史摘要] {summary.summary}",
                metadata={"type": "summary", "details": summary.to_dict()}
            )
            self.messages = system_msgs + [summary_msg] + recent_msgs
            
        elif level == CompressionLevel.HEAVY:
            summary_msg = self.compressor.heavy_compress(compressible)
            self.messages = system_msgs + [summary_msg] + recent_msgs
            
        elif level == CompressionLevel.AGGRESSIVE:
            summary_msg = self.compressor.aggressive_compress(self)
            self.messages = system_msgs + [summary_msg] + recent_msgs
        
        # 记录压缩历史
        result = {
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "original_count": original_count,
            "new_count": len(self.messages),
            "original_tokens": original_tokens,
            "new_tokens": self.total_tokens,
            "compression_ratio": 1 - (self.total_tokens / original_tokens) if original_tokens > 0 else 0
        }
        self.compression_history.append(result)
        
        return result
    
    def get_context_for_model(self) -> List[Dict[str, str]]:
        """获取用于模型调用的上下文格式"""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in self.messages
        ]
    
    def clear(self, keep_system: bool = True):
        """清空上下文"""
        if keep_system:
            system_msgs = [m for m in self.messages if m.role == MessageRole.SYSTEM]
            self.messages = system_msgs
        else:
            self.messages = []
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_messages": len(self.messages),
            "total_tokens": self.total_tokens,
            "budget": {
                "max": self.budget.max_tokens,
                "effective": self.budget.effective_max,
                "used": self.total_tokens,
                "remaining": self.budget.effective_max - self.total_tokens
            },
            "usage_ratio": self.usage_ratio,
            "status": self.status,
            "compression_count": len(self.compression_history),
            "compression_history": self.compression_history[-5:]  # 最近5次
        }
    
    def export(self) -> Dict[str, Any]:
        """导出完整上下文"""
        return {
            "messages": [m.to_dict() for m in self.messages],
            "budget": {
                "max_tokens": self.budget.max_tokens,
                "warning_threshold": self.budget.warning_threshold,
                "critical_threshold": self.budget.critical_threshold
            },
            "compression_history": self.compression_history,
            "stats": self.get_stats()
        }
    
    @classmethod
    def import_context(cls, data: Dict[str, Any]) -> 'ContextWindow':
        """导入上下文"""
        budget = ContextBudget(
            max_tokens=data.get("budget", {}).get("max_tokens", 8000),
            warning_threshold=data.get("budget", {}).get("warning_threshold", 0.8),
            critical_threshold=data.get("budget", {}).get("critical_threshold", 0.95)
        )
        
        window = cls(budget=budget)
        window.messages = [
            Message.from_dict(m) for m in data.get("messages", [])
        ]
        window.compression_history = data.get("compression_history", [])
        
        return window


class ContextManager:
    """
    上下文管理器
    
    管理多个上下文窗口，提供高级功能
    """
    
    def __init__(self):
        self.windows: Dict[str, ContextWindow] = {}
        self.active_window: Optional[str] = None
    
    def create_window(
        self,
        name: str,
        budget: Optional[ContextBudget] = None,
        system_prompt: Optional[str] = None
    ) -> ContextWindow:
        """创建新上下文窗口"""
        window = ContextWindow(budget=budget, system_prompt=system_prompt)
        self.windows[name] = window
        self.active_window = name
        return window
    
    def get_window(self, name: Optional[str] = None) -> Optional[ContextWindow]:
        """获取上下文窗口"""
        if name:
            return self.windows.get(name)
        if self.active_window:
            return self.windows.get(self.active_window)
        return None
    
    def switch_window(self, name: str) -> bool:
        """切换活动窗口"""
        if name in self.windows:
            self.active_window = name
            return True
        return False
    
    def close_window(self, name: str) -> bool:
        """关闭窗口"""
        if name in self.windows:
            del self.windows[name]
            if self.active_window == name:
                self.active_window = next(iter(self.windows.keys()), None)
            return True
        return False
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有窗口统计"""
        return {
            name: window.get_stats()
            for name, window in self.windows.items()
        }


# ========== 便捷函数 ==========

def create_context_window(
    max_tokens: int = 8000,
    system_prompt: Optional[str] = None
) -> ContextWindow:
    """便捷创建上下文窗口"""
    budget = ContextBudget(max_tokens=max_tokens)
    return ContextWindow(budget=budget, system_prompt=system_prompt)


def compact_context(
    messages: List[Dict[str, str]],
    level: str = "medium"
) -> List[Dict[str, str]]:
    """便捷压缩函数"""
    window = ContextWindow()
    for msg in messages:
        window.add_message(
            role=MessageRole(msg.get("role", "user")),
            content=msg.get("content", "")
        )
    
    result = window.compact(level=CompressionLevel(level))
    
    if result.get("status") == "skipped":
        return messages
    
    return window.get_context_for_model()
