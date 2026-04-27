"""
Sequential Thinking Tool - 序列化思考工具

功能：帮助 AI 进行多步骤推理，支持动态调整、修订和分支思考
与 Prompt Chaining 的区别：更专注于"思考"过程而非"执行"过程
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json
import asyncio


class ThoughtType(str, Enum):
    """思考类型"""
    ANALYSIS = "analysis"           # 分析
    HYPOTHESIS = "hypothesis"       # 假设
    VERIFICATION = "verification"   # 验证
    REVISION = "revision"           # 修订
    BRANCH = "branch"               # 分支
    CONCLUSION = "conclusion"       # 结论


@dataclass
class Thought:
    """单个思考步骤"""
    thought_number: int             # 思考序号
    total_thoughts: int             # 预计总思考数
    content: str                    # 思考内容
    thought_type: ThoughtType       # 思考类型
    next_thought_needed: bool       # 是否需要继续思考
    
    # 修订相关
    is_revision: bool = False       # 是否是修订
    revises_thought: Optional[int] = None  # 修订哪个思考
    
    # 分支相关
    branch_from_thought: Optional[int] = None  # 从哪个思考分支
    branch_id: Optional[str] = None  # 分支ID
    
    # 扩展思考
    needs_more_thoughts: bool = False  # 是否需要更多思考
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "thought_number": self.thought_number,
            "total_thoughts": self.total_thoughts,
            "content": self.content,
            "thought_type": self.thought_type.value,
            "next_thought_needed": self.next_thought_needed,
            "is_revision": self.is_revision,
            "revises_thought": self.revises_thought,
            "branch_from_thought": self.branch_from_thought,
            "branch_id": self.branch_id,
            "needs_more_thoughts": self.needs_more_thoughts,
            "timestamp": self.timestamp
        }


@dataclass
class ThinkingSession:
    """思考会话"""
    session_id: str
    problem: str                    # 要解决的问题
    thoughts: List[Thought] = field(default_factory=list)
    branches: Dict[str, List[Thought]] = field(default_factory=dict)
    current_branch: str = "main"    # 当前分支
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed: bool = False
    conclusion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "problem": self.problem,
            "thoughts": [t.to_dict() for t in self.thoughts],
            "branches": {k: [t.to_dict() for t in v] for k, v in self.branches.items()},
            "current_branch": self.current_branch,
            "created_at": self.created_at,
            "completed": self.completed,
            "conclusion": self.conclusion
        }


class SequentialThinkingEngine:
    """序列化思考引擎"""
    
    def __init__(self, max_thoughts: int = 20):
        self.max_thoughts = max_thoughts
        self.sessions: Dict[str, ThinkingSession] = {}
        self.current_session: Optional[ThinkingSession] = None
    
    def start_session(self, problem: str, session_id: Optional[str] = None) -> ThinkingSession:
        """开始一个新的思考会话"""
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = ThinkingSession(
            session_id=session_id,
            problem=problem
        )
        self.sessions[session_id] = session
        self.current_session = session
        return session
    
    def add_thought(self, content: str, thought_type: ThoughtType = ThoughtType.ANALYSIS,
                   next_thought_needed: bool = True, session_id: Optional[str] = None) -> Thought:
        """添加一个思考步骤"""
        session = self._get_session(session_id)
        
        thought_number = len(session.thoughts) + 1
        total_thoughts = max(thought_number + (1 if next_thought_needed else 0), session.thoughts[-1].total_thoughts if session.thoughts else thought_number)
        
        thought = Thought(
            thought_number=thought_number,
            total_thoughts=total_thoughts,
            content=content,
            thought_type=thought_type,
            next_thought_needed=next_thought_needed
        )
        
        session.thoughts.append(thought)
        
        # 检查是否完成
        if not next_thought_needed or thought_number >= self.max_thoughts:
            session.completed = True
            if thought_type == ThoughtType.CONCLUSION:
                session.conclusion = content
        
        return thought
    
    def revise_thought(self, thought_number: int, new_content: str,
                      session_id: Optional[str] = None) -> Thought:
        """修订一个已有的思考"""
        session = self._get_session(session_id)
        
        if thought_number < 1 or thought_number > len(session.thoughts):
            raise ValueError(f"Invalid thought number: {thought_number}")
        
        revision = Thought(
            thought_number=len(session.thoughts) + 1,
            total_thoughts=len(session.thoughts) + 1,
            content=new_content,
            thought_type=ThoughtType.REVISION,
            next_thought_needed=True,
            is_revision=True,
            revises_thought=thought_number
        )
        
        session.thoughts.append(revision)
        return revision
    
    def branch_thought(self, from_thought_number: int, branch_id: str,
                      content: str, session_id: Optional[str] = None) -> Thought:
        """从某个思考创建分支"""
        session = self._get_session(session_id)
        
        if from_thought_number < 1 or from_thought_number > len(session.thoughts):
            raise ValueError(f"Invalid thought number: {from_thought_number}")
        
        # 保存当前分支
        if session.current_branch not in session.branches:
            session.branches[session.current_branch] = session.thoughts.copy()
        
        # 创建新分支
        branch_thought = Thought(
            thought_number=1,
            total_thoughts=1,
            content=content,
            thought_type=ThoughtType.BRANCH,
            next_thought_needed=True,
            branch_from_thought=from_thought_number,
            branch_id=branch_id
        )
        
        session.branches[branch_id] = [branch_thought]
        session.current_branch = branch_id
        session.thoughts = [branch_thought]
        
        return branch_thought
    
    def extend_thinking(self, additional_thoughts: int, session_id: Optional[str] = None):
        """扩展思考步骤数"""
        session = self._get_session(session_id)
        
        if session.thoughts:
            last_thought = session.thoughts[-1]
            last_thought.total_thoughts += additional_thoughts
            last_thought.needs_more_thoughts = True
    
    def get_thinking_chain(self, session_id: Optional[str] = None) -> List[Thought]:
        """获取思考链"""
        session = self._get_session(session_id)
        return session.thoughts.copy()
    
    def get_formatted_chain(self, session_id: Optional[str] = None) -> str:
        """获取格式化的思考链"""
        session = self._get_session(session_id)
        lines = [f"🧠 思考会话: {session.session_id}", f"问题: {session.problem}", ""]
        
        for thought in session.thoughts:
            prefix = "  " * (thought.thought_number - 1)
            emoji = self._get_thought_emoji(thought)
            
            if thought.is_revision:
                lines.append(f"{prefix}🔄 修订 #{thought.revises_thought}: {thought.content[:50]}...")
            elif thought.branch_id:
                lines.append(f"{prefix}🌿 分支 [{thought.branch_id}]: {thought.content[:50]}...")
            else:
                lines.append(f"{prefix}{emoji} 思考 {thought.thought_number}/{thought.total_thoughts}: {thought.content[:50]}...")
        
        if session.conclusion:
            lines.append(f"\n✅ 结论: {session.conclusion}")
        
        return "\n".join(lines)
    
    def _get_session(self, session_id: Optional[str] = None) -> ThinkingSession:
        """获取会话"""
        if session_id:
            if session_id not in self.sessions:
                raise ValueError(f"Session not found: {session_id}")
            return self.sessions[session_id]
        
        if self.current_session is None:
            raise ValueError("No active session")
        
        return self.current_session
    
    def _get_thought_emoji(self, thought: Thought) -> str:
        """获取思考类型的 emoji"""
        emojis = {
            ThoughtType.ANALYSIS: "🔍",
            ThoughtType.HYPOTHESIS: "💡",
            ThoughtType.VERIFICATION: "✅",
            ThoughtType.REVISION: "🔄",
            ThoughtType.BRANCH: "🌿",
            ThoughtType.CONCLUSION: "🎯"
        }
        return emojis.get(thought.thought_type, "💭")
    
    def save_session(self, filepath: str, session_id: Optional[str] = None):
        """保存会话"""
        session = self._get_session(session_id)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)


class SequentialThinkingTool:
    """Sequential Thinking Tool - 供 Agent 使用"""
    
    def __init__(self, max_thoughts: int = 20):
        self.engine = SequentialThinkingEngine(max_thoughts=max_thoughts)
        self.active = False
    
    def start(self, problem: str) -> str:
        """开始思考"""
        self.active = True
        session = self.engine.start_session(problem)
        return f"开始思考会话: {session.session_id}\n问题: {problem}\n\n请使用 think() 添加第一个思考。"
    
    def think(self, thought: str, thought_type: str = "analysis",
             next_thought_needed: bool = True) -> str:
        """添加思考"""
        if not self.active:
            return "错误: 没有活动的思考会话，请先调用 start()"
        
        try:
            t_type = ThoughtType(thought_type)
        except ValueError:
            t_type = ThoughtType.ANALYSIS
        
        thought_obj = self.engine.add_thought(
            content=thought,
            thought_type=t_type,
            next_thought_needed=next_thought_needed
        )
        
        result = f"思考 {thought_obj.thought_number}/{thought_obj.total_thoughts} 已记录"
        if next_thought_needed:
            result += "\n请继续思考..."
        else:
            result += "\n思考完成！"
            self.active = False
        
        return result
    
    def revise(self, thought_number: int, new_thought: str) -> str:
        """修订思考"""
        if not self.active:
            return "错误: 没有活动的思考会话"
        
        revision = self.engine.revise_thought(thought_number, new_thought)
        return f"已修订思考 #{thought_number}，新思考编号: {revision.thought_number}"
    
    def branch(self, from_thought: int, branch_id: str, thought: str) -> str:
        """创建分支"""
        if not self.active:
            return "错误: 没有活动的思考会话"
        
        branch_thought = self.engine.branch_thought(from_thought, branch_id, thought)
        return f"已创建分支 '{branch_id}'，从思考 #{from_thought} 开始"
    
    def extend(self, additional: int) -> str:
        """扩展思考"""
        if not self.active:
            return "错误: 没有活动的思考会话"
        
        self.engine.extend_thinking(additional)
        return f"已扩展 {additional} 个思考步骤"
    
    def get_summary(self) -> str:
        """获取摘要"""
        return self.engine.get_formatted_chain()
    
    def conclude(self, conclusion: str) -> str:
        """得出结论"""
        if not self.active:
            return "错误: 没有活动的思考会话"
        
        self.engine.add_thought(
            content=conclusion,
            thought_type=ThoughtType.CONCLUSION,
            next_thought_needed=False
        )
        self.active = False
        
        return f"思考完成！\n结论: {conclusion}\n\n{self.get_summary()}"


# 便捷函数
def create_sequential_thinking(max_thoughts: int = 20) -> SequentialThinkingTool:
    """创建序列化思考工具"""
    return SequentialThinkingTool(max_thoughts=max_thoughts)
