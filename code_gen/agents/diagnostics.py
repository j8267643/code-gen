"""
Diagnostics - 诊断系统

基于 GSD-2 的诊断设计，提供：
1. 系统健康检查
2. 性能指标收集
3. 问题诊断和报告
4. 资源使用监控
5. 诊断日志记录

使用示例:
    >>> from diagnostics import Diagnostics, DiagnosticLevel
    >>> 
    >>> diag = Diagnostics()
    >>> 
    >>> # 记录诊断信息
    >>> diag.info("agent", "Agent started successfully")
    >>> diag.warning("memory", "High memory usage detected", {"usage": "85%"})
    >>> diag.error("network", "Connection failed", {"error": "timeout"})
    >>> 
    >>> # 运行健康检查
    >>> health = await diag.run_health_check()
    >>> print(health.status)
    >>> 
    >>> # 生成诊断报告
    >>> report = diag.generate_report()
"""
import asyncio
import json
import platform
import sys
import time
import traceback
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
import psutil


class DiagnosticLevel(Enum):
    """诊断级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class DiagnosticEntry:
    """诊断条目"""
    timestamp: datetime
    level: DiagnosticLevel
    category: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    exception: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category,
            "message": self.message,
            "details": self.details,
            "source": self.source,
            "exception": self.exception
        }


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SystemHealth:
    """系统健康状态"""
    overall_status: HealthStatus
    checks: List[HealthCheckResult]
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def is_healthy(self) -> bool:
        """是否完全健康"""
        return self.overall_status == HealthStatus.HEALTHY
    
    @property
    def failed_checks(self) -> List[HealthCheckResult]:
        """失败的检查"""
        return [
            c for c in self.checks 
            if c.status in [HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN]
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "checks": [c.to_dict() for c in self.checks],
            "timestamp": self.timestamp.isoformat(),
            "is_healthy": self.is_healthy,
            "failed_count": len(self.failed_checks)
        }


@dataclass
class PerformanceMetrics:
    """性能指标"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_usage_percent: float
    open_files: int
    thread_count: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": round(self.cpu_percent, 2),
            "memory_percent": round(self.memory_percent, 2),
            "memory_used_mb": round(self.memory_used_mb, 2),
            "memory_total_mb": round(self.memory_total_mb, 2),
            "disk_usage_percent": round(self.disk_usage_percent, 2),
            "open_files": self.open_files,
            "thread_count": self.thread_count,
            "timestamp": self.timestamp.isoformat()
        }


