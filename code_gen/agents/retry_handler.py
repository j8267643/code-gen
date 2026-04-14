"""
Retry Handler - 增强重试处理器

基于 GSD-2 的 RetryHandler 设计，提供：
1. 指数退避策略
2. 可重试错误类型识别
3. 凭证轮换支持
4. Provider 回退机制
5. 详细的重试统计

使用示例:
    >>> from retry_handler import RetryHandler, RetryConfig
    >>> 
    >>> config = RetryConfig(
    ...     max_retries=3,
    ...     base_delay=1.0,
    ...     max_delay=30.0,
    ...     exponential_base=2.0
    ... )
    >>> 
    >>> handler = RetryHandler(config)
    >>> 
    >>> # 使用装饰器
    >>> @handler.with_retry
    >>> async def api_call():
    ...     return await some_api.request()
    >>> 
    >>> # 使用上下文管理器
    >>> async with handler.attempt() as attempt:
    ...     result = await api_call()
"""
import asyncio
import random
import time
from typing import (
    Callable, TypeVar, Optional, List, Set, 
    Union, Any, Dict, Tuple, Type
)
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
import logging


T = TypeVar('T')


class RetryableErrorType(Enum):
    """可重试错误类型"""
    RATE_LIMIT = auto()      # 速率限制
    TIMEOUT = auto()         # 超时
    NETWORK = auto()         # 网络错误
    SERVER_ERROR = auto()    # 服务器错误 (5xx)
    SERVICE_UNAVAILABLE = auto()  # 服务不可用
    CONNECTION_RESET = auto()     # 连接重置
    UNKNOWN = auto()         # 未知


@dataclass
class RetryConfig:
    """
    重试配置
    
    Attributes:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数基数
        jitter: 是否添加随机抖动
        jitter_max: 最大抖动（秒）
        retryable_exceptions: 可重试的异常类型
        on_retry: 重试回调函数
        on_exhausted: 重试耗尽回调
    """
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_max: float = 1.0
    retryable_exceptions: Tuple[Type[Exception], ...] = field(default_factory=tuple)
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
    on_exhausted: Optional[Callable[[int, Exception], None]] = None
    
    def __post_init__(self):
        if not self.retryable_exceptions:
            # 默认可重试异常
            self.retryable_exceptions = (
                ConnectionError,
                TimeoutError,
                asyncio.TimeoutError,
                OSError,
            )


@dataclass
class RetryAttempt:
    """重试尝试记录"""
    attempt_number: int
    exception: Optional[Exception]
    delay: float
    timestamp: float = field(default_factory=time.time)
    error_type: RetryableErrorType = RetryableErrorType.UNKNOWN
    
    def __repr__(self) -> str:
        return f"RetryAttempt({self.attempt_number}, {self.error_type.name}, delay={self.delay:.2f}s)"


@dataclass
class RetryResult:
    """重试结果"""
    success: bool
    result: Any = None
    final_exception: Optional[Exception] = None
    attempts: List[RetryAttempt] = field(default_factory=list)
    total_duration: float = 0.0
    
    @property
    def attempt_count(self) -> int:
        """尝试次数"""
        return len(self.attempts)
    
    @property
    def last_error(self) -> Optional[str]:
        """最后错误信息"""
        if self.final_exception:
            return str(self.final_exception)
        if self.attempts and self.attempts[-1].exception:
            return str(self.attempts[-1].exception)
        return None


@dataclass
class CredentialInfo:
    """凭证信息"""
    key: str
    provider: str
    is_active: bool = True
    last_used: Optional[float] = None
    failure_count: int = 0
    
    def mark_used(self):
        """标记为已使用"""
        self.last_used = time.time()
    
    def mark_failed(self):
        """标记为失败"""
        self.failure_count += 1
        if self.failure_count >= 3:
            self.is_active = False
    
    def reset(self):
        """重置状态"""
        self.failure_count = 0
        self.is_active = True


