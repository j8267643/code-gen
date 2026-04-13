"""
Code execution and calculator tools
Inspired by PraisonAI's code tools
"""
import ast
import io
import sys
import traceback
import subprocess
import tempfile
import os
import signal
import logging
from typing import Any, Dict, Set
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

from code_gen.tools.base import Tool, ToolResult

# 配置日志
logger = logging.getLogger(__name__)


class PythonExecuteTool(Tool):
    """Execute Python code safely with sandbox restrictions"""
    
    name = "python_execute"
    description = "Execute Python code in a sandboxed environment with strict security controls. Returns stdout, stderr, and any return value."
    input_schema = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Execution timeout in seconds (max 60)",
                "default": 10,
            },
        },
        "required": ["code"],
    }
    
    # 限制的内置函数（危险操作）
    RESTRICTED_BUILTINS: Set[str] = {
        # 代码执行相关
        'eval', 'exec', 'compile', '__import__',
        # 输入/交互相关
        'input', 'raw_input', 'breakpoint',
        # 退出相关
        'exit', 'quit', 'reload',
        # 属性操作（可能用于绕过限制）
        'getattr', 'setattr', 'delattr',
        # 命名空间操作（可能泄露信息）
        'globals', 'locals', 'vars',
        # 文件操作
        'open',
        # 帮助/信息泄露
        'help', 'copyright', 'credits', 'license',
    }
    
    # 允许的安全内置函数
    ALLOWED_BUILTINS: Set[str] = {
        # 数学运算
        'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
        'chr', 'complex', 'dict', 'divmod', 'enumerate', 'filter', 'float',
        'format', 'frozenset', 'hex', 'int', 'iter', 'len', 'list', 'map',
        'max', 'min', 'next', 'oct', 'ord', 'pow', 'print', 'range',
        'repr', 'reversed', 'round', 'set', 'slice', 'sorted', 'str',
        'sum', 'tuple', 'zip',
        # 类型检查（安全的）
        'type', 'isinstance', 'callable', 'issubclass', 'hasattr', 'dir',
        'id', 'hash',
        # 面向对象
        'staticmethod', 'classmethod', 'property', 'super', 'object',
        # 常量
        'True', 'False', 'None', 'NotImplemented', 'Ellipsis', '__debug__',
        # 异常类
        'Exception', 'TypeError', 'ValueError', 'KeyError', 'IndexError',
        'AttributeError', 'RuntimeError', 'StopIteration', 'ArithmeticError',
        'LookupError', 'AssertionError', 'BufferError', 'EOFError',
        'ImportError', 'ModuleNotFoundError', 'NameError', 'OSError',
        'IOError', 'BlockingIOError', 'ChildProcessError', 'ConnectionError',
        'BrokenPipeError', 'ConnectionAbortedError', 'ConnectionRefusedError',
        'ConnectionResetError', 'FileExistsError', 'FileNotFoundError',
        'InterruptedError', 'IsADirectoryError', 'NotADirectoryError',
        'PermissionError', 'ProcessLookupError', 'TimeoutError',
        'ReferenceError', 'SyntaxError', 'IndentationError', 'TabError',
        'SystemError', 'UnicodeError', 'UnicodeDecodeError', 'UnicodeEncodeError',
        'UnicodeTranslateError', 'Warning', 'UserWarning', 'DeprecationWarning',
        'PendingDeprecationWarning', 'SyntaxWarning', 'RuntimeWarning',
        'FutureWarning', 'ImportWarning', 'UnicodeWarning', 'BytesWarning',
        'ResourceWarning',
        # 特殊属性
        '__name__', '__doc__', '__package__', '__spec__', '__annotations__',
        '__builtins__', '__cached__', '__file__', '__loader__'
    }
    
    def __init__(self):
        super().__init__()
        self.execution_log: list = []
    
    async def execute(self, code: str, timeout: int = 10) -> ToolResult:
        """
        在沙箱环境中执行 Python 代码
        
        安全措施：
        1. AST 静态分析检测危险代码
        2. 限制执行时间
        3. 禁用危险内置函数
        4. 记录执行日志
        """
        # 限制最大超时时间
        timeout = min(timeout, 60)
        
        # 记录执行请求
        execution_id = self._log_execution_request(code, timeout)
        
        try:
            # Security check - AST 静态分析
            if self._is_dangerous_code(code):
                self._log_execution_result(execution_id, False, "Security check failed")
                return ToolResult(
                    success=False,
                    content="",
                    error="Code contains potentially dangerous operations and was blocked by security check"
                )
            
            # 使用子进程执行代码（真正的沙箱）
            result = await self._execute_in_subprocess(code, timeout)
            
            self._log_execution_result(
                execution_id, 
                result.success, 
                result.error if not result.success else "Success"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Execution failed: {str(e)}"
            self._log_execution_result(execution_id, False, error_msg)
            return ToolResult(
                success=False,
                content="",
                error=error_msg
            )
    
    def _log_execution_request(self, code: str, timeout: int) -> str:
        """记录执行请求"""
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(code) % 10000}"
        log_entry = {
            'id': execution_id,
            'timestamp': datetime.now().isoformat(),
            'code': code[:500],  # 限制日志长度
            'timeout': timeout,
            'status': 'started'
        }
        self.execution_log.append(log_entry)
        logger.info(f"Code execution request: {execution_id}")
        return execution_id
    
    def _log_execution_result(self, execution_id: str, success: bool, message: str):
        """记录执行结果"""
        for entry in self.execution_log:
            if entry['id'] == execution_id:
                entry['status'] = 'success' if success else 'failed'
                entry['message'] = message
                break
        logger.info(f"Code execution result: {execution_id} - {'success' if success else 'failed'}")
    
    async def _execute_in_subprocess(self, code: str, timeout: int) -> ToolResult:
        """在子进程中执行代码，提供真正的隔离"""
        import asyncio
        
        # 创建安全的执行脚本
        safe_code = self._create_safe_execution_script(code)
        temp_file = None
        
        try:
            # 创建临时文件（使用 UTF-8 编码）
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(safe_code)
                temp_file = f.name
            
            # 在子进程中执行
            process = await asyncio.create_subprocess_exec(
                sys.executable, temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024  # 限制输出大小 1MB
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                
                stdout_str = stdout.decode('utf-8', errors='replace')[:10000]  # 限制输出
                stderr_str = stderr.decode('utf-8', errors='replace')[:10000]
                
                if process.returncode != 0:
                    return ToolResult(
                        success=False,
                        content=stdout_str,
                        error=f"Process exited with code {process.returncode}: {stderr_str}"
                    )
                
                return ToolResult(
                    success=True,
                    content=stdout_str if stdout_str else "Code executed successfully (no output)",
                    data={
                        "stdout": stdout_str,
                        "stderr": stderr_str,
                        "returncode": process.returncode
                    }
                )
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Code execution timed out after {timeout} seconds"
                )
                
        finally:
            # 确保清理临时文件
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary file {temp_file}: {e}")
    
    def _create_safe_execution_script(self, code: str) -> str:
        """创建安全的执行脚本，限制内置函数"""
        allowed_builtins = ', '.join(f"'{b}'" for b in self.ALLOWED_BUILTINS)
        
        script = f'''
import sys
import builtins

# 保存原始的 print
_original_print = print

# 创建受限的内置函数命名空间
safe_builtins = {{}}
for name in [{allowed_builtins}]:
    if hasattr(builtins, name):
        safe_builtins[name] = getattr(builtins, name)

# 添加安全的 print 函数
def safe_print(*args, **kwargs):
    return _original_print(*args, **kwargs)

safe_builtins['print'] = safe_print

# 替换全局内置函数
__builtins__ = safe_builtins

# 执行用户代码
try:
{self._indent_code(code)}
except Exception as e:
    print(f"Error: {{e}}", file=sys.stderr)
    sys.exit(1)
'''
        return script
    
    def _indent_code(self, code: str) -> str:
        """缩进代码块"""
        lines = code.strip().split('\n')
        return '\n'.join('    ' + line for line in lines)
    
    def _is_dangerous_code(self, code: str) -> bool:
        """
        使用 AST 进行严格的安全检查
        
        检测危险操作：
        - 导入危险模块 (os, sys, subprocess, etc.)
        - 调用危险函数 (eval, exec, compile, open, etc.)
        - 文件操作
        - 网络操作
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return False  # 语法错误会在执行时捕获
        
        # 危险模块和别名映射
        dangerous_modules = {
            'os', 'sys', 'subprocess', 'importlib', 'builtins', '__builtin__',
            'socket', 'urllib', 'http', 'ftplib', 'smtplib', 'telnetlib',
            'pickle', 'marshal', 'ctypes', 'mmap', 'shlex', 'pty', 'tty',
            'platform', 'pwd', 'grp', 'spwd', 'crypt', 'termios', 'resource',
            'nis', 'nis', 'dbm', 'gdbm', 'dbhash', 'bsddb185', 'bsddb3'
        }
        
        # 危险函数名
        dangerous_functions = {
            'eval', 'exec', 'compile', 'open', '__import__', 'input',
            'raw_input', 'reload', 'exit', 'quit', 'help',
            'getattr', 'setattr', 'delattr', 'hasattr',
            'globals', 'locals', 'vars', 'dir',
            'breakpoint', 'copyright', 'credits', 'license'
        }
        
        # 收集导入的模块及其别名
        imported_modules = {}  # name -> real_module
        
        for node in ast.walk(tree):
            # 检查导入语句
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split('.')[0]
                    if module_name in dangerous_modules:
                        return True
                    # 记录别名
                    asname = alias.asname if alias.asname else alias.name
                    imported_modules[asname] = module_name
                    
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split('.')[0]
                    if module_name in dangerous_modules:
                        return True
                    # 记录 from xxx import yyy as zzz
                    for alias in node.names:
                        asname = alias.asname if alias.asname else alias.name
                        imported_modules[asname] = f"{module_name}.{alias.name}"
            
            # 检查函数调用
            elif isinstance(node, ast.Call):
                func_name = self._get_call_name(node.func)
                if func_name:
                    # 直接调用危险函数
                    if func_name in dangerous_functions:
                        return True
                    # 通过别名调用危险模块的函数
                    parts = func_name.split('.')
                    if parts[0] in imported_modules:
                        return True
                    # 检查 os.system, subprocess.call 等
                    if len(parts) >= 2:
                        if parts[0] in dangerous_modules:
                            return True
            
            # 检查属性访问（可能通过 getattr 等）
            elif isinstance(node, ast.Attribute):
                if node.attr in ('system', 'popen', 'spawn', 'fork', 'kill', 
                                'remove', 'unlink', 'rmdir', 'mkdir', 'makedirs',
                                'rename', 'replace', 'link', 'symlink'):
                    return True
            
            # 检查 __import__ 调用
            elif isinstance(node, ast.Name):
                if node.id == '__import__':
                    return True
        
        return False
    
    def _get_call_name(self, node) -> str:
        """获取函数调用的完整名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_call_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        return ""


