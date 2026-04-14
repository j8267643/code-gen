"""
Utilities - 工具函数和性能优化

提供通用的工具函数、性能监控、缓存、重试机制等
"""
from typing import Dict, Any, List, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
import asyncio
import time
import hashlib
import json
from contextlib import contextmanager


T = TypeVar('T')


@dataclass
class PerformanceMetrics:
    """性能指标"""
    operation: str
    start_time: float
    end_time: float = 0
    success: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """执行时长"""
        return self.end_time - self.start_time


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self._active_operations: Dict[str, PerformanceMetrics] = {}
    
    @contextmanager
    def track(self, operation: str, **metadata):
        """跟踪操作性能"""
        metric = PerformanceMetrics(
            operation=operation,
            start_time=time.time(),
            metadata=metadata
        )
        self._active_operations[operation] = metric
        
        try:
            yield metric
            metric.success = True
        except Exception as e:
            metric.success = False
            metric.error = str(e)
            raise
        finally:
            metric.end_time = time.time()
            self.metrics.append(metric)
            del self._active_operations[operation]
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.metrics:
            return {"message": "暂无性能数据"}
        
        total_ops = len(self.metrics)
        successful = sum(1 for m in self.metrics if m.success)
        total_duration = sum(m.duration for m in self.metrics)
        
        # 按操作分组统计
        by_operation: Dict[str, List[PerformanceMetrics]] = {}
        for m in self.metrics:
            by_operation.setdefault(m.operation, []).append(m)
        
        operation_stats = {}
        for op, metrics in by_operation.items():
            durations = [m.duration for m in metrics]
            operation_stats[op] = {
                "count": len(metrics),
                "success_rate": sum(1 for m in metrics if m.success) / len(metrics),
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations)
            }
        
        return {
            "total_operations": total_ops,
            "successful": successful,
            "failed": total_ops - successful,
            "success_rate": successful / total_ops,
            "total_duration": total_duration,
            "avg_duration": total_duration / total_ops,
            "by_operation": operation_stats
        }
    
    def reset(self):
        """重置监控数据"""
        self.metrics.clear()
        self._active_operations.clear()


class SimpleCache(Generic[T]):
    """简单缓存"""
    
    def __init__(self, ttl: int = 3600, max_size: int = 1000):
        """
        Args:
            ttl: 缓存过期时间（秒）
            max_size: 最大缓存条目数
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def _make_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[T]:
        """获取缓存"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if time.time() > entry["expires"]:
            del self._cache[key]
            return None
        
        return entry["value"]
    
    def set(self, key: str, value: T, ttl: Optional[int] = None):
        """设置缓存"""
        # 清理过期条目
        self._cleanup()
        
        # 限制大小
        if len(self._cache) >= self.max_size:
            # 删除最旧的条目
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k]["created"])
            del self._cache[oldest_key]
        
        self._cache[key] = {
            "value": value,
            "created": time.time(),
            "expires": time.time() + (ttl or self.ttl)
        }
    
    def _cleanup(self):
        """清理过期条目"""
        now = time.time()
        expired = [k for k, v in self._cache.items() if now > v["expires"]]
        for k in expired:
            del self._cache[k]
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
    
    def cached(self, func: Callable) -> Callable:
        """缓存装饰器"""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            key = self._make_key(func.__name__, *args, **kwargs)
            cached_value = self.get(key)
            if cached_value is not None:
                return cached_value
            
            result = await func(*args, **kwargs)
            self.set(key, result)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = self._make_key(func.__name__, *args, **kwargs)
            cached_value = self.get(key)
            if cached_value is not None:
                return cached_value
            
            result = func(*args, **kwargs)
            self.set(key, result)
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


class RetryManager:
    """重试管理器"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retryable_exceptions: tuple = (Exception,)
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions
    
    def calculate_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
    
    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """执行带重试的函数"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except self.retryable_exceptions as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    await asyncio.sleep(delay)
                else:
                    break
        
        raise last_exception
    
    def retry(self, func: Callable) -> Callable:
        """重试装饰器"""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self.execute(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self.execute(func, *args, **kwargs))
            finally:
                loop.close()
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_calls: int, period: float):
        """
        Args:
            max_calls: 周期内最大调用次数
            period: 周期（秒）
        """
        self.max_calls = max_calls
        self.period = period
        self.calls: List[float] = []
    
    async def acquire(self):
        """获取执行许可"""
        now = time.time()
        
        # 清理过期的调用记录
        self.calls = [c for c in self.calls if now - c < self.period]
        
        # 检查是否超过限制
        if len(self.calls) >= self.max_calls:
            # 等待直到可以执行
            sleep_time = self.calls[0] + self.period - now
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            return await self.acquire()
        
        self.calls.append(now)
    
    def __call__(self, func: Callable) -> Callable:
        """装饰器"""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            await self.acquire()
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self.acquire())
                return func(*args, **kwargs)
            finally:
                loop.close()
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


# ========== 便捷函数 ==========

def timing_decorator(func_name: Optional[str] = None):
    """计时装饰器"""
    def decorator(func: Callable) -> Callable:
        name = func_name or func.__name__
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                print(f"⏱️ {name} 耗时: {time.time() - start:.2f}s")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                print(f"⏱️ {name} 耗时: {time.time() - start:.2f}s")
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def async_batch_process(
    items: List[T],
    process_func: Callable[[T], Any],
    batch_size: int = 10,
    max_concurrency: int = 5
) -> List[Any]:
    """异步批处理"""
    async def process_batch(batch: List[T]) -> List[Any]:
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def process_with_limit(item: T) -> Any:
            async with semaphore:
                if asyncio.iscoroutinefunction(process_func):
                    return await process_func(item)
                else:
                    return process_func(item)
        
        tasks = [process_with_limit(item) for item in batch]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def run_all():
        results = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await process_batch(batch)
            results.extend(batch_results)
        return results
    
    return asyncio.run(run_all())


def safe_json_loads(text: str, default: Any = None) -> Any:
    """安全的 JSON 解析"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断字符串"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
    return f"{prefix}{timestamp}_{random_suffix}"


# 全局实例
performance_monitor = PerformanceMonitor()
cache = SimpleCache()
retry_manager = RetryManager()