class Diagnostics:
    """
    诊断系统
    
    收集系统健康信息、性能指标和诊断日志
    """
    
    def __init__(
        self,
        max_entries: int = 1000,
        enable_system_metrics: bool = True
    ):
        self.max_entries = max_entries
        self.enable_system_metrics = enable_system_metrics
        
        # 诊断条目
        self._entries: List[DiagnosticEntry] = []
        
        # 健康检查器
        self._health_checkers: Dict[str, Callable[[], HealthCheckResult]] = {}
        
        # 性能指标历史
        self._metrics_history: List[PerformanceMetrics] = []
        self._max_metrics_history = 100
        
        # 统计
        self._stats = {
            "entries_by_level": {level.value: 0 for level in DiagnosticLevel},
            "entries_by_category": {},
            "total_entries": 0
        }
    
    def log(
        self,
        level: DiagnosticLevel,
        category: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        source: str = "",
        exception: Optional[Exception] = None
    ) -> None:
        """
        记录诊断条目
        
        Args:
            level: 诊断级别
            category: 类别（如 'agent', 'network', 'memory'）
            message: 消息
            details: 详细信息
            source: 来源
            exception: 异常对象
        """
        entry = DiagnosticEntry(
            timestamp=datetime.now(),
            level=level,
            category=category,
            message=message,
            details=details or {},
            source=source,
            exception=traceback.format_exc() if exception else None
        )
        
        self._entries.append(entry)
        
        # 限制条目数量
        if len(self._entries) > self.max_entries:
            self._entries.pop(0)
        
        # 更新统计
        self._stats["total_entries"] += 1
        self._stats["entries_by_level"][level.value] += 1
        self._stats["entries_by_category"][category] = \
            self._stats["entries_by_category"].get(category, 0) + 1
    
    def debug(
        self,
        category: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        source: str = ""
    ) -> None:
        """记录调试信息"""
        self.log(DiagnosticLevel.DEBUG, category, message, details, source)
    
    def info(
        self,
        category: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        source: str = ""
    ) -> None:
        """记录信息"""
        self.log(DiagnosticLevel.INFO, category, message, details, source)
    
    def warning(
        self,
        category: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        source: str = ""
    ) -> None:
        """记录警告"""
        self.log(DiagnosticLevel.WARNING, category, message, details, source)
    
    def error(
        self,
        category: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        source: str = "",
        exception: Optional[Exception] = None
    ) -> None:
        """记录错误"""
        self.log(DiagnosticLevel.ERROR, category, message, details, source, exception)
    
    def critical(
        self,
        category: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        source: str = "",
        exception: Optional[Exception] = None
    ) -> None:
        """记录严重错误"""
        self.log(DiagnosticLevel.CRITICAL, category, message, details, source, exception)
    
    def register_health_checker(
        self,
        name: str,
        checker: Callable[[], HealthCheckResult]
    ) -> None:
        """
        注册健康检查器
        
        Args:
            name: 检查器名称
            checker: 检查函数
        """
        self._health_checkers[name] = checker
    
    async def run_health_check(self) -> SystemHealth:
        """
        运行所有健康检查
        
        Returns:
            系统健康状态
        """
        checks: List[HealthCheckResult] = []
        
        # 运行注册的检查器
        for name, checker in self._health_checkers.items():
            try:
                start = time.time()
                if asyncio.iscoroutinefunction(checker):
                    result = await checker()
                else:
                    result = checker()
                result.duration_ms = (time.time() - start) * 1000
                checks.append(result)
            except Exception as e:
                checks.append(HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check failed: {e}",
                    details={"error": str(e)}
                ))
        
        # 确定整体状态
        if any(c.status == HealthStatus.UNHEALTHY for c in checks):
            overall = HealthStatus.UNHEALTHY
        elif any(c.status == HealthStatus.DEGRADED for c in checks):
            overall = HealthStatus.DEGRADED
        elif all(c.status == HealthStatus.HEALTHY for c in checks):
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN
        
        return SystemHealth(
            overall_status=overall,
            checks=checks
        )
    
    def collect_metrics(self) -> PerformanceMetrics:
        """
        收集系统性能指标
        
        Returns:
            性能指标
        """
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 内存使用
            memory = psutil.virtual_memory()
            
            # 磁盘使用
            disk = psutil.disk_usage('/')
            
            # 进程信息
            process = psutil.Process()
            open_files = len(process.open_files())
            thread_count = process.num_threads()
            
            metrics = PerformanceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_total_mb=memory.total / (1024 * 1024),
                disk_usage_percent=(disk.used / disk.total) * 100,
                open_files=open_files,
                thread_count=thread_count
            )
            
            # 保存历史
            self._metrics_history.append(metrics)
            if len(self._metrics_history) > self._max_metrics_history:
                self._metrics_history.pop(0)
            
            return metrics
            
        except Exception as e:
            self.error("diagnostics", "Failed to collect metrics", {"error": str(e)})
            return PerformanceMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_total_mb=0.0,
                disk_usage_percent=0.0,
                open_files=0,
                thread_count=0
            )
    
    def get_entries(
        self,
        level: Optional[DiagnosticLevel] = None,
        category: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[DiagnosticEntry]:
        """
        获取诊断条目
        
        Args:
            level: 过滤级别
            category: 过滤类别
            since: 从此时间之后
            limit: 最大数量
        
        Returns:
            诊断条目列表
        """
        result = self._entries
        
        if level:
            result = [e for e in result if e.level == level]
        
        if category:
            result = [e for e in result if e.category == category]
        
        if since:
            result = [e for e in result if e.timestamp >= since]
        
        return result[-limit:]
    
    def generate_report(self) -> Dict[str, Any]:
        """
        生成诊断报告
        
        Returns:
            报告字典
        """
        # 收集当前指标
        metrics = self.collect_metrics()
        
        # 获取最近的条目
        recent_entries = self.get_entries(limit=50)
        
        # 系统信息
        system_info = {
            "platform": platform.platform(),
            "python_version": sys.version,
            "processor": platform.processor(),
            "hostname": platform.node()
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system_info": system_info,
            "metrics": metrics.to_dict(),
            "stats": self._stats,
            "recent_entries": [e.to_dict() for e in recent_entries],
            "entry_summary": {
                level.value: len([e for e in self._entries if e.level == level])
                for level in DiagnosticLevel
            }
        }
    
    def save_report(self, path: Union[str, Path]) -> None:
        """
        保存诊断报告到文件
        
        Args:
            path: 文件路径
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        report = self.generate_report()
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "entries_count": len(self._entries),
            "metrics_history_count": len(self._metrics_history),
            "health_checkers_count": len(self._health_checkers)
        }
    
    def clear(self) -> None:
        """清除所有数据"""
        self._entries.clear()
        self._metrics_history.clear()
        self._stats = {
            "entries_by_level": {level.value: 0 for level in DiagnosticLevel},
            "entries_by_category": {},
            "total_entries": 0
        }


# 全局诊断实例
_global_diagnostics: Optional[Diagnostics] = None


def get_diagnostics() -> Diagnostics:
    """获取全局诊断实例"""
    global _global_diagnostics
    if _global_diagnostics is None:
        _global_diagnostics = Diagnostics()
    return _global_diagnostics


# 便捷函数
def log_diagnostic(
    level: DiagnosticLevel,
    category: str,
    message: str,
    **kwargs
) -> None:
    """记录诊断信息"""
    get_diagnostics().log(level, category, message, **kwargs)
