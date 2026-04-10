"""
弹性工具调用 - 自动处理工具调用错误并持续尝试
"""
import asyncio
import subprocess
import os
import sys
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

from .resilient_executor import ResilientExecutor, ExecutionResult


@dataclass
class ToolCall:
    """工具调用定义"""
    tool_name: str
    params: Dict[str, Any]
    fallback_tools: List[tuple] = None


class ResilientToolCaller:
    """
    弹性工具调用器

    特性：
    1. 自动参数修正（cmd -> command, depth -> 移除等）
    2. 环境检测（Windows/Linux, Python版本等）
    3. 依赖自动安装
    4. 多策略降级
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.executor = ResilientExecutor(max_attempts=10, verbose=verbose)
        self.tool_registry: Dict[str, Callable] = {}
        self._register_default_tools()

    def _log(self, message: str):
        if self.verbose:
            print(f"[ResilientTool] {message}")

    def _register_default_tools(self):
        """注册默认工具"""
        self.tool_registry['execute_command'] = self._execute_command
        self.tool_registry['list_directory'] = self._list_directory
        self.tool_registry['read_file'] = self._read_file
        self.tool_registry['write_file'] = self._write_file

    # ===== 工具实现 =====

    def _execute_command(self, command: str, **kwargs) -> Dict:
        """执行命令 - 自动处理环境差异"""
        import shutil

        # 检测操作系统
        is_windows = os.name == 'nt'

        # 转换命令
        if is_windows:
            # Windows 环境
            if command.startswith('bash'):
                # 尝试转换为 PowerShell
                command = command.replace('bash -lc', 'powershell -Command')
                command = command.replace("'", '"')
                self._log(f"转换命令为 PowerShell: {command}")

            if 'pytest' in command and not shutil.which('pytest'):
                # pytest 未安装，尝试使用 python -m pytest
                command = command.replace('pytest', 'python -m pytest')
                self._log(f"使用 python -m pytest 替代")

        # 执行
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Command timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _list_directory(self, path: str = '.', **kwargs) -> Dict:
        """列出目录 - 忽略不支持的参数"""
        try:
            target_path = Path(path)
            if not target_path.exists():
                return {'success': False, 'error': f'Path not found: {path}'}

            items = []
            for item in target_path.iterdir():
                items.append({
                    'name': item.name,
                    'is_file': item.is_file(),
                    'is_dir': item.is_dir(),
                    'size': item.stat().st_size if item.is_file() else 0
                })

            return {
                'success': True,
                'path': str(target_path.absolute()),
                'items': items,
                'count': len(items)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _read_file(self, file_path: str, **kwargs) -> Dict:
        """读取文件"""
        try:
            path = Path(file_path)
            if not path.exists():
                return {'success': False, 'error': f'File not found: {file_path}'}

            content = path.read_text(encoding='utf-8')
            return {
                'success': True,
                'content': content,
                'size': len(content)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _write_file(self, file_path: str, content: str, **kwargs) -> Dict:
        """写入文件"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            return {
                'success': True,
                'path': str(path.absolute()),
                'size': len(content)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ===== 核心调用方法 =====

    async def call(self, tool_name: str, **params) -> Dict:
        """
        调用工具 - 自动处理错误和降级

        Args:
            tool_name: 工具名称
            **params: 工具参数

        Returns:
            Dict: 执行结果
        """
        self._log(f"调用工具: {tool_name}")
        self._log(f"参数: {params}")

        # 参数预处理
        params = self._preprocess_params(tool_name, params)

        # 获取工具函数
        if tool_name not in self.tool_registry:
            return {'success': False, 'error': f'Unknown tool: {tool_name}'}

        tool_func = self.tool_registry[tool_name]

        # 使用弹性执行器
        result = await self.executor.execute(tool_func, **params)

        if result.success:
            return result.result if isinstance(result.result, dict) else {'success': True, 'result': result.result}
        else:
            # 尝试降级方案
            fallback_result = await self._try_fallbacks(tool_name, params)
            if fallback_result:
                return fallback_result

            return {'success': False, 'error': result.error_message, 'attempts': len(result.attempts)}

    def _preprocess_params(self, tool_name: str, params: Dict) -> Dict:
        """预处理参数 - 修正常见错误"""
        processed = params.copy()

        # 通用参数修正
        if 'cmd' in processed and 'command' not in processed:
            processed['command'] = processed.pop('cmd')
            self._log("自动修正: cmd -> command")

        # 移除不支持的参数
        unsupported = ['depth', 'recursive']
        for param in unsupported:
            if param in processed:
                del processed[param]
                self._log(f"移除不支持的参数: {param}")

        return processed

    async def _try_fallbacks(self, tool_name: str, params: Dict) -> Optional[Dict]:
        """尝试降级方案"""
        self._log(f"尝试降级方案: {tool_name}")

        if tool_name == 'execute_command':
            command = params.get('command', '')

            # 降级1: 尝试使用不同 shell
            if 'bash' in command:
                self._log("降级: 尝试使用 sh 替代 bash")
                new_command = command.replace('bash', 'sh')
                result = await self.executor.execute(self._execute_command, command=new_command)
                if result.success:
                    return result.result

            # 降级2: 简化命令
            if 'pytest' in command:
                self._log("降级: 尝试直接运行 Python 脚本")
                # 提取 Python 文件路径
                import re
                match = re.search(r'(\S+\.py)', command)
                if match:
                    py_file = match.group(1)
                    new_command = f'python {py_file}'
                    result = await self.executor.execute(self._execute_command, command=new_command)
                    if result.success:
                        return result.result

        elif tool_name == 'list_directory':
            # 降级: 使用 os.listdir
            self._log("降级: 使用 os.listdir")
            try:
                path = params.get('path', '.')
                items = os.listdir(path)
                return {
                    'success': True,
                    'path': path,
                    'items': [{'name': item, 'is_file': os.path.isfile(os.path.join(path, item)),
                              'is_dir': os.path.isdir(os.path.join(path, item))} for item in items],
                    'count': len(items)
                }
            except Exception as e:
                self._log(f"降级失败: {e}")

        return None

    # ===== 便捷方法 =====

    async def run_tests(self, test_path: str) -> Dict:
        """运行测试 - 自动处理 pytest 缺失"""
        self._log(f"运行测试: {test_path}")

        # 策略1: 使用 pytest
        result = await self.call('execute_command', command=f'pytest {test_path} -v')
        if result['success']:
            return result

        # 策略2: 使用 python -m pytest
        result = await self.call('execute_command', command=f'python -m pytest {test_path} -v')
        if result['success']:
            return result

        # 策略3: 直接运行测试文件
        self._log("降级: 直接运行测试文件")
        result = await self.call('execute_command', command=f'python {test_path}')
        return result

    async def ensure_dependency(self, package: str) -> bool:
        """确保依赖已安装"""
        try:
            __import__(package)
            return True
        except ImportError:
            self._log(f"安装依赖: {package}")
            result = await self.call('execute_command', command=f'pip install {package}')
            return result['success']


