"""
Async Job Manager - 异步任务管理器

基于 GSD-2 的 AsyncJobManager 设计，提供：
1. 后台任务管理
2. 任务取消支持
3. TTL 自动清理
4. 任务状态跟踪
5. 并发控制

使用场景:
- 管理长时间运行的工具执行
- 后台数据处理
- 异步文件操作

使用示例:
    >>> from async_job_manager import AsyncJobManager, JobConfig
    >>> 
    >>> manager = AsyncJobManager(max_concurrent=5)
    >>> 
    >>> # 提交任务
    >>> job_id = await manager.submit(long_running_task, arg1, arg2)
    >>> 
    >>> # 检查状态
    >>> status = manager.get_status(job_id)
    >>> 
    >>> # 等待完成
    >>> result = await manager.wait_for(job_id)
    >>> 
    >>> # 取消任务
    >>> await manager.cancel(job_id)
"""
import asyncio
import uuid
import time
from typing import (
    Dict, Any, Optional, Callable, Union, 
    List, Set, TypeVar, Coroutine
)
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from concurrent.futures import CancelledError


T = TypeVar('T')


class JobStatus(Enum):
    """任务状态"""
    PENDING = "pending"       # 等待中
    RUNNING = "running"       # 运行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消
    TIMEOUT = "timeout"       # 超时


@dataclass
class JobConfig:
    """任务配置"""
    ttl_seconds: float = 3600.0      # 任务存活时间
    timeout_seconds: Optional[float] = None  # 执行超时
    max_retries: int = 0             # 最大重试次数
    priority: int = 0                # 优先级（数字越小优先级越高）
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobResult:
    """任务结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    retry_count: int = 0


@dataclass
class JobInfo:
    """任务信息"""
    job_id: str
    status: JobStatus
    config: JobConfig
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[JobResult] = None
    progress: float = 0.0            # 进度 0-100
    message: str = ""
    
    @property
    def duration_seconds(self) -> float:
        """获取持续时间"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return 0.0
    
    @property
    def is_active(self) -> bool:
        """是否活跃"""
        return self.status in [JobStatus.PENDING, JobStatus.RUNNING]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "progress": self.progress,
            "message": self.message,
            "result": {
                "success": self.result.success if self.result else None,
                "error": self.result.error if self.result else None
            } if self.result else None
        }