class CredentialRotator:
    """
    凭证轮换器
    
    管理多个凭证，自动轮换以应对速率限制
    """
    
    def __init__(self):
        self._credentials: Dict[str, CredentialInfo] = {}
        self._current_index = 0
        self._lock = asyncio.Lock()
    
    def add_credential(self, key: str, provider: str) -> None:
        """添加凭证"""
        self._credentials[key] = CredentialInfo(key=key, provider=provider)
    
    async def get_next(self) -> Optional[CredentialInfo]:
        """获取下一个可用凭证"""
        async with self._lock:
            active_creds = [
                c for c in self._credentials.values() if c.is_active
            ]
            
            if not active_creds:
                # 重置所有凭证
                for cred in self._credentials.values():
                    cred.reset()
                active_creds = list(self._credentials.values())
            
            if not active_creds:
                return None
            
            # 轮询选择
            cred = active_creds[self._current_index % len(active_creds)]
            self._current_index += 1
            cred.mark_used()
            
            return cred
    
    def mark_failed(self, key: str) -> None:
        """标记凭证失败"""
        if key in self._credentials:
            self._credentials[key].mark_failed()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total": len(self._credentials),
            "active": sum(1 for c in self._credentials.values() if c.is_active),
            "credentials": {
                k: {
                    "provider": c.provider,
                    "is_active": c.is_active,
                    "failure_count": c.failure_count
                }
                for k, c in self._credentials.items()
            }
        }


