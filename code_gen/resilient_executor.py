"""
弹性执行器 - 自动重试、策略切换、持续探索直到成功
基于 error_recovery 模块构建
"""
import asyncio
import time
import traceback
from typing import Callable, Any, List, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ExecutionStrategy(Enum):
    """执行策略"""
    DIRECT = "direct"           # 直接执行
    RETRY = "retry"             # 重试
    FALLBACK = "fallback"       # 降级
    ALTERNATIVE = "alternative" # 替代方案
    HYBRID = "hybrid"           # 混合策略


@dataclass
class ExecutionAttempt:
    """执行尝试记录"""
    attempt_number: int
    strategy: ExecutionStrategy
    timestamp: datetime
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    result: Any = None
    attempts: List[ExecutionAttempt] = field(default_factory=list)
    total_duration_ms: float = 0.0
    final_strategy: ExecutionStrategy = ExecutionStrategy.DIRECT
    error_message: Optional[str] = None


class ResilientExecutor:
    """
    弹性执行器 - 持续探索直到成功

    特性：
    1. 自动重试 - 失败时自动重试，指数退避
    2. 策略切换 - 一种方法失败时自动切换备用方案
    3. 智能降级 - 高级功能失败时使用基础功能
    4. 错误学习 - 记录失败模式，避免重复犯错
    5. 超时控制 - 防止无限尝试
    """

    def __init__(
        self,
        max_attempts: int = 10,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        timeout_seconds: float = 300.0,
        verbose: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout_seconds = timeout_seconds
        self.verbose = verbose
        self.attempt_history: List[ExecutionAttempt] = []
        self.error_patterns: Dict[str, int] = {}  # 错误模式计数

    def _log(self, message: str, level: str = "INFO"):
        """输出日志"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")

    def _calculate_delay(self, attempt: int) -> float:
        """计算指数退避延迟"""
        delay = self.base_delay * (2 ** (attempt - 1))
        return min(delay, self.max_delay)

    def _analyze_error(self, error: Exception) -> str:
        """分析错误类型"""
        error_str = str(error).lower()

        if "no such file" in error_str or "not found" in error_str:
            return "file_not_found"
        elif "permission" in error_str or "access" in error_str:
            return "permission_denied"
        elif "connection" in error_str or "network" in error_str:
            return "network_error"
        elif "timeout" in error_str:
            return "timeout"
        elif "module" in error_str and "not found" in error_str:
            return "missing_module"
        elif "argument" in error_str:
            return "invalid_argument"
        else:
            return "unknown"

    def _get_fallback_strategies(
        self,
        primary_func: Callable,
        error_type: str,
        attempt_number: int
    ) -> List[tuple]:
        """
        获取降级策略列表

        根据错误类型和尝试次数，返回备用的执行策略
        """
        strategies = []

        if error_type == "file_not_found":
            # 文件不存在，尝试创建或查找替代路径
            strategies = [
                ("创建目录", lambda: self._ensure_directory(primary_func)),
                ("查找替代路径", lambda: self._find_alternative_path(primary_func)),
            ]
        elif error_type == "missing_module":
            # 缺少模块，尝试安装或使用替代工具
            strategies = [
                ("安装依赖", lambda: self._install_dependency(primary_func)),
                ("使用替代工具", lambda: self._use_alternative_tool(primary_func)),
            ]
        elif error_type == "invalid_argument":
            # 参数错误，尝试修正参数
            strategies = [
                ("修正参数", lambda: self._fix_arguments(primary_func)),
                ("简化调用", lambda: self._simplify_call(primary_func)),
            ]
        elif error_type == "network_error":
            # 网络错误，尝试离线方案或缓存
            strategies = [
                ("使用缓存", lambda: self._use_cache(primary_func)),
                ("离线模式", lambda: self._offline_mode(primary_func)),
            ]

        # 通用降级策略
        strategies.extend([
            ("简化执行", lambda: self._simplified_execution(primary_func)),
            ("基础功能", lambda: self._basic_functionality(primary_func)),
        ])

        return strategies

    # ===== 降级策略实现 =====

    def _ensure_directory(self, func: Callable):
        """确保目录存在"""
        import os
        from pathlib import Path

        # 尝试从函数中提取路径
        try:
            # 常见路径参数名
            path_params = ['path', 'dir', 'directory', 'work_dir', 'base_path']
            for param in path_params:
                if hasattr(func, param):
                    path = getattr(func, param)
                    Path(path).mkdir(parents=True, exist_ok=True)
                    self._log(f"创建目录: {path}")
                    return True
        except:
            pass
        return False

    def _find_alternative_path(self, func: Callable):
        """查找替代路径"""
        # 尝试当前目录、临时目录等
        alternatives = ['.', './temp', '/tmp', os.getcwd()]
        return alternatives[0] if alternatives else None

    def _install_dependency(self, func: Callable):
        """尝试安装缺失的依赖"""
        import subprocess
        import sys

        # 常见依赖映射
        module_mapping = {
            'pytest': 'pytest',
            'yaml': 'pyyaml',
            'requests': 'requests',
            'rich': 'rich',
        }

        for module, package in module_mapping.items():
            try:
                __import__(module)
            except ImportError:
                self._log(f"尝试安装依赖: {package}")
                try:
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                    self._log(f"成功安装: {package}")
                    return True
                except:
                    pass
        return False

    def _use_alternative_tool(self, func: Callable):
        """使用替代工具"""
        # 工具映射
        alternatives = {
            'pytest': 'python -m unittest',
            'bash': 'cmd' if os.name == 'nt' else 'sh',
            'npm': 'yarn' if shutil.which('yarn') else 'npm',
        }
        return alternatives

    def _fix_arguments(self, func: Callable):
        """修正参数"""
        # 常见参数修正
        fixes = {
            'cmd': 'command',
            'dir': 'directory',
            'path': 'file_path',
        }
        return fixes

    def _simplify_call(self, func: Callable):
        """简化调用"""
        return lambda *args, **kwargs: func()

    def _use_cache(self, func: Callable):
        """使用缓存"""
        return None

    def _offline_mode(self, func: Callable):
        """离线模式"""
        return None

    def _simplified_execution(self, func: Callable):
        """简化执行"""
        return lambda *args, **kwargs: None

    def _basic_functionality(self, func: Callable):
        """基础功能"""
        return lambda *args, **kwargs: True

    async def execute(
        self,
        func: Callable[..., Any],
        *args,
        fallback_funcs: Optional[List[Callable]] = None,
        context: Optional[Dict] = None,
        **kwargs
    ) -> ExecutionResult:
        """
        执行函数，持续尝试直到成功或达到最大尝试次数

        Args:
            func: 主执行函数
            *args: 位置参数
            fallback_funcs: 降级函数列表
            context: 执行上下文
            **kwargs: 关键字参数

        Returns:
            ExecutionResult: 执行结果
        """
        start_time = time.time()
        attempts = []
        fallback_funcs = fallback_funcs or []

        self._log(f"开始执行: {func.__name__ if hasattr(func, '__name__') else 'anonymous'}")
        self._log(f"最大尝试次数: {self.max_attempts}, 超时: {self.timeout_seconds}s")

        for attempt_num in range(1, self.max_attempts + 1):
            attempt_start = time.time()

            # 检查超时
            elapsed = time.time() - start_time
            if elapsed > self.timeout_seconds:
                self._log(f"执行超时 ({elapsed:.1f}s > {self.timeout_seconds}s)", "WARNING")
                return ExecutionResult(
                    success=False,
                    attempts=attempts,
                    total_duration_ms=elapsed * 1000,
                    error_message="Execution timeout"
                )

            # 选择策略
            if attempt_num == 1:
                strategy = ExecutionStrategy.DIRECT
                current_func = func
                current_args = args
                current_kwargs = kwargs
            elif attempt_num <= 3:
                # 重试阶段
                strategy = ExecutionStrategy.RETRY
                current_func = func
                current_args = args
                current_kwargs = kwargs

                # 指数退避
                delay = self._calculate_delay(attempt_num - 1)
                self._log(f"等待 {delay:.1f}s 后重试...")
                await asyncio.sleep(delay)
            elif fallback_funcs and attempt_num <= 3 + len(fallback_funcs):
                # 降级策略
                strategy = ExecutionStrategy.FALLBACK
                fallback_idx = attempt_num - 4
                current_func = fallback_funcs[fallback_idx]
                current_args = args
                current_kwargs = kwargs
                self._log(f"尝试降级方案 #{fallback_idx + 1}")
            else:
                # 替代方案
                strategy = ExecutionStrategy.ALTERNATIVE
                # 这里可以实现更复杂的替代逻辑
                self._log("尝试替代方案...")
                current_func = func
                current_args = args
                current_kwargs = {k: v for k, v in kwargs.items() if k not in ['depth', 'recursive']}

            try:
                # 执行
                self._log(f"尝试 #{attempt_num} [{strategy.value}]...")

                if asyncio.iscoroutinefunction(current_func):
                    result = await current_func(*current_args, **current_kwargs)
                else:
                    result = current_func(*current_args, **current_kwargs)

                # 成功
                duration = (time.time() - attempt_start) * 1000
                attempt = ExecutionAttempt(
                    attempt_number=attempt_num,
                    strategy=strategy,
                    timestamp=datetime.now(),
                    success=True,
                    result=result,
                    duration_ms=duration
                )
                attempts.append(attempt)

                total_duration = (time.time() - start_time) * 1000
                self._log(f"✅ 执行成功！尝试 {attempt_num} 次，耗时 {total_duration:.0f}ms", "SUCCESS")

                return ExecutionResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    total_duration_ms=total_duration,
                    final_strategy=strategy
                )

            except Exception as e:
                # 失败
                duration = (time.time() - attempt_start) * 1000
                error_type = self._analyze_error(e)
                error_msg = str(e)

                attempt = ExecutionAttempt(
                    attempt_number=attempt_num,
                    strategy=strategy,
                    timestamp=datetime.now(),
                    success=False,
                    error=f"[{error_type}] {error_msg}",
                    duration_ms=duration
                )
                attempts.append(attempt)

                self._log(f"❌ 尝试 #{attempt_num} 失败: [{error_type}] {error_msg}", "ERROR")

                # 记录错误模式
                self.error_patterns[error_type] = self.error_patterns.get(error_type, 0) + 1

                # 分析错误并提供建议
                if error_type == "invalid_argument":
                    self._log("💡 提示: 参数错误，尝试修正参数名...")
                    # 自动修正常见参数错误
                    if 'cmd' in kwargs and 'command' not in kwargs:
                        kwargs['command'] = kwargs.pop('cmd')
                        self._log("  已自动修正: cmd -> command")
                    if 'depth' in kwargs:
                        del kwargs['depth']
                        self._log("  已移除不支持的参数: depth")
                    if 'recursive' in kwargs:
                        del kwargs['recursive']
                        self._log("  已移除不支持的参数: recursive")

                elif error_type == "missing_module":
                    self._log("💡 提示: 缺少依赖，尝试安装...")
                    self._install_dependency(func)

                elif error_type == "file_not_found":
                    self._log("💡 提示: 文件不存在，尝试创建...")
                    self._ensure_directory(func)

        # 所有尝试都失败
        total_duration = (time.time() - start_time) * 1000
        self._log(f"所有 {self.max_attempts} 次尝试都失败", "ERROR")

        return ExecutionResult(
            success=False,
            attempts=attempts,
            total_duration_ms=total_duration,
            error_message=f"All {self.max_attempts} attempts failed"
        )

    def execute_sync(
        self,
        func: Callable[..., Any],
        *args,
        fallback_funcs: Optional[List[Callable]] = None,
        **kwargs
    ) -> ExecutionResult:
        """同步执行包装器"""
        return asyncio.run(self.execute(func, *args, fallback_funcs=fallback_funcs, **kwargs))


# ===== 便捷函数 =====

def execute_with_persistence(
    func: Callable,
    *args,
    max_attempts: int = 10,
    **kwargs
) -> Any:
    """
    便捷函数：持续执行直到成功

    示例:
        result = execute_with_persistence(
            subprocess.run,
            ['python', 'script.py'],
            capture_output=True
        )
    """
    executor = ResilientExecutor(max_attempts=max_attempts)
    result = asyncio.run(executor.execute(func, *args, **kwargs))

    if result.success:
        return result.result
    else:
        raise Exception(f"执行失败: {result.error_message}")


# 测试代码
if __name__ == "__main__":
    import os
    import shutil

    async def test_resilient_executor():
        print("=" * 60)
        print("🧪 弹性执行器测试")
        print("=" * 60)

        executor = ResilientExecutor(max_attempts=5, verbose=True)

        # 测试1: 正常执行
        print("\n测试1: 正常执行")
        result = await executor.execute(lambda: "Hello World")
        print(f"结果: {result.result}")

        # 测试2: 失败后重试成功
        print("\n测试2: 失败后重试成功")
        attempt_count = 0
        def flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception(f"模拟失败 #{attempt_count}")
            return f"成功！尝试了 {attempt_count} 次"

        result = await executor.execute(flaky_function)
        print(f"结果: {result.result}")
        print(f"尝试次数: {len(result.attempts)}")

        # 测试3: 参数自动修正
        print("\n测试3: 参数自动修正")
        def test_func(command):
            return f"执行命令: {command}"

        # 使用错误的参数名
        result = await executor.execute(test_func, cmd="echo hello")
        print(f"结果: {result.result if result.success else result.error_message}")

        print("\n" + "=" * 60)
        print("✅ 测试完成")
        print("=" * 60)

    asyncio.run(test_resilient_executor())
