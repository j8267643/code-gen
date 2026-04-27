"""
Project Analyzer - Analyze project structure and determine how to run it
Similar to how Claude analyzes projects before running
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ProjectType(Enum):
    """Project type enumeration"""
    FASTAPI = "fastapi"
    FLASK = "flask"
    DJANGO = "django"
    REACT = "react"
    VUE = "vue"
    ANGULAR = "angular"
    NODEJS = "nodejs"
    PYTHON_SCRIPT = "python_script"
    HTML_STATIC = "html_static"
    UNKNOWN = "unknown"


@dataclass
class ProjectComponent:
    """Individual project component (frontend or backend)"""
    name: str  # "frontend" or "backend"
    project_type: ProjectType
    entry_file: Optional[str]
    run_command: str
    install_command: Optional[str]
    port: Optional[int]
    path: str  # relative path to component


@dataclass
class ProjectInfo:
    """Project information"""
    project_type: ProjectType
    entry_file: Optional[str]
    run_command: str
    install_command: Optional[str]
    requirements_file: Optional[str]
    detected_files: List[str]
    framework_version: Optional[str] = None
    port: Optional[int] = None
    # Full-stack support
    is_fullstack: bool = False
    components: List[ProjectComponent] = None
    
    def __post_init__(self):
        if self.components is None:
            self.components = []
    
    def to_dict(self) -> dict:
        return {
            "project_type": self.project_type.value,
            "entry_file": self.entry_file,
            "run_command": self.run_command,
            "install_command": self.install_command,
            "requirements_file": self.requirements_file,
            "detected_files": self.detected_files,
            "framework_version": self.framework_version,
            "port": self.port,
            "is_fullstack": self.is_fullstack,
            "components": [
                {
                    "name": c.name,
                    "type": c.project_type.value,
                    "path": c.path,
                    "run_command": c.run_command,
                    "port": c.port
                } for c in self.components
            ]
        }


class ProjectAnalyzer:
    """Analyze project structure and determine run configuration"""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        
    def analyze(self) -> ProjectInfo:
        """Analyze project and return run information"""
        detected_files = []
        
        # Scan for common files
        for pattern in ["*.py", "*.js", "*.json", "*.html", "requirements.txt", "package.json"]:
            detected_files.extend([str(f.relative_to(self.project_path)) for f in self.project_path.rglob(pattern)])
        
        # Check if this is a full-stack project (has both backend and frontend)
        has_backend = any("backend/" in f or "backend\\" in f for f in detected_files)
        has_frontend = any("frontend/" in f or "frontend\\" in f for f in detected_files)
        
        if has_backend and has_frontend:
            # This is a full-stack project
            return self._analyze_fullstack(detected_files)
        
        # Detect project type
        project_type = self._detect_project_type(detected_files)
        
        # Get run configuration based on type
        entry_file, run_command, install_command, requirements_file, port = self._get_run_config(
            project_type, detected_files
        )
        
        return ProjectInfo(
            project_type=project_type,
            entry_file=entry_file,
            run_command=run_command,
            install_command=install_command,
            requirements_file=requirements_file,
            detected_files=detected_files,
            port=port
        )
    
    def _analyze_fullstack(self, files: List[str]) -> ProjectInfo:
        """Analyze a full-stack project with both frontend and backend"""
        components = []
        
        # Analyze backend
        backend_files = [f for f in files if "backend/" in f or "backend\\" in f]
        backend_type = self._detect_project_type(backend_files)
        
        # 对于组件，命令在项目根目录执行，所以 base_path 应该用于模块路径
        backend_entry, backend_cmd, backend_install, _, backend_port = self._get_run_config(
            backend_type, backend_files, base_path="backend"
        )
        
        # 修改 backend 命令，确保在项目根目录执行
        # 将 "cd backend; ..." 改为在项目根目录执行
        if backend_cmd and backend_cmd.startswith("cd backend;"):
            backend_cmd = backend_cmd.replace("cd backend; ", "")
        
        components.append(ProjectComponent(
            name="backend",
            project_type=backend_type,
            entry_file=backend_entry,
            run_command=backend_cmd,
            install_command=backend_install,
            port=backend_port,
            path="."  # 在项目根目录执行
        ))
        
        # Analyze frontend
        frontend_files = [f for f in files if "frontend/" in f or "frontend\\" in f]
        frontend_type = self._detect_frontend_type(frontend_files)
        frontend_entry, frontend_cmd, frontend_install, frontend_port = self._get_frontend_config(
            frontend_files, base_path="frontend"
        )
        
        # 对于 HTML_STATIC 类型的 frontend，命令在 frontend 目录执行，不需要 --directory 参数
        if frontend_type == ProjectType.HTML_STATIC and frontend_cmd:
            frontend_cmd = frontend_cmd.replace(" --directory frontend", "")
        
        components.append(ProjectComponent(
            name="frontend",
            project_type=frontend_type,
            entry_file=frontend_entry,
            run_command=frontend_cmd,
            install_command=frontend_install,
            port=frontend_port,
            path="frontend"
        ))
        
        # For full-stack, use backend command as primary but indicate it's full-stack
        # AI should use components to run both separately
        
        return ProjectInfo(
            project_type=backend_type,  # Use backend type as primary
            entry_file=backend_entry,
            run_command=backend_cmd,  # Just backend command
            install_command=backend_install,
            requirements_file="requirements.txt" if any("requirements.txt" in f for f in files) else None,
            detected_files=files,
            port=backend_port,
            is_fullstack=True,
            components=components
        )
    
    def _detect_project_type(self, files: List[str]) -> ProjectType:
        """Detect project type from files - 优先检查明确的配置文件"""
        file_set = set(files)
        
        # 1. 首先检查 Python 项目配置文件（优先级最高）
        if 'pyproject.toml' in file_set or 'setup.py' in file_set or 'setup.cfg' in file_set:
            # 检查具体的 Python 框架
            for f in files:
                if f.endswith('.py'):
                    content = self._read_file_content(f)
                    if content:
                        if 'FastAPI' in content:
                            return ProjectType.FASTAPI
                        if 'Flask' in content:
                            return ProjectType.FLASK
                        if 'Django' in content or 'django' in content:
                            return ProjectType.DJANGO
            # 有 pyproject.toml 但没有特定框架，认为是 Python 脚本项目
            return ProjectType.PYTHON_SCRIPT
        
        # 2. 检查 Django（manage.py 是强特征）
        if any('manage.py' in f for f in files):
            return ProjectType.DJANGO
        
        # 3. 检查根目录的 package.json（真正的 NodeJS 项目）
        root_package_json = 'package.json' in file_set
        if root_package_json:
            content = self._read_file_content('package.json')
            if content:
                if 'react' in content.lower():
                    return ProjectType.REACT
                if 'vue' in content.lower():
                    return ProjectType.VUE
                if 'angular' in content.lower():
                    return ProjectType.ANGULAR
                return ProjectType.NODEJS
        
        # 4. 检查 FastAPI/Flask（通过代码内容）
        for f in files:
            if f.endswith('.py'):
                content = self._read_file_content(f)
                if content:
                    if 'FastAPI' in content:
                        return ProjectType.FASTAPI
                    if 'Flask' in content:
                        return ProjectType.FLASK
        
        # 5. 纯 HTML 项目（没有 Python 和 NodeJS 配置）
        has_html = any(f.endswith('.html') for f in files)
        has_python = any(f.endswith('.py') for f in files)
        
        if has_html and not has_python:
            return ProjectType.HTML_STATIC
        
        # 6. Python 脚本项目
        if has_python:
            return ProjectType.PYTHON_SCRIPT
        
        return ProjectType.UNKNOWN
    
    def _get_run_config(self, project_type: ProjectType, files: List[str], base_path: str = "") -> Tuple[
        Optional[str], str, Optional[str], Optional[str], Optional[int]
    ]:
        """Get run configuration for project type"""
        
        if project_type == ProjectType.FASTAPI:
            # Find main.py or app.py
            entry = self._find_entry_file(files, ['main.py', 'app.py'])
            if entry:
                # Build module path with base_path
                module = entry.replace('.py', '').replace('/', '.').replace('\\', '.')
                if base_path:
                    # For uvicorn, use base_path.module format
                    module = f"{base_path}.{module.replace(base_path + '.', '')}"
                # Use python -m uvicorn for better cross-platform compatibility
                return entry, f"python -m uvicorn {module}:app --reload", "pip install -r requirements.txt", "requirements.txt", 8000
            # Default entry
            module = f"{base_path}.main" if base_path else "main"
            return None, f"python -m uvicorn {module}:app --reload", "pip install -r requirements.txt", "requirements.txt", 8000
        
        elif project_type == ProjectType.FLASK:
            entry = self._find_entry_file(files, ['app.py', 'main.py'])
            if base_path:
                return entry, f"cd {base_path}; flask run", "pip install -r requirements.txt", "requirements.txt", 5000
            return entry, "flask run", "pip install -r requirements.txt", "requirements.txt", 5000
        
        elif project_type == ProjectType.DJANGO:
            if base_path:
                return f"{base_path}/manage.py", f"cd {base_path}; python manage.py runserver", "pip install -r requirements.txt", "requirements.txt", 8000
            return "manage.py", "python manage.py runserver", "pip install -r requirements.txt", "requirements.txt", 8000
        
        elif project_type == ProjectType.REACT:
            if base_path:
                return None, f"cd {base_path}; npm start", "npm install", "package.json", 3000
            return None, "npm start", "npm install", "package.json", 3000
        
        elif project_type == ProjectType.VUE:
            if base_path:
                return None, f"cd {base_path}; npm run serve", "npm install", "package.json", 8080
            return None, "npm run serve", "npm install", "package.json", 8080
        
        elif project_type == ProjectType.NODEJS:
            entry = self._find_entry_file(files, ['index.js', 'app.js', 'server.js'])
            if entry:
                if base_path:
                    return entry, f"cd {base_path}; node {entry}", "npm install", "package.json", None
                return entry, f"node {entry}", "npm install", "package.json", None
            if base_path:
                return None, f"cd {base_path}; node index.js", "npm install", "package.json", None
            return None, "node index.js", "npm install", "package.json", None
        
        elif project_type == ProjectType.HTML_STATIC:
            html_files = [f for f in files if f.endswith('.html')]
            entry = 'index.html' if 'index.html' in html_files else (html_files[0] if html_files else None)
            # For static HTML, use Python's http.server
            if entry:
                # Check if entry is in a subdirectory
                entry_dir = Path(entry).parent
                if entry_dir and str(entry_dir) != '.':
                    return entry, f"python -m http.server 8080 --directory {entry_dir}", None, None, 8080
                return entry, "python -m http.server 8080", None, None, 8080
            return None, "No HTML files found", None, None, None
        
        elif project_type == ProjectType.PYTHON_SCRIPT:
            # 1. 首先检查 pyproject.toml 中的入口点
            if 'pyproject.toml' in files:
                content = self._read_file_content('pyproject.toml')
                if content:
                    # 检查 [project.scripts] 部分
                    import re
                    scripts_match = re.search(r'\[project\.scripts\](.+?)(?=\[|$)', content, re.DOTALL)
                    if scripts_match:
                        # 提取第一个脚本命令
                        script_lines = scripts_match.group(1).strip().split('\n')
                        for line in script_lines:
                            line = line.strip()
                            if line and '=' in line and not line.startswith('#'):
                                # 格式: nanobot = "nanobot.cli.commands:app"
                                match = re.match(r'(\w+)\s*=\s*"(.+?)"', line)
                                if match:
                                    script_name = match.group(1)
                                    module_path = match.group(2)
                                    # 返回 python -m 命令
                                    module = module_path.split(':')[0]
                                    return None, f"python -m {module}", "pip install -e .", "pyproject.toml", None
            
            # 2. 检查是否有 __main__.py（可执行包）
            main_packages = [f for f in files if f.endswith('__main__.py')]
            if main_packages:
                # 提取包名
                main_file = main_packages[0]
                parts = main_file.replace('\\', '/').split('/')
                if len(parts) >= 2:
                    package_name = parts[0]
                    return main_file, f"python -m {package_name}", "pip install -e .", "pyproject.toml", None
            
            # 3. 查找常见的入口文件
            entry = self._find_entry_file(files, ['main.py', 'app.py', 'run.py'])
            if entry:
                return entry, f"python {entry}", None, None, None
            
            # 4. 使用第一个 Python 文件
            py_files = [f for f in files if f.endswith('.py') and not f.startswith('test_') and '/test' not in f and '\\test' not in f]
            if py_files:
                return py_files[0], f"python {py_files[0]}", None, None, None
            
            return None, "No Python files found", None, None, None
        
        return None, "Unknown project type", None, None, None
    
    def _detect_frontend_type(self, files: List[str]) -> ProjectType:
        """Detect frontend project type"""
        file_set = set(files)
        
        # Check for React
        if any('package.json' in f for f in files):
            for f in files:
                if 'package.json' in f:
                    content = self._read_file_content(f)
                    if content:
                        if 'react' in content.lower():
                            return ProjectType.REACT
                        if 'vue' in content.lower():
                            return ProjectType.VUE
        
        # Check for HTML/JS static
        if any(f.endswith('.html') for f in files):
            return ProjectType.HTML_STATIC
        
        return ProjectType.UNKNOWN
    
    def _get_frontend_config(self, files: List[str], base_path: str = "frontend") -> Tuple[
        Optional[str], str, Optional[str], Optional[int]
    ]:
        """Get frontend run configuration"""
        frontend_type = self._detect_frontend_type(files)
        
        if frontend_type == ProjectType.REACT:
            return None, f"cd {base_path}; npm start", f"cd {base_path}; npm install", 3000
        
        elif frontend_type == ProjectType.VUE:
            return None, f"cd {base_path}; npm run serve", f"cd {base_path}; npm install", 8080
        
        elif frontend_type == ProjectType.HTML_STATIC:
            html_files = [f for f in files if f.endswith('.html')]
            entry = None
            for f in html_files:
                if 'index.html' in f:
                    entry = f
                    break
            if not entry and html_files:
                entry = html_files[0]
            
            if entry:
                # Use Python's http.server for static files
                # 指定 --directory 参数确保服务器在正确的目录启动
                return entry, f"python -m http.server 8080 --directory {base_path}", None, 8080
            return None, "No HTML files found", None, None
        
        return None, "python -m http.server 8080", None, 8080
    
    def _find_entry_file(self, files: List[str], candidates: List[str]) -> Optional[str]:
        """Find entry file from candidates"""
        for candidate in candidates:
            for f in files:
                if f.endswith(candidate):
                    return f
        return None
    
    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read file content safely"""
        try:
            full_path = self.project_path / file_path
            if full_path.exists():
                return full_path.read_text(encoding='utf-8')
        except Exception:
            pass
        return None
    
    def generate_run_plan(self) -> str:
        """Generate a human-readable run plan"""
        info = self.analyze()
        
        lines = [f"📊 Project Analysis Results:", ""]
        
        if info.is_fullstack:
            lines.append(f"🎯 Project Type: FULL-STACK ({info.project_type.value.upper()} + Frontend)")
            lines.append(f"Detected Files: {', '.join(info.detected_files[:5])}{'...' if len(info.detected_files) > 5 else ''}")
            lines.append("")
            lines.append("🚀 Run Instructions (Both Frontend and Backend):")
            lines.append("")
            
            for component in info.components:
                lines.append(f"📦 {component.name.upper()} ({component.project_type.value}):")
                if component.install_command:
                    lines.append(f"   Install: {component.install_command}")
                lines.append(f"   Run: {component.run_command}")
                if component.port:
                    lines.append(f"   URL: http://localhost:{component.port}")
                lines.append("")
        else:
            lines.append(f"Project Type: {info.project_type.value.upper()}")
            lines.append(f"Entry File: {info.entry_file or 'N/A'}")
            lines.append(f"Detected Files: {', '.join(info.detected_files[:5])}{'...' if len(info.detected_files) > 5 else ''}")
            lines.append("")
            lines.append("🚀 Run Instructions:")
            
            if info.install_command:
                lines.append(f"1. Install dependencies: {info.install_command}")
            
            lines.append(f"{'2' if info.install_command else '1'}. Run the project: {info.run_command}")
            
            if info.port:
                lines.append(f"3. Open browser: http://localhost:{info.port}")
        
        return "\n".join(lines)


# Global analyzer instance
analyzer = ProjectAnalyzer()
