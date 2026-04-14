"""
Agent Handoffs - 代理交接系统
Inspired by PraisonAI's Handoff System

代理交接使 Agent 能够将任务动态委托给其他专业 Agent，
构建复杂的多代理系统，每个 Agent 专注于其专业领域。
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Callable, Union, Type, TYPE_CHECKING
from dataclasses import dataclass, field
from pathlib import Path
import json
from pydantic import BaseModel

if TYPE_CHECKING:
    from .agent import Agent


@dataclass
class HandoffConfig:
    """代理交接配置"""
    target_agent: Agent  # 目标代理
    name: Optional[str] = None  # 交接工具名称
    description: Optional[str] = None  # 交接工具描述
    input_model: Optional[Type[BaseModel]] = None  # 结构化输入模型
    callback: Optional[Callable[[str, str, Dict], bool]] = None  # 回调函数
    filter_history: bool = True  # 是否过滤历史记录
    keep_last_n_messages: Optional[int] = None  # 保留最近N条消息
    
    def __post_init__(self):
        """初始化后处理"""
        if self.name is None:
            self.name = f"handoff_to_{self.target_agent.name}"
        if self.description is None:
            self.description = f"将对话交接给 {self.target_agent.name} ({self.target_agent.role})"


class HandoffManager:
    """
    代理交接管理器
    
    管理 Agent 之间的任务交接，支持：
    1. 动态任务委派
    2. 上下文传递
    3. 回调处理
    4. 历史记录过滤
    """
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.handoff_history: List[Dict[str, Any]] = []
        self.current_agent: Optional[Agent] = None
        self.conversation_context: List[Dict[str, str]] = []
    
    def register_handoffs(
        self,
        agent: Agent,
        handoff_configs: List[HandoffConfig]
    ) -> Dict[str, Any]:
        """
        为 Agent 注册交接能力
        
        Args:
            agent: 源代理
            handoff_configs: 交接配置列表
            
        Returns:
            交接工具定义（用于工具注册）
        """
        tools = []
        
        for config in handoff_configs:
            tool_def = self._create_handoff_tool(config)
            tools.append(tool_def)
        
        # 更新 Agent 的系统提示词，添加交接说明
        handoff_names = [c.name for c in handoff_configs]
        handoff_instruction = self._create_handoff_instruction(handoff_configs)
        
        return {
            "tools": tools,
            "instruction": handoff_instruction,
            "configs": {c.name: c for c in handoff_configs}
        }
    
    def _create_handoff_tool(self, config: HandoffConfig) -> Dict[str, Any]:
        """创建交接工具定义"""
        tool = {
            "type": "function",
            "function": {
                "name": config.name,
                "description": config.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "传递给目标代理的消息或上下文"
                        },
                        "reason": {
                            "type": "string",
                            "description": "交接原因"
                        }
                    },
                    "required": ["message"]
                }
            }
        }
        
        # 如果有结构化输入模型，使用模型定义参数
        if config.input_model:
            tool["function"]["parameters"] = config.input_model.schema()
        
        return tool
    
    def _create_handoff_instruction(self, configs: List[HandoffConfig]) -> str:
        """创建交接指令说明"""
        lines = [
            "\n【代理交接能力】",
            "你可以将任务交接给以下专业代理：",
            ""
        ]
        
        for config in configs:
            lines.append(f"- {config.name}: {config.description}")
        
        lines.extend([
            "",
            "当你认为需要专业处理时，使用相应的交接工具。",
            "交接时会自动传递完整的对话上下文。"
        ])
        
        return "\n".join(lines)
    
    async def execute_handoff(
        self,
        from_agent: Agent,
        to_agent: Agent,
        message: str,
        context: Dict[str, Any],
        config: Optional[HandoffConfig] = None
    ) -> Dict[str, Any]:
        """
        执行代理交接
        
        Args:
            from_agent: 源代理
            to_agent: 目标代理
            message: 交接消息
            context: 当前上下文
            config: 交接配置
            
        Returns:
            交接结果
        """
        print(f"\n🔄 代理交接: {from_agent.name} → {to_agent.name}")
        print(f"   原因: {message[:100]}...")
        
        # 执行回调（如果有）
        if config and config.callback:
            try:
                allowed = config.callback(from_agent.name, to_agent.name, context)
                if not allowed:
                    print(f"   ❌ 交接被回调函数阻止")
                    return {
                        "success": False,
                        "error": "Handoff blocked by callback",
                        "from": from_agent.name,
                        "to": to_agent.name
                    }
            except Exception as e:
                print(f"   ⚠️ 回调执行失败: {e}")
        
        # 准备上下文
        filtered_context = self._filter_context(context, config)
        
        # 记录交接历史
        handoff_record = {
            "from": from_agent.name,
            "to": to_agent.name,
            "message": message,
            "timestamp": self._get_timestamp(),
            "context_summary": self._summarize_context(filtered_context)
        }
        self.handoff_history.append(handoff_record)
        
        # 构建交接提示词
        handoff_prompt = self._build_handoff_prompt(
            from_agent, to_agent, message, filtered_context
        )
        
        print(f"   ✅ 交接完成，上下文已传递")
        
        return {
            "success": True,
            "handoff_prompt": handoff_prompt,
            "target_agent": to_agent,
            "from": from_agent.name,
            "to": to_agent.name,
            "context": filtered_context
        }
    
    def _filter_context(
        self,
        context: Dict[str, Any],
        config: Optional[HandoffConfig]
    ) -> Dict[str, Any]:
        """过滤上下文"""
        if not config or not config.filter_history:
            return context
        
        filtered = context.copy()
        
        # 过滤历史记录
        if "history" in filtered and config.keep_last_n_messages:
            filtered["history"] = filtered["history"][-config.keep_last_n_messages:]
        
        return filtered
    
    def _build_handoff_prompt(
        self,
        from_agent: Agent,
        to_agent: Agent,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """构建交接提示词"""
        lines = [
            f"【任务交接】",
            f"",
            f"你从 {from_agent.name} ({from_agent.role}) 接收了任务交接。",
            f"",
            f"交接原因: {message}",
            f"",
            f"你的角色: {to_agent.role}",
            f"你的目标: {to_agent.goal}",
            f"",
        ]
        
        # 添加上下文摘要
        if context.get("history"):
            lines.extend([
                "对话历史:",
                "---"
            ])
            for msg in context["history"][-5:]:  # 最近5条
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:200]
                lines.append(f"{role}: {content}...")
            lines.append("---")
        
        lines.extend([
            "",
            "请基于以上上下文继续处理任务。"
        ])
        
        return "\n".join(lines)
    
    def _summarize_context(self, context: Dict[str, Any]) -> str:
        """摘要上下文"""
        history = context.get("history", [])
        return f"{len(history)} messages"
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_handoff_history(self) -> List[Dict[str, Any]]:
        """获取交接历史"""
        return self.handoff_history.copy()
    
    def clear_history(self):
        """清空交接历史"""
        self.handoff_history.clear()


class HandoffAgentMixin:
    """
    支持交接功能的 Agent Mixin
    
    为 Agent 添加交接能力
    """
    
    def __init__(self):
        self.handoff_configs: List[HandoffConfig] = []
        self.handoff_manager: Optional[HandoffManager] = None
        self._handoff_tools: Dict[str, Any] = {}
    
    def enable_handoffs(
        self,
        handoff_configs: List[HandoffConfig],
        handoff_manager: HandoffManager
    ):
        """
        启用交接功能
        
        Args:
            handoff_configs: 可交接的目标代理配置
            handoff_manager: 交接管理器
        """
        self.handoff_configs = handoff_configs
        self.handoff_manager = handoff_manager
        
        # 注册交接工具
        registration = handoff_manager.register_handoffs(
            self,  # type: ignore
            handoff_configs
        )
        
        self._handoff_tools = registration["configs"]
        
        # 更新系统提示词
        if hasattr(self, 'system_prompt'):
            self.system_prompt += registration["instruction"]  # type: ignore
        
        print(f"✅ {self.name} 已启用交接功能，可交接给: {[c.target_agent.name for c in handoff_configs]}")  # type: ignore
    
    async def handoff_to(
        self,
        target_agent_name: str,
        message: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        交接给指定代理
        
        Args:
            target_agent_name: 目标代理名称
            message: 交接消息
            context: 当前上下文
            
        Returns:
            交接结果
        """
        if not self.handoff_manager:
            raise RuntimeError("交接功能未启用，请先调用 enable_handoffs()")
        
        # 查找配置
        config = None
        for cfg in self.handoff_configs:
            if cfg.target_agent.name == target_agent_name:
                config = cfg
                break
        
        if not config:
            available = [c.target_agent.name for c in self.handoff_configs]
            raise ValueError(f"无法交接给 {target_agent_name}，可用目标: {available}")
        
        # 执行交接
        return await self.handoff_manager.execute_handoff(
            from_agent=self,  # type: ignore
            to_agent=config.target_agent,
            message=message,
            context=context,
            config=config
        )


def create_handoff(
    agent: Agent,
    name: Optional[str] = None,
    description: Optional[str] = None,
    callback: Optional[Callable] = None,
    input_model: Optional[Type[BaseModel]] = None
) -> HandoffConfig:
    """
    便捷函数：创建交接配置
    
    Args:
        agent: 目标代理
        name: 交接工具名称
        description: 交接工具描述
        callback: 回调函数
        input_model: 结构化输入模型
        
    Returns:
        交接配置
        
    Example:
        >>> billing_agent = Agent(name="Billing", ...)
        >>> handoff_config = create_handoff(
        ...     agent=billing_agent,
        ...     name="transfer_to_billing",
        ...     description="将账单问题转给账单专家"
        ... )
    """
    return HandoffConfig(
        target_agent=agent,
        name=name,
        description=description,
        callback=callback,
        input_model=input_model
    )


# 便捷函数别名
handoff = create_handoff
