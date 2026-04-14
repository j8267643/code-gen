"""
Human-in-the-loop (HITL) - 人机协作系统
Inspired by PraisonAI's Human-in-the-loop

在 AI Agent 工作流程中引入人类干预：
1. 审批请求 - 关键操作需要人类确认
2. 内容审核 - 敏感/重要内容人工检查
3. 异常处理 - AI 不确定时求助人类
4. 反馈收集 - 收集人类反馈改进 AI

支持配置化开关，可灵活启用/禁用
"""
from typing import Dict, Any, List, Optional, Callable, Union, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime


class HITLMode(Enum):
    """人机协作模式"""
    DISABLED = "disabled"           # 完全禁用，自动通过
    AUTO = "auto"                   # 自动模式，仅在必要时触发
    MANUAL = "manual"               # 手动模式，所有关键操作都触发
    AUDIT = "audit"                 # 审计模式，记录但不阻塞


class HITLResponseType(Enum):
    """人类响应类型"""
    APPROVED = "approved"           # 批准
    REJECTED = "rejected"           # 拒绝
    MODIFIED = "modified"           # 修改后批准
    NEEDS_INFO = "needs_info"       # 需要更多信息
    TIMEOUT = "timeout"             # 超时


@dataclass
class HITLConfig:
    """人机协作配置"""
    enabled: bool = True                    # 是否启用 HITL
    mode: HITLMode = HITLMode.AUTO          # 协作模式
    timeout: int = 300                      # 默认超时时间（秒）
    
    # 触发条件配置
    trigger_on_dangerous_code: bool = True  # 危险代码触发
    trigger_on_file_operations: bool = True # 文件操作触发
    trigger_on_low_confidence: bool = True  # 低置信度触发
    trigger_on_api_cost: bool = True        # API 成本触发
    confidence_threshold: float = 0.7       # 置信度阈值
    api_cost_threshold: float = 10.0        # API 成本阈值（美元）
    
    # 自动审批配置（用于 AUTO 模式）
    auto_approve_safe_operations: bool = True   # 自动批准安全操作
    auto_approve_low_cost: bool = True          # 自动批准低成本操作
    low_cost_threshold: float = 1.0             # 低成本阈值
    
    # 回调函数
    on_approval: Optional[Callable] = None      # 批准回调
    on_rejection: Optional[Callable] = None     # 拒绝回调
    on_timeout: Optional[Callable] = None       # 超时回调


@dataclass
class HITLRequest:
    """人机协作请求"""
    id: str                                 # 请求ID
    title: str                              # 标题
    content: str                            # 内容
    request_type: str                       # 请求类型
    context: Dict[str, Any] = field(default_factory=dict)
    options: List[str] = field(default_factory=list)
    timeout: int = 300
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 触发原因
    trigger_reason: str = ""                # 触发原因
    severity: str = "medium"                # 严重程度: low, medium, high, critical


@dataclass
class HITLResponse:
    """人机协作响应"""
    request_id: str                         # 对应请求ID
    response_type: HITLResponseType         # 响应类型
    feedback: Optional[str] = None          # 反馈内容
    modified_content: Optional[str] = None  # 修改后的内容
    responder: Optional[str] = None         # 响应者
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class HITLHandler(ABC):
    """人机协作处理器基类"""
    
    @abstractmethod
    async def request_approval(self, request: HITLRequest) -> HITLResponse:
        """请求审批"""
        pass
    
    @abstractmethod
    async def request_input(self, request: HITLRequest) -> HITLResponse:
        """请求输入"""
        pass
    
    @abstractmethod
    async def notify(self, request: HITLRequest) -> None:
        """发送通知（无需响应）"""
        pass