class RetryHandler:
    """
    增强重试处理器
    
    支持指数退避、凭证轮换和 Provider 回退
    """
    
    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        credential_rotator: Optional[CredentialRotator] = None
    ):
        self.config = config or RetryConfig()
        self.credential_rotator = credential_rotator
        self._stats = {
            "total_attempts": 0,
            "successful_retries": 0,
            "failed_permanently": 0,
            "total_wait_time": 0.0
        }
        self._logger = logging.getLogger(__name__)
    
    def calculate_delay(self, attempt: int) -> float:
        """
        计算重试延迟
        
        使用指数退避 + 抖动
        """
        # 指数退避
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        
        # 限制最大延迟
        delay = min(delay, self.config.max_delay)
        
        # 添加抖动
        if self.config.jitter:
            jitter = random.uniform(0, self.config.jitter_max)
            delay += jitter
        
        return delay
    
    def classify_error(self, error: Exception) -> RetryableErrorType:
        """
        分类错误类型
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # 速率限制
        if any(kw in error_str for kw in ['rate limit', 'ratelimit', 'too many requests', '429']):
            return RetryableErrorType.RATE_LIMIT
        
        # 超时
        if any(kw in error_str for kw in ['timeout', 'timed out']):
            return RetryableErrorType.TIMEOUT
        
        # 网络错误
        if any(kw in error_str for kw in ['network', 'connection', 'dns', 'unreachable']):
            return RetryableErrorType.NETWORK
        
        # 服务器错误
        if any(kw in error_str for kw in ['500', '502', '503', '504', 'internal server error']):
            return RetryableErrorType.SERVER_ERROR
        
        # 服务不可用
        if any(kw in error_str for kw in ['unavailable', 'maintenance', 'overloaded']):
            return RetryableErrorType.SERVICE_UNAVAILABLE
        
        # 连接重置
        if any(kw in error_str for kw in ['reset', 'broken pipe']):
            return RetryableErrorType.CONNECTION_RESET
        
        return RetryableErrorType.UNKNOWN
    
    def is_retryable(self, error: Exception) -> bool:
        """
        检查错误是否可重试
        """
        # 检查异常类型
        if isinstance(error, self.config.retryable_exceptions):
            return True
        
        # 检查错误分类
        error_type = self.classify_error(error)
        return error_type in [
            RetryableErrorType.RATE_LIMIT,
            RetryableErrorType.TIMEOUT,
            RetryableErrorType.NETWORK,
            RetryableErrorType.SERVER_ERROR,
            RetryableErrorType.SERVICE_UNAVAILABLE,
            RetryableErrorType.CONNECTION_RESET
        ]
    
    async def execute(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> RetryResult:
        """
        执行函数并自动重试
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            RetryResult 包含结果和重试信息
        """
        start_time = time.time()
        attempts: List[RetryAttempt] = []
        
        for attempt_num in range(self.config.max_retries + 1):
            self._stats["total_attempts"] += 1
            
            try:
                # 执行函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # 成功
                total_duration = time.time() - start_time
                
                if attempt_num > 0:
                    self._stats["successful_retries"] += 1
                
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    total_duration=total_duration
                )
                
            except Exception as e:
                error_type = self.classify_error(e)
                
                # 检查是否可重试
                if not self.is_retryable(e):
                    # 不可重试，立即失败
                    return RetryResult(
                        success=False,
                        final_exception=e,
                        attempts=attempts,
                        total_duration=time.time() - start_time
                    )
                
                # 记录尝试
                attempt = RetryAttempt(
                    attempt_number=attempt_num + 1,
                    exception=e,
                    delay=0.0,
                    error_type=error_type
                )
                attempts.append(attempt)
                
                # 检查是否还有重试次数
                if attempt_num >= self.config.max_retries:
                    self._stats["failed_permanently"] += 1
                    
                    # 调用耗尽回调
                    if self.config.on_exhausted:
                        self.config.on_exhausted(attempt_num + 1, e)
                    
                    return RetryResult(
                        success=False,
                        final_exception=e,
                        attempts=attempts,
                        total_duration=time.time() - start_time
                    )
                
                # 计算延迟
                delay = self.calculate_delay(attempt_num)
                attempt.delay = delay
                self._stats["total_wait_time"] += delay
                
                # 调用重试回调
                if self.config.on_retry:
                    self.config.on_retry(attempt_num + 1, e, delay)
                
                self._logger.warning(
                    f"Retry {attempt_num + 1}/{self.config.max_retries} "
                    f"after {delay:.2f}s due to {error_type.name}: {e}"
                )
                
                # 等待
                await asyncio.sleep(delay)
        
        # 不应该到达这里
        return RetryResult(
            success=False,
            attempts=attempts,
            total_duration=time.time() - start_time
        )
    
    def with_retry(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        装饰器：为函数添加重试能力
        
        Example:
            >>> @retry_handler.with_retry
            >>> async def api_call():
            ...     return await fetch_data()
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await self.execute(func, *args, **kwargs)
            if result.success:
                return result.result
            else:
                raise result.final_exception or Exception("Retry exhausted")
        
        return wrapper
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "config": {
                "max_retries": self.config.max_retries,
                "base_delay": self.config.base_delay,
                "max_delay": self.config.max_delay
            }
        }
    
    def reset_stats(self) -> None:
        """重置统计"""
        self._stats = {
            "total_attempts": 0,
            "successful_retries": 0,
            "failed_permanently": 0,
            "total_wait_time": 0.0
        }


class ProviderFallback:
    """
    Provider 回退管理器
    
    当主 provider 失败时自动切换到备用
    """
    
    def __init__(self):
        self._providers: List[Dict[str, Any]] = []
        self._current_index = 0
    
    def add_provider(
        self,
        name: str,
        factory: Callable[..., T],
        priority: int = 0
    ) -> None:
        """
        添加 provider
        
        Args:
            name: provider 名称
            factory: 创建 provider 实例的工厂函数
            priority: 优先级（数字越小优先级越高）
        """
        self._providers.append({
            "name": name,
            "factory": factory,
            "priority": priority,
            "failure_count": 0,
            "last_failure": None
        })
        # 按优先级排序
        self._providers.sort(key=lambda p: p["priority"])
    
    async def execute(self, operation: Callable[[T], Any]) -> Any:
        """
        执行操作，自动处理 provider 回退
        
        Args:
            operation: 操作函数，接收 provider 实例
        
        Returns:
            操作结果
        
        Raises:
            Exception: 所有 provider 都失败
        """
        errors = []
        
        for provider_info in self._providers:
            try:
                # 创建 provider 实例
                if asyncio.iscoroutinefunction(provider_info["factory"]):
                    provider = await provider_info["factory"]()
                else:
                    provider = provider_info["factory"]()
                
                # 执行操作
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(provider)
                else:
                    result = operation(provider)
                
                return result
                
            except Exception as e:
                provider_info["failure_count"] += 1
                provider_info["last_failure"] = time.time()
                errors.append((provider_info["name"], e))
                continue
        
        # 所有 provider 都失败
        error_msg = "; ".join([f"{name}: {e}" for name, e in errors])
        raise Exception(f"All providers failed: {error_msg}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "providers": [
                {
                    "name": p["name"],
                    "priority": p["priority"],
                    "failure_count": p["failure_count"],
                    "last_failure": p["last_failure"]
                }
                for p in self._providers
            ]
        }


# 便捷函数
def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs
):
    """
    便捷装饰器：为函数添加重试能力
    
    Example:
        >>> @with_retry(max_retries=5)
        >>> async def api_call():
        ...     return await fetch_data()
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        **kwargs
    )
    handler = RetryHandler(config)
    return handler.with_retry
