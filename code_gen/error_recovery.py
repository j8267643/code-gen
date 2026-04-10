"""
错误恢复机制模块
提供自动重试、降级策略和错误分类功能
"""
import asyncio
import functools
import logging
from typing import TypeVar, Callable, Any, Optional, List, Dict, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import random
import traceback


T = TypeVar('T')


class ErrorCategory(Enum):
    """错误分类"""
    NETWORK = "network"          # 网络错误（可重试）
    TIMEOUT = "timeout"          # 超时错误（可重试）
    RATE_LIMIT = "rate_limit"    # 限流错误（可重试，需等待）
    AUTH = "auth"                # 认证错误（不可重试）
    VALIDATION = "validation"    # 验证错误（不可重试）
    RESOURCE = "resource"        # 资源错误（可能可重试）
    UNKNOWN = "unknown"          # 未知错误


class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"              # 重试
    FALLBACK = "fallback"        # 降级
    CIRCUIT_BREAK = "circuit_break"  # 熔断
    FAIL = "fail"                # 失败


@dataclass
class ErrorContext:
    """错误上下文"""
    error: Exception
    category: ErrorCategory
    attempt: int
    max_attempts: int
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def should_retry(self) -> bool:
        """是否应该重试"""
        if self.attempt >= self.max_attempts:
            return False
        return self.category in [
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.RESOURCE
        ]
    
    def get_retry_delay(self) -> float:
        """获取重试延迟（指数退避 + 抖动）"""
        base_delay = min(2 ** self.attempt, 60)  # 最大60秒
        jitter = random.uniform(0, 1)  # 0-1秒随机抖动
        
        if self.category == ErrorCategory.RATE_LIMIT:
            # 限流错误等待更久
            return base_delay * 2 + jitter
        
        return base_delay + jitter


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    strategy_used: RecoveryStrategy = RecoveryStrategy.FAIL
    attempts: int = 0
    total_time: float = 0.0
    fallback_used: bool = False