class ConsoleHITLHandler(HITLHandler):
    """控制台人机协作处理器"""
    
    def __init__(self, config: Optional[HITLConfig] = None):
        self.config = config or HITLConfig()
        self.pending_requests: Dict[str, HITLRequest] = {}
    
    async def request_approval(self, request: HITLRequest) -> HITLResponse:
        """控制台请求审批"""
        print(f"\n{'='*60}")
        print(f"🤖 AI 请求人类确认")
        print(f"{'='*60}")
        print(f"标题: {request.title}")
        print(f"类型: {request.request_type}")
        print(f"严重程度: {request.severity}")
        if request.trigger_reason:
            print(f"触发原因: {request.trigger_reason}")
        print(f"\n内容:\n{request.content}")
        print(f"{'='*60}")
        
        # 显示选项
        options = request.options or ["批准 (y)", "拒绝 (n)", "修改 (m)"]
        print(f"\n选项: {', '.join(options)}")
        
        # 获取用户输入（在异步环境中使用线程）
        loop = asyncio.get_event_loop()
        user_input = await loop.run_in_executor(
            None, 
            lambda: input("\n您的选择: ").strip().lower()
        )
        
        # 解析响应
        if user_input in ['y', 'yes', '批准', '1']:
            return HITLResponse(
                request_id=request.id,
                response_type=HITLResponseType.APPROVED
            )
        elif user_input in ['n', 'no', '拒绝', '2']:
            feedback = await loop.run_in_executor(
                None,
                lambda: input("拒绝原因（可选）: ").strip()
            )
            return HITLResponse(
                request_id=request.id,
                response_type=HITLResponseType.REJECTED,
                feedback=feedback or None
            )
        elif user_input in ['m', 'modify', '修改', '3']:
            modified = await loop.run_in_executor(
                None,
                lambda: input("请输入修改后的内容: ").strip()
            )
            return HITLResponse(
                request_id=request.id,
                response_type=HITLResponseType.MODIFIED,
                modified_content=modified
            )
        else:
            print("未识别的输入，默认拒绝")
            return HITLResponse(
                request_id=request.id,
                response_type=HITLResponseType.REJECTED,
                feedback="未识别的响应"
            )
    
    async def request_input(self, request: HITLRequest) -> HITLResponse:
        """控制台请求输入"""
        print(f"\n{'='*60}")
        print(f"🤖 AI 需要您的帮助")
        print(f"{'='*60}")
        print(f"问题: {request.title}")
        print(f"\n{request.content}")
        
        if request.options:
            print(f"\n选项:")
            for i, option in enumerate(request.options, 1):
                print(f"  {i}. {option}")
        
        loop = asyncio.get_event_loop()
        user_input = await loop.run_in_executor(
            None,
            lambda: input("\n您的回答: ").strip()
        )
        
        return HITLResponse(
            request_id=request.id,
            response_type=HITLResponseType.APPROVED,
            feedback=user_input
        )
    
    async def notify(self, request: HITLRequest) -> None:
        """控制台通知"""
        print(f"\n{'='*60}")
        print(f"🔔 AI 通知")
        print(f"{'='*60}")
        print(f"标题: {request.title}")
        print(f"{request.content}")
        print(f"{'='*60}\n")


class AutoHITLHandler(HITLHandler):
    """自动人机协作处理器（无需人类干预）"""
    
    def __init__(self, config: Optional[HITLConfig] = None):
        self.config = config or HITLConfig()
    
    async def request_approval(self, request: HITLRequest) -> HITLResponse:
        """自动审批（基于规则）"""
        # 根据严重程度自动决定
        if request.severity in ['low', 'medium']:
            return HITLResponse(
                request_id=request.id,
                response_type=HITLResponseType.APPROVED,
                feedback="自动批准（低/中风险）"
            )
        else:
            # 高风险需要人工，但这里是自动处理器，所以拒绝
            return HITLResponse(
                request_id=request.id,
                response_type=HITLResponseType.REJECTED,
                feedback="高风险操作需要人工审核（自动处理器无法处理）"
            )
    
    async def request_input(self, request: HITLRequest) -> HITLResponse:
        """自动返回默认值"""
        return HITLResponse(
            request_id=request.id,
            response_type=HITLResponseType.APPROVED,
            feedback="自动响应（无人工输入）"
        )
    
    async def notify(self, request: HITLRequest) -> None:
        """自动模式不显示通知"""
        pass