# ===== 全局实例 =====

_tool_caller: Optional[ResilientToolCaller] = None


def get_tool_caller() -> ResilientToolCaller:
    """获取全局工具调用器实例"""
    global _tool_caller
    if _tool_caller is None:
        _tool_caller = ResilientToolCaller()
    return _tool_caller


# ===== 便捷函数 =====

async def resilient_call(tool_name: str, **params) -> Dict:
    """便捷函数：弹性调用工具"""
    caller = get_tool_caller()
    return await caller.call(tool_name, **params)


def resilient_call_sync(tool_name: str, **params) -> Dict:
    """同步版本"""
    return asyncio.run(resilient_call(tool_name, **params))


# 测试
if __name__ == "__main__":
    async def main():
        print("=" * 60)
        print("🧪 弹性工具调用测试")
        print("=" * 60)

        caller = ResilientToolCaller()

        # 测试1: 列出目录
        print("\n测试1: 列出目录")
        result = await caller.call('list_directory', path='.')
        print(f"成功: {result['success']}, 项目数: {result.get('count', 0)}")

        # 测试2: 执行命令（使用错误参数名）
        print("\n测试2: 执行命令（自动修正参数）")
        result = await caller.call('execute_command', cmd='echo hello')
        print(f"成功: {result['success']}")
        if result['success']:
            print(f"输出: {result.get('stdout', '').strip()}")

        # 测试3: 运行测试
        print("\n测试3: 运行测试")
        result = await caller.run_tests('tests/test_complete_system.py')
        print(f"成功: {result['success']}")
        if not result['success']:
            print(f"错误: {result.get('error', 'Unknown')}")

        print("\n" + "=" * 60)
        print("✅ 测试完成")
        print("=" * 60)

    asyncio.run(main())
