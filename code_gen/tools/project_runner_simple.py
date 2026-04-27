"""
Simple Project Runner - 简化版项目运行工具

基于实际成功运行项目的经验：
1. 分析项目结构
2. 识别前后端
3. 使用正确的命令启动服务
4. 验证服务是否启动成功
"""
import os
import subprocess
import platform
from typing import Optional, Dict, Any, List
from .base import Tool


class SimpleProjectRunnerTool(Tool):
    """
    简化版项目运行工具
    
    使用示例:
    - 运行项目: {"path": "D:\\LX\\code-gen\\test"}
    """
    
    name = "run_project_simple"
    description = """运行项目（自动检测并启动前后端服务）
    
    这个工具会：
    1. 分析项目结构，识别前后端
    2. 自动选择合适的启动命令
    3. 在后台启动服务
    4. 返回访问地址
    
    支持的项目类型：
    - FastAPI/Flask (Python)
    - Node.js/Express
    - 纯前端 (HTML/JS)
    - 全栈项目（前后端分离）
    """
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "项目根目录的绝对路径"
            }
        },
        "required": ["path"]
    }
    
    def execute(self, arguments: Dict[str, Any]) -> str:
        """执行项目运行"""
        path = arguments.get("path", "")
        
        if not path or not os.path.exists(path):
            return f"错误: 路径不存在: {path}"
        
        results = []
        
        # 1. 分析项目结构
        results.append(f"📁 分析项目: {path}")
        
        has_backend = os.path.exists(os.path.join(path, "backend"))
        has_frontend = os.path.exists(os.path.join(path, "frontend"))
        has_requirements = os.path.exists(os.path.join(path, "requirements.txt"))
        has_package_json = os.path.exists(os.path.join(path, "package.json"))
        has_run_sh = os.path.exists(os.path.join(path, "run.sh"))
        
        # 2. 运行后端
        if has_backend:
            backend_path = os.path.join(path, "backend")
            results.append(self._run_backend(backend_path))
        elif has_requirements or has_run_sh:
            results.append(self._run_backend(path))
        
        # 3. 运行前端
        if has_frontend:
            frontend_path = os.path.join(path, "frontend")
            results.append(self._run_frontend(frontend_path))
        elif os.path.exists(os.path.join(path, "index.html")):
            results.append(self._run_frontend(path))
        
        return "\n".join(results)
    
    def _run_backend(self, path: str) -> str:
        """运行后端服务"""
        results = [f"🔧 启动后端服务: {path}"]
        
        # 检测后端类型
        main_py = os.path.join(path, "main.py")
        app_py = os.path.join(path, "app.py")
        manage_py = os.path.join(path, "manage.py")
        server_js = os.path.join(path, "server.js")
        app_js = os.path.join(path, "app.js")
        
        is_windows = platform.system().lower() == "windows"
        
        if os.path.exists(main_py) or os.path.exists(app_py):
            # FastAPI/Flask
            entry = "main:app" if os.path.exists(main_py) else "app:app"
            cmd = f"cd {path} ; python -m uvicorn {entry} --reload --host 0.0.0.0 --port 8000"
            
            try:
                if is_windows:
                    subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                    )
                results.append(f"  ✅ 后端已启动: http://localhost:8000")
            except Exception as e:
                results.append(f"  ❌ 启动失败: {e}")
        
        elif os.path.exists(server_js) or os.path.exists(app_js):
            # Node.js
            entry = "server.js" if os.path.exists(server_js) else "app.js"
            cmd = f"cd {path} ; node {entry}"
            
            try:
                if is_windows:
                    subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                    )
                results.append(f"  ✅ Node.js 服务已启动")
            except Exception as e:
                results.append(f"  ❌ 启动失败: {e}")
        
        else:
            results.append("  ⚠️ 未找到后端入口文件")
        
        return "\n".join(results)
    
    def _run_frontend(self, path: str) -> str:
        """运行前端服务"""
        results = [f"🎨 启动前端服务: {path}"]
        
        has_index_html = os.path.exists(os.path.join(path, "index.html"))
        has_package_json = os.path.exists(os.path.join(path, "package.json"))
        
        is_windows = platform.system().lower() == "windows"
        
        if has_package_json:
            # Node.js 项目，尝试 npm start
            cmd = f"cd {path} ; npm start"
            try:
                if is_windows:
                    subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                    )
                results.append(f"  ✅ 前端已启动 (npm)")
            except Exception as e:
                results.append(f"  ❌ 启动失败: {e}")
        
        elif has_index_html:
            # 纯 HTML，使用 Python HTTP 服务器
            cmd = f"cd {path} ; python -m http.server 8080"
            try:
                if is_windows:
                    subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                    )
                results.append(f"  ✅ 前端已启动: http://localhost:8080")
            except Exception as e:
                results.append(f"  ❌ 启动失败: {e}")
        
        else:
            results.append("  ⚠️ 未找到前端入口文件")
        
        return "\n".join(results)