class HumanInTheLoop:
    """
    人机协作管理器
    
    管理 AI 与人类的交互，支持多种模式和处理器
    """
    
    def __init__(self, config: Optional[HITLConfig] = None, 
                 handler: Optional[HITLHandler] = None):
        self.config = config or HITLConfig()
        self.handler = handler or ConsoleHITLHandler(self.config)
        self.request_history: List[HITLRequest] = []
        self.response_history: List[HITLResponse] = []
        self._request_counter = 0
    
    def _generate_id(self) -> str:
        """生成请求ID"""
        self._request_counter += 1
        return f"hitl_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._request_counter}"
    
    def is_enabled(self) -> bool:
        """检查是否启用人机协作"""
        return self.config.enabled and self.config.mode != HITLMode.DISABLED
    
    def should_trigger(self, trigger_type: str, context: Dict[str, Any] = None) -> bool:
        """
        检查是否应该触发人机协作
        
        Args:
            trigger_type: 触发类型
            context: 上下文信息
        """
        if not self.is_enabled():
            return False
        
        if self.config.mode == HITLMode.MANUAL:
            return True
        
        if self.config.mode == HITLMode.AUDIT:
            return False  # 审计模式只记录，不阻塞
        
        # AUTO 模式：根据条件判断
        context = context or {}
        
        if trigger_type == "dangerous_code" and self.config.trigger_on_dangerous_code:
            return True
        
        if trigger_type == "file_operation" and self.config.trigger_on_file_operations:
            return True
        
        if trigger_type == "low_confidence" and self.config.trigger_on_low_confidence:
            confidence = context.get("confidence", 1.0)
            if confidence < self.config.confidence_threshold:
                return True
        
        if trigger_type == "api_cost" and self.config.trigger_on_api_cost:
            cost = context.get("estimated_cost", 0)
            if cost > self.config.api_cost_threshold:
                return True
        
        return False
    
    async def request_approval(
        self,
        title: str,
        content: str,
        request_type: str = "approval",
        context: Optional[Dict[str, Any]] = None,
        options: Optional[List[str]] = None,
        severity: str = "medium",
        trigger_reason: str = ""
    ) -> HITLResponse:
        """
        请求人类审批
        
        Args:
            title: 标题
            content: 内容
            request_type: 请求类型
            context: 上下文
            options: 选项列表
            severity: 严重程度
            trigger_reason: 触发原因
            
        Returns:
            HITLResponse: 人类响应
        """
        # 如果禁用，自动通过
        if not self.is_enabled():
            return HITLResponse(
                request_id="auto",
                response_type=HITLResponseType.APPROVED,
                feedback="HITL 已禁用，自动批准"
            )
        
        # 审计模式：记录但不阻塞
        if self.config.mode == HITLMode.AUDIT:
            request = HITLRequest(
                id=self._generate_id(),
                title=title,
                content=content,
                request_type=request_type,
                context=context or {},
                options=options or [],
                severity=severity,
                trigger_reason=trigger_reason
            )
            self.request_history.append(request)
            return HITLResponse(
                request_id=request.id,
                response_type=HITLResponseType.APPROVED,
                feedback="审计模式：自动批准"
            )
        
        # 创建请求
        request = HITLRequest(
            id=self._generate_id(),
            title=title,
            content=content,
            request_type=request_type,
            context=context or {},
            options=options,
            severity=severity,
            trigger_reason=trigger_reason
        )
        self.request_history.append(request)
        
        # 发送请求并等待响应
        try:
            response = await asyncio.wait_for(
                self.handler.request_approval(request),
                timeout=self.config.timeout
            )
            self.response_history.append(response)
            
            # 执行回调
            if response.response_type == HITLResponseType.APPROVED and self.config.on_approval:
                self.config.on_approval(request, response)
            elif response.response_type == HITLResponseType.REJECTED and self.config.on_rejection:
                self.config.on_rejection(request, response)
            
            return response
            
        except asyncio.TimeoutError:
            if self.config.on_timeout:
                self.config.on_timeout(request)
            return HITLResponse(
                request_id=request.id,
                response_type=HITLResponseType.TIMEOUT,
                feedback="请求超时"
            )
    
    async def request_input(
        self,
        title: str,
        content: str,
        options: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> HITLResponse:
        """请求人类输入"""
        if not self.is_enabled():
            return HITLResponse(
                request_id="auto",
                response_type=HITLResponseType.APPROVED,
                feedback="HITL 已禁用"
            )
        
        request = HITLRequest(
            id=self._generate_id(),
            title=title,
            content=content,
            request_type="input",
            context=context or {},
            options=options or []
        )
        self.request_history.append(request)
        
        try:
            response = await asyncio.wait_for(
                self.handler.request_input(request),
                timeout=self.config.timeout
            )
            self.response_history.append(response)
            return response
        except asyncio.TimeoutError:
            return HITLResponse(
                request_id=request.id,
                response_type=HITLResponseType.TIMEOUT,
                feedback="请求超时"
            )
    
    async def notify(
        self,
        title: str,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """发送通知"""
        if not self.is_enabled():
            return
        
        request = HITLRequest(
            id=self._generate_id(),
            title=title,
            content=content,
            request_type="notification",
            context=context or {}
        )
        self.request_history.append(request)
        await self.handler.notify(request)
    
    def get_history(self) -> List[Dict[str, Any]]:
        """获取历史记录"""
        history = []
        for req in self.request_history:
            # 查找对应的响应
            resp = next(
                (r for r in self.response_history if r.request_id == req.id),
                None
            )
            history.append({
                "request": req,
                "response": resp
            })
        return history
    
    def clear_history(self) -> None:
        """清空历史记录"""
        self.request_history.clear()
        self.response_history.clear()


# ========== 便捷函数 ==========

def create_hitl(
    enabled: bool = True,
    mode: str = "auto",
    timeout: int = 300,
    **kwargs
) -> HumanInTheLoop:
    """
    便捷函数：创建人机协作管理器
    
    Args:
        enabled: 是否启用
        mode: 模式 (disabled, auto, manual, audit)
        timeout: 超时时间
        **kwargs: 其他配置参数
        
    Returns:
        HumanInTheLoop 实例
    """
    config = HITLConfig(
        enabled=enabled,
        mode=HITLMode(mode),
        timeout=timeout,
        **kwargs
    )
    return HumanInTheLoop(config)


def create_disabled_hitl() -> HumanInTheLoop:
    """创建禁用的 HITL（自动通过所有请求）"""
    return create_hitl(enabled=False)


def create_manual_hitl(timeout: int = 300) -> HumanInTheLoop:
    """创建手动模式 HITL（所有请求都需人工确认）"""
    return create_hitl(mode="manual", timeout=timeout)