class ErrorClassifier:
    """错误分类器"""
    
    # 错误关键词映射
    ERROR_PATTERNS = {
        ErrorCategory.NETWORK: [
            "connection", "network", "unreachable", "refused", "reset",
            "连接", "网络", "无法访问"
        ],
        ErrorCategory.TIMEOUT: [
            "timeout", "timed out", "deadline exceeded",
            "超时", "时间"
        ],
        ErrorCategory.RATE_LIMIT: [
            "rate limit", "too many requests", "429", "throttled",
            "限流", "请求过多"
        ],
        ErrorCategory.AUTH: [
            "unauthorized", "forbidden", "authentication", "401", "403",
            "未授权", "认证", "禁止"
        ],
        ErrorCategory.VALIDATION: [
            "validation", "invalid", "bad request", "400",
            "验证", "无效"
        ],
        ErrorCategory.RESOURCE: [
            "not found", "404", "resource", "memory", "disk", "quota",
            "未找到", "资源", "内存", "磁盘"
        ]
    }
    
    @classmethod
    def classify(cls, error: Exception) -> ErrorCategory:
        """分类错误"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        for category, patterns in cls.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern in error_str or pattern in error_type:
                    return category
        
        return ErrorCategory.UNKNOWN


class RetryPolicy:
    """重试策略"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        retryable_categories: Optional[List[ErrorCategory]] = None,
        on_retry: Optional[Callable[[ErrorContext], None]] = None
    ):
        self.max_attempts = max_attempts
        self.retryable_categories = retryable_categories or [
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.RATE_LIMIT
        ]
        self.on_retry = on_retry
    
    async def execute(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> RecoveryResult:
        """执行带重试的函数"""
        start_time = datetime.now()
        last_error = None
        
        for attempt in range(1, self.max_attempts + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                total_time = (datetime.now() - start_time).total_seconds()
                return RecoveryResult(
                    success=True,
                    result=result,
                    strategy_used=RecoveryStrategy.RETRY if attempt > 1 else RecoveryStrategy.FAIL,
                    attempts=attempt,
                    total_time=total_time
                )
                
            except Exception as e:
                last_error = e
                category = ErrorClassifier.classify(e)
                
                context = ErrorContext(
                    error=e,
                    category=category,
                    attempt=attempt,
                    max_attempts=self.max_attempts
                )
                
                # 检查是否应该重试
                if not context.should_retry():
                    break
                
                # 回调通知
                if self.on_retry:
                    self.on_retry(context)
                
                # 等待后重试
                if attempt < self.max_attempts:
                    delay = context.get_retry_delay()
                    await asyncio.sleep(delay)
        
        total_time = (datetime.now() - start_time).total_seconds()
        return RecoveryResult(
            success=False,
            error=last_error,
            strategy_used=RecoveryStrategy.FAIL,
            attempts=self.max_attempts,
            total_time=total_time
        )


class FallbackStrategy:
    """降级策略"""
    
    def __init__(
        self,
        primary_func: Callable,
        fallback_funcs: List[Callable],
        retry_policy: Optional[RetryPolicy] = None
    ):
        self.primary_func = primary_func
        self.fallback_funcs = fallback_funcs
        self.retry_policy = retry_policy or RetryPolicy()
    
    async def execute(self, *args, **kwargs) -> RecoveryResult:
        """执行带降级的函数"""
        start_time = datetime.now()
        
        # 首先尝试主函数
        result = await self.retry_policy.execute(self.primary_func, *args, **kwargs)
        if result.success:
            return result
        
        # 依次尝试降级函数
        for fallback_func in self.fallback_funcs:
            try:
                if asyncio.iscoroutinefunction(fallback_func):
                    fallback_result = await fallback_func(*args, **kwargs)
                else:
                    fallback_result = fallback_func(*args, **kwargs)
                
                total_time = (datetime.now() - start_time).total_seconds()
                return RecoveryResult(
                    success=True,
                    result=fallback_result,
                    strategy_used=RecoveryStrategy.FALLBACK,
                    attempts=result.attempts + 1,
                    total_time=total_time,
                    fallback_used=True
                )
            except Exception:
                continue
        
        # 所有降级都失败
        total_time = (datetime.now() - start_time).total_seconds()
        return RecoveryResult(
            success=False,
            error=result.error,
            strategy_used=RecoveryStrategy.FAIL,
            attempts=result.attempts + len(self.fallback_funcs),
            total_time=total_time
        )


class CircuitBreaker:
    """熔断器 - 防止级联故障"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """检查是否可以执行"""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # 检查是否过了恢复时间
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.state = "half-open"
                    self.half_open_calls = 0
                    return True
            return False
        
        if self.state == "half-open":
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
        
        return True
    
    def record_success(self):
        """记录成功"""
        if self.state == "half-open":
            self.half_open_calls -= 1
            if self.half_open_calls <= 0:
                self.state = "closed"
                self.failures = 0
        else:
            self.failures = max(0, self.failures - 1)
    
    def record_failure(self):
        """记录失败"""
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if self.state == "half-open":
            self.state = "open"
        elif self.failures >= self.failure_threshold:
            self.state = "open"
    
    async def execute(self, func: Callable[..., T], *args, **kwargs) -> RecoveryResult:
        """执行带熔断保护的函数"""
        if not self.can_execute():
            return RecoveryResult(
                success=False,
                error=Exception("Circuit breaker is open"),
                strategy_used=RecoveryStrategy.CIRCUIT_BREAK
            )
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            self.record_success()
            return RecoveryResult(
                success=True,
                result=result,
                strategy_used=RecoveryStrategy.FAIL
            )
            
        except Exception as e:
            self.record_failure()
            return RecoveryResult(
                success=False,
                error=e,
                strategy_used=RecoveryStrategy.CIRCUIT_BREAK
            )


class ResilientClient:
    """弹性客户端 - 整合所有恢复策略"""
    
    def __init__(
        self,
        retry_policy: Optional[RetryPolicy] = None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        self.retry_policy = retry_policy or RetryPolicy()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.error_history: List[ErrorContext] = []
    
    async def execute(
        self,
        func: Callable[..., T],
        fallback_funcs: Optional[List[Callable]] = None,
        *args,
        **kwargs
    ) -> RecoveryResult:
        """
        执行带完整恢复策略的函数
        
        执行顺序：
        1. 检查熔断器
        2. 尝试主函数（带重试）
        3. 尝试降级函数
        """
        # 1. 检查熔断器
        if not self.circuit_breaker.can_execute():
            # 熔断器打开，直接尝试降级
            if fallback_funcs:
                for fallback in fallback_funcs:
                    try:
                        if asyncio.iscoroutinefunction(fallback):
                            result = await fallback(*args, **kwargs)
                        else:
                            result = fallback(*args, **kwargs)
                        return RecoveryResult(
                            success=True,
                            result=result,
                            strategy_used=RecoveryStrategy.FALLBACK,
                            fallback_used=True
                        )
                    except:
                        continue
            
            return RecoveryResult(
                success=False,
                error=Exception("Circuit breaker is open and no fallback succeeded"),
                strategy_used=RecoveryStrategy.CIRCUIT_BREAK
            )
        
        # 2. 尝试主函数
        result = await self.retry_policy.execute(func, *args, **kwargs)
        
        if result.success:
            self.circuit_breaker.record_success()
            return result
        
        # 记录错误
        if result.error:
            self.error_history.append(ErrorContext(
                error=result.error,
                category=ErrorClassifier.classify(result.error),
                attempt=result.attempts,
                max_attempts=self.retry_policy.max_attempts
            ))
        
        self.circuit_breaker.record_failure()
        
        # 3. 尝试降级
        if fallback_funcs:
            fallback_strategy = FallbackStrategy(func, fallback_funcs, self.retry_policy)
            fallback_result = await fallback_strategy.execute(*args, **kwargs)
            
            if fallback_result.success:
                return fallback_result
        
        return result
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        if not self.error_history:
            return {"total_errors": 0}
        
        categories = {}
        for ctx in self.error_history:
            cat = ctx.category.value
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "categories": categories,
            "circuit_breaker_state": self.circuit_breaker.state,
            "recent_errors": [
                {
                    "category": ctx.category.value,
                    "attempt": ctx.attempt,
                    "time": ctx.timestamp.isoformat()
                }
                for ctx in self.error_history[-5:]
            ]
        }


# 装饰器版本
def with_retry(
    max_attempts: int = 3,
    retryable_exceptions: Optional[List[type]] = None
):
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        retry_policy = RetryPolicy(max_attempts=max_attempts)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_policy.execute(func, *args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(retry_policy.execute(func, *args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def with_fallback(*fallback_funcs: Callable):
    """降级装饰器"""
    def decorator(primary_func: Callable) -> Callable:
        strategy = FallbackStrategy(primary_func, list(fallback_funcs))
        
        @functools.wraps(primary_func)
        async def async_wrapper(*args, **kwargs):
            return await strategy.execute(*args, **kwargs)
        
        @functools.wraps(primary_func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(strategy.execute(*args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(primary_func) else sync_wrapper
    return decorator