class CalculatorTool(Tool):
    """Perform mathematical calculations"""
    
    name = "calculator"
    description = "Perform mathematical calculations. Supports basic arithmetic, scientific functions, and unit conversions."
    input_schema = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to evaluate (e.g., '2 + 2', 'sin(pi/2)', 'sqrt(16)')",
            },
        },
        "required": ["expression"],
    }
    
    async def execute(self, expression: str) -> ToolResult:
        try:
            # Clean the expression
            expression = expression.strip()
            
            # Create safe evaluation environment
            safe_dict = {
                'abs': abs,
                'round': round,
                'max': max,
                'min': min,
                'sum': sum,
                'pow': pow,
            }
            
            # Add math functions
            import math
            math_funcs = {
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'asin': math.asin,
                'acos': math.acos,
                'atan': math.atan,
                'sinh': math.sinh,
                'cosh': math.cosh,
                'tanh': math.tanh,
                'sqrt': math.sqrt,
                'log': math.log,
                'log10': math.log10,
                'log2': math.log2,
                'exp': math.exp,
                'ceil': math.ceil,
                'floor': math.floor,
                'factorial': math.factorial,
                'pi': math.pi,
                'e': math.e,
                'degrees': math.degrees,
                'radians': math.radians,
            }
            safe_dict.update(math_funcs)
            
            # Evaluate the expression
            try:
                result = eval(expression, {"__builtins__": {}}, safe_dict)
                
                # Format result
                if isinstance(result, float):
                    # Round to avoid floating point issues
                    result = round(result, 10)
                    # Remove trailing zeros
                    result_str = str(result).rstrip('0').rstrip('.') if '.' in str(result) else str(result)
                else:
                    result_str = str(result)
                
                return ToolResult(
                    success=True,
                    content=f"{expression} = {result_str}",
                    data={"expression": expression, "result": result}
                )
                
            except SyntaxError as e:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Invalid expression syntax: {str(e)}"
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Calculation error: {str(e)}"
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Calculator failed: {str(e)}"
            )


