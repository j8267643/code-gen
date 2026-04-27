"""
Smart Project Runner - 智能项目运行工具
封装完整的项目运行工作流，处理各种边界情况
"""
import subprocess
import platform
import time
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

from code_gen.tools.base import Tool, ToolResult


class RunStatus(Enum):
    """运行状态"""
    SUCCESS = "success"
    FAILED = "failed"
    PORT_IN_USE = "port_in_use"
    ALREADY_RUNNING = "already_running"
    TIMEOUT = "timeout"


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    command: str
    port: int
    cwd: str
    url: str


class ProjectRunnerTool(Tool):
    """
    智能项目运行工具 - 一键运行完整项目
    自动处理端口占用、依赖安装、前后端启动等
    """
    
    name = "run_project"
    description = """一键运行完整项目（全栈项目自动运行前后端）
    
    这个工具会：
    1. 自动分析项目结构
    2. 检查并释放被占用的端口
    3. 安装依赖（如果需要）
    4. 启动所有服务（前后端）
    5. 返回所有服务的访问地址
    
    适用于：
    - 单服务后端项目（FastAPI/Flask/Django）
    - 单服务前端项目（React/Vue/静态页面）
    - 全栈项目（前后端同时运行）
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "项目根目录的绝对路径",
            },
            "install_deps": {
                "type": "boolean",
                "description": "是否自动安装依赖（默认：true）",
                "default": True,
            },
        },
        "required": ["path"],
    }
    
    async def execute(self, path: str, install_deps: bool = True) -> ToolResult:
        """执行项目运行"""
        try:
            project_path = Path(path)
            if not project_path.exists():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"项目路径不存在: {path}"
                )
            
            # 步骤1：分析项目
            analysis = await self._analyze_project(project_path)
            if not analysis:
                return ToolResult(
                    success=False,
                    content="",
                    error="无法分析项目结构"
                )
            
            results = []
            services = []
            
            # 收集所有需要运行的服务
            if analysis.get("is_fullstack"):
                # 全栈项目 - 运行前后端
                for comp in analysis.get("components", []):
                    services.append(ServiceInfo(
                        name=comp["name"],
                        command=comp["run_command"],
                        port=comp["port"],
                        cwd=str(project_path / comp["path"]) if comp.get("path") else str(project_path),
                        url=f"http://localhost:{comp['port']}"
                    ))
            else:
                # 单服务项目
                services.append(ServiceInfo(
                    name=analysis.get("project_type", "main"),
                    command=analysis["run_command"],
                    port=analysis.get("port", 8000),
                    cwd=str(project_path),
                    url=f"http://localhost:{analysis.get('port', 8000)}"
                ))
            
            # 步骤2：安装依赖
            if install_deps and analysis.get("install_command"):
                install_result = await self._install_dependencies(
                    analysis["install_command"],
                    str(project_path)
                )
                results.append(f"📦 依赖安装: {install_result}")
            
            # 步骤3：运行每个服务
            for service in services:
                result = await self._run_service(service)
                results.append(result)
            
            # 汇总结果
            summary = "\n".join(results)
            return ToolResult(
                success=True,
                content=summary,
                error=None
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"运行项目失败: {str(e)}"
            )
    
    async def _analyze_project(self, project_path: Path) -> Optional[Dict]:
        """分析项目结构"""
        try:
            from code_gen.project_analyzer import ProjectAnalyzer
            analyzer = ProjectAnalyzer(str(project_path))
            info = analyzer.analyze()
            return info.to_dict()
        except Exception as e:
            print(f"分析项目失败: {e}")
            return None
    
    async def _install_dependencies(self, install_command: str, cwd: str) -> str:
        """安装依赖"""
        try:
            result = subprocess.run(
                install_command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                return "✅ 成功"
            else:
                return f"⚠️ 警告: {result.stderr[:200]}"
        except subprocess.TimeoutExpired:
            return "⏱️ 超时（可能仍在后台安装）"
        except Exception as e:
            return f"❌ 失败: {str(e)}"
    
    async def _run_service(self, service: ServiceInfo) -> str:
        """运行单个服务，处理端口占用等问题"""
        lines = [f"\n🚀 {service.name.upper()} SERVICE"]
        lines.append(f"   命令: {service.command}")
        lines.append(f"   端口: {service.port}")
        
        # 检查端口占用
        if self._is_port_in_use(service.port):
            lines.append(f"   ⚠️ 端口 {service.port} 被占用，尝试释放...")
            
            # 尝试多种方式释放端口
            freed = await self._free_port(service.port)
            if not freed:
                lines.append(f"   ❌ 无法释放端口 {service.port}")
                lines.append(f"   💡 建议: 手动检查并关闭占用端口的程序")
                return "\n".join(lines)
            else:
                lines.append(f"   ✅ 端口已释放")
        
        # 启动服务
        try:
            process = self._start_service(service)
            if process:
                # 等待服务启动
                await asyncio.sleep(3)
                
                # 检查是否成功启动
                if self._is_port_in_use(service.port):
                    lines.append(f"   ✅ 服务已启动")
                    lines.append(f"   🌐 访问地址: {service.url}")
                else:
                    # 检查进程是否还在运行
                    if process.poll() is None:
                        lines.append(f"   ⚠️ 服务正在启动中，请稍后检查")
                        lines.append(f"   🌐 预期地址: {service.url}")
                    else:
                        # 进程已退出，返回码不为0
                        return_code = process.returncode
                        lines.append(f"   ❌ 启动失败 (退出码: {return_code})")
                        lines.append(f"   💡 建议: 检查命令是否正确，依赖是否安装")
            else:
                lines.append(f"   ❌ 无法创建进程")
        except Exception as e:
            lines.append(f"   ❌ 错误: {str(e)}")
            import traceback
            lines.append(f"   [dim]{traceback.format_exc()[:200]}[/dim]")
        
        return "\n".join(lines)
    
    def _is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', port))
                return result == 0
        except:
            return False
    
    async def _free_port(self, port: int) -> bool:
        """尝试释放端口 - 多种方法"""
        is_windows = platform.system().lower() == "windows"
        
        # 方法1: 通过端口查找并杀死进程
        try:
            if is_windows:
                # 获取占用端口的PID
                result = subprocess.run(
                    f"netstat -ano | findstr :{port}",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                pids = set()
                for line in result.stdout.split('\n'):
                    if f":{port}" in line and ("LISTENING" in line or "ESTABLISHED" in line):
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            try:
                                pid = int(parts[-1])
                                pids.add(pid)
                            except:
                                pass
                
                # 杀死所有相关进程
                for pid in pids:
                    try:
                        subprocess.run(
                            f"taskkill /PID {pid} /F",
                            shell=True,
                            capture_output=True,
                            timeout=5
                        )
                    except:
                        pass
            else:
                # Linux/Mac
                result = subprocess.run(
                    f"lsof -ti :{port}",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                for pid_str in result.stdout.strip().split('\n'):
                    if pid_str:
                        try:
                            pid = int(pid_str)
                            subprocess.run(
                                f"kill -9 {pid}",
                                shell=True,
                                capture_output=True,
                                timeout=5
                            )
                        except:
                            pass
            
            # 等待端口释放
            await asyncio.sleep(1)
            
            # 检查是否成功
            if not self._is_port_in_use(port):
                return True
                
        except Exception as e:
            print(f"释放端口失败: {e}")
        
        # 方法2: 尝试使用taskkill /F /IM 强制终止常见进程名
        try:
            if is_windows:
                common_names = ["python.exe", "uvicorn.exe", "node.exe"]
                for name in common_names:
                    subprocess.run(
                        f"taskkill /F /IM {name} 2>nul",
                        shell=True,
                        capture_output=True,
                        timeout=3
                    )
            await asyncio.sleep(1)
            
            if not self._is_port_in_use(port):
                return True
        except:
            pass
        
        return False
    
    def _start_service(self, service: ServiceInfo) -> Optional[subprocess.Popen]:
        """启动服务进程"""
        try:
            is_windows = platform.system().lower() == "windows"
            
            # 使用 DEVNULL 避免管道缓冲区问题
            import subprocess
            
            if is_windows:
                # Windows: 使用creationflags创建独立进程
                # 将输出重定向到 DEVNULL 避免阻塞
                process = subprocess.Popen(
                    service.command,
                    shell=True,
                    cwd=service.cwd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                # Unix/Linux/Mac
                process = subprocess.Popen(
                    service.command,
                    shell=True,
                    cwd=service.cwd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                )
            
            return process
        except Exception as e:
            print(f"启动服务失败: {e}")
            import traceback
            traceback.print_exc()
            return None