class AsyncJobManager:
    """
    异步任务管理器
    
    管理后台任务的提交、执行、取消和清理
    """
    
    def __init__(
        self,
        max_concurrent: int = 10,
        cleanup_interval: float = 60.0
    ):
        """
        初始化任务管理器
        
        Args:
            max_concurrent: 最大并发任务数
            cleanup_interval: 清理间隔（秒）
        """
        self.max_concurrent = max_concurrent
        self.cleanup_interval = cleanup_interval
        
        # 任务存储
        self._jobs: Dict[str, JobInfo] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        
        # 并发控制
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # 清理任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # 统计
        self._stats = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
            "timeout": 0
        }
    
    async def start(self) -> None:
        """启动管理器"""
        if not self._running:
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self) -> None:
        """停止管理器"""
        self._running = False
        
        # 取消清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except CancelledError:
                pass
        
        # 取消所有活跃任务
        await self.cancel_all()
    
    async def submit(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args,
        config: Optional[JobConfig] = None,
        **kwargs
    ) -> str:
        """
        提交异步任务
        
        Args:
            func: 异步函数
            *args: 位置参数
            config: 任务配置
            **kwargs: 关键字参数
        
        Returns:
            任务 ID
        """
        await self.start()
        
        job_id = str(uuid.uuid4())
        config = config or JobConfig()
        
        # 创建任务信息
        job_info = JobInfo(
            job_id=job_id,
            status=JobStatus.PENDING,
            config=config,
            created_at=datetime.now()
        )
        self._jobs[job_id] = job_info
        
        # 创建任务
        task = asyncio.create_task(
            self._execute_job(job_id, func, args, kwargs)
        )
        self._tasks[job_id] = task
        
        self._stats["submitted"] += 1
        
        return job_id
    
    async def _execute_job(
        self,
        job_id: str,
        func: Callable,
        args: tuple,
        kwargs: dict
    ) -> None:
        """执行任务"""
        job_info = self._jobs.get(job_id)
        if not job_info:
            return
        
        async with self._semaphore:
            job_info.status = JobStatus.RUNNING
            job_info.started_at = datetime.now()
            
            start_time = time.time()
            retry_count = 0
            
            try:
                # 设置超时
                timeout = job_info.config.timeout_seconds
                
                if timeout:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout
                    )
                else:
                    result = await func(*args, **kwargs)
                
                # 成功
                job_info.result = JobResult(
                    success=True,
                    data=result,
                    duration_seconds=time.time() - start_time,
                    retry_count=retry_count
                )
                job_info.status = JobStatus.COMPLETED
                self._stats["completed"] += 1
                
            except asyncio.TimeoutError:
                job_info.result = JobResult(
                    success=False,
                    error="Task timeout",
                    duration_seconds=time.time() - start_time
                )
                job_info.status = JobStatus.TIMEOUT
                self._stats["timeout"] += 1
                
            except CancelledError:
                job_info.result = JobResult(
                    success=False,
                    error="Task cancelled",
                    duration_seconds=time.time() - start_time
                )
                job_info.status = JobStatus.CANCELLED
                self._stats["cancelled"] += 1
                raise
                
            except Exception as e:
                job_info.result = JobResult(
                    success=False,
                    error=str(e),
                    duration_seconds=time.time() - start_time
                )
                job_info.status = JobStatus.FAILED
                self._stats["failed"] += 1
                
            finally:
                job_info.completed_at = datetime.now()
    
    def get_status(self, job_id: str) -> Optional[JobStatus]:
        """
        获取任务状态
        
        Args:
            job_id: 任务 ID
        
        Returns:
            任务状态或 None
        """
        job_info = self._jobs.get(job_id)
        return job_info.status if job_info else None
    
    def get_info(self, job_id: str) -> Optional[JobInfo]:
        """
        获取任务信息
        
        Args:
            job_id: 任务 ID
        
        Returns:
            任务信息或 None
        """
        return self._jobs.get(job_id)
    
    def get_result(self, job_id: str) -> Optional[JobResult]:
        """
        获取任务结果
        
        Args:
            job_id: 任务 ID
        
        Returns:
            任务结果或 None
        """
        job_info = self._jobs.get(job_id)
        return job_info.result if job_info else None
    
    async def wait_for(
        self,
        job_id: str,
        timeout: Optional[float] = None
    ) -> Optional[JobResult]:
        """
        等待任务完成
        
        Args:
            job_id: 任务 ID
            timeout: 等待超时
        
        Returns:
            任务结果或 None
        """
        task = self._tasks.get(job_id)
        if not task:
            return self.get_result(job_id)
        
        try:
            await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            pass
        
        return self.get_result(job_id)
    
    async def cancel(self, job_id: str) -> bool:
        """
        取消任务
        
        Args:
            job_id: 任务 ID
        
        Returns:
            是否成功取消
        """
        task = self._tasks.get(job_id)
        if not task:
            return False
        
        task.cancel()
        
        try:
            await task
        except CancelledError:
            pass
        
        return True
    
    async def cancel_all(self, status: Optional[JobStatus] = None) -> int:
        """
        取消所有任务
        
        Args:
            status: 只取消指定状态的任务，None 表示取消所有
        
        Returns:
            取消的任务数
        """
        cancelled = 0
        
        for job_id, job_info in list(self._jobs.items()):
            if status and job_info.status != status:
                continue
            
            if await self.cancel(job_id):
                cancelled += 1
        
        return cancelled
    
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 100
    ) -> List[JobInfo]:
        """
        列出任务
        
        Args:
            status: 过滤状态
            limit: 最大数量
        
        Returns:
            任务信息列表
        """
        jobs = list(self._jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        # 按创建时间排序（最新的在前）
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return jobs[:limit]
    
    def update_progress(self, job_id: str, progress: float, message: str = "") -> bool:
        """
        更新任务进度
        
        在任务函数内部调用
        
        Args:
            job_id: 任务 ID
            progress: 进度 0-100
            message: 进度消息
        
        Returns:
            是否成功更新
        """
        job_info = self._jobs.get(job_id)
        if not job_info:
            return False
        
        job_info.progress = max(0.0, min(100.0, progress))
        if message:
            job_info.message = message
        
        return True
    
    async def _cleanup_loop(self) -> None:
        """清理循环"""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                self._cleanup_expired()
            except CancelledError:
                break
            except Exception:
                pass
    
    def _cleanup_expired(self) -> int:
        """
        清理过期任务
        
        Returns:
            清理的任务数
        """
        now = datetime.now()
        expired = []
        
        for job_id, job_info in self._jobs.items():
            # 检查 TTL
            age = (now - job_info.created_at).total_seconds()
            if age > job_info.config.ttl_seconds:
                expired.append(job_id)
                continue
            
            # 检查已完成任务的任务对象
            if not job_info.is_active and job_id in self._tasks:
                task = self._tasks[job_id]
                if task.done():
                    expired.append(job_id)
        
        for job_id in expired:
            self._jobs.pop(job_id, None)
            self._tasks.pop(job_id, None)
        
        return len(expired)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息
        """
        active_count = sum(
            1 for j in self._jobs.values() if j.is_active
        )
        
        return {
            **self._stats,
            "active_jobs": active_count,
            "total_jobs": len(self._jobs),
            "max_concurrent": self.max_concurrent
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        asyncio.create_task(self.stop())


# 便捷函数
async def run_in_background(
    func: Callable[..., Coroutine[Any, Any, T]],
    *args,
    **kwargs
) -> str:
    """
    在后台运行函数
    
    Args:
        func: 异步函数
        *args: 位置参数
        **kwargs: 关键字参数
    
    Returns:
        任务 ID
    """
    manager = AsyncJobManager()
    return await manager.submit(func, *args, **kwargs)