class CodeAnalyzerTool(Tool):
    """Analyze code for issues and improvements"""
    
    name = "code_analyzer"
    description = "Analyze Python code for syntax errors, style issues, and potential bugs."
    input_schema = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to analyze",
            },
        },
        "required": ["code"],
    }
    
    async def execute(self, code: str) -> ToolResult:
        try:
            issues = []
            
            # Check syntax
            try:
                ast.parse(code)
                issues.append("✓ Syntax is valid")
            except SyntaxError as e:
                issues.append(f"✗ Syntax error: {e}")
                return ToolResult(
                    success=False,
                    content="\n".join(issues),
                    error=f"Syntax error at line {e.lineno}: {e.msg}"
                )
            
            # Basic code analysis
            tree = ast.parse(code)
            
            # Count different elements
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
            
            issues.append(f"\n📊 Code Statistics:")
            issues.append(f"  - Functions: {len(functions)}")
            issues.append(f"  - Classes: {len(classes)}")
            issues.append(f"  - Imports: {len(imports)}")
            
            # Check for common issues
            issues.append("\n🔍 Analysis:")
            
            # Check for bare except
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        issues.append("  ⚠️ Found bare 'except:' clause - consider catching specific exceptions")
            
            # Check for long lines
            lines = code.split('\n')
            long_lines = [(i+1, len(line)) for i, line in enumerate(lines) if len(line) > 100]
            if long_lines:
                issues.append(f"  ⚠️ {len(long_lines)} lines exceed 100 characters")
            
            # Check for TODO/FIXME
            todo_count = sum(1 for line in lines if 'TODO' in line.upper() or 'FIXME' in line.upper())
            if todo_count > 0:
                issues.append(f"  ℹ️ Found {todo_count} TODO/FIXME comments")
            
            if len(issues) == 3:  # Only header lines
                issues.append("  ✓ No obvious issues found")
            
            return ToolResult(
                success=True,
                content="\n".join(issues),
                data={
                    "functions": len(functions),
                    "classes": len(classes),
                    "imports": len(imports),
                    "lines": len(lines)
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Analysis failed: {str(e)}"
            )
