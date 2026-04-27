"""
Sequential Thinking Tool - 序列化思考工具

帮助 AI 进行多步骤推理，支持动态调整、修订和分支思考
"""
from typing import Optional
from code_gen.tools.base import Tool, ToolResult
from code_gen.features import (
    SequentialThinkingEngine, ThoughtType, Thought
)


class SequentialThinkingTool(Tool):
    """
    序列化思考工具 - 用于复杂问题的多步骤推理
    
    功能：
    - 分解复杂问题为多个思考步骤
    - 支持修订之前的思考
    - 支持从某个思考点创建分支
    - 动态扩展思考步骤
    
    适用场景：
    - 复杂问题分析
    - 调试和故障排查
    - 方案设计和评估
    - 代码审查和改进建议
    """
    
    name = "sequentialthinking"
    description = """进行序列化思考，将复杂问题分解为多个步骤进行推理。

这个工具帮助你对复杂问题进行结构化思考，支持：
- 分步骤分析和推理
- 修订之前的思考
- 创建思考分支探索不同方案
- 动态调整思考深度

使用场景：
- 复杂问题诊断
- 方案设计
- 代码审查
- 调试分析
"""
    
    input_schema = {
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "当前思考步骤的内容",
            },
            "thought_number": {
                "type": "integer",
                "description": "当前思考步骤的序号（从1开始，默认：1）",
                "default": 1,
            },
            "total_thoughts": {
                "type": "integer",
                "description": "预计总共需要的思考步骤数（默认：3）",
                "default": 3,
            },
            "next_thought_needed": {
                "type": "boolean",
                "description": "是否还需要继续思考（默认：true）",
                "default": True,
            },
            "thought_type": {
                "type": "string",
                "enum": ["analysis", "hypothesis", "verification", "revision", "branch", "conclusion"],
                "description": "思考类型：analysis(分析), hypothesis(假设), verification(验证), revision(修订), branch(分支), conclusion(结论)",
                "default": "analysis",
            },
            "is_revision": {
                "type": "boolean",
                "description": "是否是修订之前的思考",
                "default": False,
            },
            "revises_thought": {
                "type": "integer",
                "description": "如果是修订，指定修订哪个思考步骤",
            },
            "branch_from_thought": {
                "type": "integer",
                "description": "如果是分支，指定从哪个思考步骤分支",
            },
            "branch_id": {
                "type": "string",
                "description": "分支ID（创建分支时使用）",
            },
            "session_id": {
                "type": "string",
                "description": "思考会话ID（可选，用于多会话管理）",
            },
        },
        "required": ["thought"],
    }
    
    def __init__(self):
        super().__init__()
        self.engine = SequentialThinkingEngine(max_thoughts=20)
    
    async def execute(
        self,
        thought: str,
        thought_number: int = 1,
        total_thoughts: int = 3,
        next_thought_needed: bool = True,
        thought_type: str = "analysis",
        is_revision: bool = False,
        revises_thought: Optional[int] = None,
        branch_from_thought: Optional[int] = None,
        branch_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ToolResult:
        """执行序列化思考"""
        try:
            # 获取或创建会话
            if session_id and session_id in self.engine.sessions:
                session = self.engine.sessions[session_id]
                self.engine.current_session = session
            elif not self.engine.current_session:
                session = self.engine.start_session(
                    problem="Sequential thinking session",
                    session_id=session_id
                )
            else:
                session = self.engine.current_session
            
            # 转换思考类型
            try:
                t_type = ThoughtType(thought_type.lower())
            except ValueError:
                t_type = ThoughtType.ANALYSIS
            
            # 处理修订
            if is_revision and revises_thought:
                result_thought = self.engine.revise_thought(
                    thought_number=revises_thought,
                    new_content=thought,
                    session_id=session.session_id
                )
                action = "修订思考"
            # 处理分支
            elif branch_from_thought and branch_id:
                result_thought = self.engine.branch_thought(
                    from_thought_number=branch_from_thought,
                    branch_id=branch_id,
                    content=thought,
                    session_id=session.session_id
                )
                action = "创建分支"
            # 正常添加思考
            else:
                result_thought = self.engine.add_thought(
                    content=thought,
                    thought_type=t_type,
                    next_thought_needed=next_thought_needed,
                    session_id=session.session_id
                )
                action = "添加思考"
            
            # 构建结果
            progress = f"({result_thought.thought_number}/{total_thoughts})"
            status = "✅ 思考完成" if not next_thought_needed else "🔄 继续思考..."
            
            result_text = f"""{action} {progress}

💭 思考内容: {thought}
📊 类型: {thought_type}
📈 进度: {result_thought.thought_number} / {total_thoughts}
🔄 状态: {status}
"""
            
            # 如果是修订或分支，添加相关信息
            if is_revision and revises_thought:
                result_text += f"📝 修订自: 思考 #{revises_thought}\n"
            if branch_from_thought:
                result_text += f"🌿 分支自: 思考 #{branch_from_thought} (分支ID: {branch_id})\n"
            
            # 获取当前思考链
            chain = self.engine.get_thinking_chain(session.session_id)
            if len(chain) > 1:
                result_text += f"\n📋 思考链 ({len(chain)} 步):\n"
                for i, t in enumerate(chain[-5:], 1):  # 显示最近5步
                    prefix = "🔄" if t.is_revision else "🌿" if t.branch_id else "💭"
                    result_text += f"  {prefix} #{t.thought_number}: {t.content[:50]}...\n"
            
            return ToolResult(
                success=True,
                content=result_text,
                data={
                    "session_id": session.session_id,
                    "thought": result_thought.to_dict(),
                    "chain_length": len(chain),
                    "completed": session.completed
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"序列化思考失败: {str(e)}"
            )


class GetThinkingChainTool(Tool):
    """获取思考链工具"""
    
    name = "get_thinking_chain"
    description = "获取当前的思考链，查看所有思考步骤"
    
    input_schema = {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "思考会话ID",
            },
        },
        "required": [],
    }
    
    def __init__(self, engine: SequentialThinkingEngine):
        super().__init__()
        self.engine = engine
    
    async def execute(self, session_id: Optional[str] = None) -> ToolResult:
        """获取思考链"""
        try:
            chain = self.engine.get_thinking_chain(session_id)
            
            if not chain:
                return ToolResult(
                    success=True,
                    content="暂无思考记录",
                    data={"chain": []}
                )
            
            result_text = f"📋 思考链 ({len(chain)} 步):\n\n"
            for thought in chain:
                prefix = "🔄" if thought.is_revision else "🌿" if thought.branch_id else "💭"
                type_emoji = {
                    "analysis": "🔍",
                    "hypothesis": "💡",
                    "verification": "✅",
                    "revision": "📝",
                    "branch": "🌿",
                    "conclusion": "🎯"
                }.get(thought.thought_type.value, "💭")
                
                result_text += f"{prefix} {type_emoji} 思考 #{thought.thought_number}/{thought.total_thoughts}\n"
                result_text += f"   类型: {thought.thought_type.value}\n"
                result_text += f"   内容: {thought.content}\n"
                if thought.is_revision:
                    result_text += f"   修订自: #{thought.revises_thought}\n"
                if thought.branch_id:
                    result_text += f"   分支ID: {thought.branch_id}\n"
                result_text += "\n"
            
            return ToolResult(
                success=True,
                content=result_text,
                data={
                    "chain": [t.to_dict() for t in chain],
                    "total_thoughts": len(chain)
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"获取思考链失败: {str(e)}"
            )
