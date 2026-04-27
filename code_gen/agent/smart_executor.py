"""
Smart Executor - Agent-driven execution
像人类开发者一样直接执行任务，减少 LLM 调用
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import quote

import aiohttp
from aiohttp import ClientError, ClientConnectorError

from code_gen.tools.base import ToolResult
from code_gen.agent.iteration_budget import IterationBudget
from code_gen.ui.cli_ui import (
    print_info, print_success, print_warning, print_error,
    print_tool_call, print_tool_result, Spinner, build_tool_preview
)

console = None  # Remove rich console, use cli_ui instead


class SmartExecutor:
    """
    智能执行器 - 像人类一样直接执行任务
    
    核心思想：
    - 理解用户目标
    - 自己规划步骤
    - 直接执行工具
    - 只在复杂推理时才问 LLM
    - 使用迭代预算管理调用次数
    - 使用记忆系统保持对话上下文
    """
    
    def __init__(self, tool_registry, llm_client, max_iterations: int = 30, work_dir: Optional[str] = None):
        self.tools = tool_registry
        self.llm = llm_client
        self.project_root = ""
        self.max_iterations = max_iterations
        self.budget: Optional[IterationBudget] = None
        self.work_dir = work_dir or "."
        
        # 初始化记忆系统
        self._init_memory()
    
    def _init_memory(self):
        """初始化记忆系统"""
        try:
            # 直接导入 memory 模块，避免通过 agents 包导入（因为 agents 包有循环依赖）
            import sys
            from pathlib import Path
            
            # 手动导入 memory 模块
            memory_path = Path(__file__).parent.parent / "agents" / "memory.py"
            if memory_path.exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("memory", memory_path)
                memory_module = importlib.util.module_from_spec(spec)
                sys.modules["memory"] = memory_module
                spec.loader.exec_module(memory_module)
                
                AgentMemory = memory_module.AgentMemory
                MemoryConfig = memory_module.MemoryConfig
                StorageBackend = memory_module.StorageBackend
                
                config = MemoryConfig(
                    backend=StorageBackend.FILE,
                    storage_path=Path(self.work_dir) / ".code_gen" / "memory",
                    user_id="smart_executor",
                    auto_promote=True,
                    importance_threshold=0.7
                )
                self.memory = AgentMemory(config)
            else:
                self.memory = None
        except Exception as e:
            print_warning(f"记忆系统初始化失败: {e}")
            self.memory = None
        
    async def execute(self, user_input: str, project_root: str) -> str:
        """执行用户请求"""
        self.project_root = project_root
        
        # Initialize iteration budget for this execution
        self.budget = IterationBudget(max_total=self.max_iterations)
        
        # 1. 理解目标
        goal = self._understand_goal(user_input)
        print_info(f"Goal: {goal['type']}")
        
        # 2. 根据目标类型选择执行策略
        if goal["type"] == "run_project":
            return await self._run_project(goal["path"])
        elif goal["type"] == "read_file":
            return await self._read_file(goal["path"])
        elif goal["type"] == "write_file":
            return await self._write_file(goal["path"], goal.get("content", ""))
        elif goal["type"] == "execute_command":
            return await self._execute_command(goal["command"])
        elif goal["type"] == "search":
            return await self._search(goal["query"])
        elif goal["type"] == "web_search":
            return await self._web_search(goal["query"])
        elif goal["type"] == "chat":
            return await self._chat(user_input)
        else:
            # 复杂任务，需要 LLM 帮助规划
            return await self._plan_and_execute(user_input)
    
    def _understand_goal(self, user_input: str) -> Dict:
        """理解用户目标 - 简单的规则匹配"""
        text = user_input.lower()
        
        # 运行项目
        if any(kw in text for kw in ["运行", "启动", "run", "start", "execute"]):
            # 提取路径
            path = self._extract_path(user_input)
            return {"type": "run_project", "path": path or self.project_root}
        
        # 读取文件
        if any(kw in text for kw in ["读取", "查看", "read", "show", "cat", "查看"]):
            path = self._extract_path(user_input)
            if path:
                return {"type": "read_file", "path": path}
        
        # 写入文件
        if any(kw in text for kw in ["写入", "创建", "write", "create", "新建"]):
            path = self._extract_path(user_input)
            if path:
                return {"type": "write_file", "path": path}
        
        # 执行命令
        if any(kw in text for kw in ["执行", "command", "cmd", "shell", "bash"]):
            cmd = self._extract_command(user_input)
            if cmd:
                return {"type": "execute_command", "command": cmd}
        
        # 默认聊天 - 让 LLM 自主决定是否需要搜索
        # 不再通过硬编码关键词判断，而是在 _chat 方法中由 LLM 决定
        return {"type": "chat"}
    
    def _extract_path(self, text: str) -> Optional[str]:
        """从文本中提取路径"""
        # 匹配引号中的路径
        patterns = [
            r'["\']([^"\']+\.(?:py|js|ts|html|css|json|md|txt))["\']',
            r'["\']([A-Za-z]:\\[^"\']+)["\']',
            r'["\'](/[^"\']+)["\']',
            r'【([^】]+)】',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                path = match.group(1)
                # 转换为绝对路径
                if not Path(path).is_absolute():
                    path = str(Path(self.project_root) / path)
                return path
        return None
    
    def _extract_command(self, text: str) -> Optional[str]:
        """从文本中提取命令"""
        # 匹配反引号或引号中的命令
        patterns = [
            r'`([^`]+)`',
            r'"([^"]+(?:pip|npm|python|node|uvicorn)[^"]*)"',
            r"'([^']+(?:pip|npm|python|node|uvicorn)[^']*)'",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None
    
    def _extract_query(self, text: str) -> str:
        """提取搜索查询"""
        # 移除常见关键词
        keywords = ["搜索", "查找", "search", "find", "grep", "for", "查找"]
        query = text
        for kw in keywords:
            query = query.replace(kw, "").strip()
        return query or text
    
    # ============ 具体执行方法 ============
    
    async def _run_project(self, path: str) -> str:
        """运行项目 - 像人类开发者一样"""
        from code_gen.ui.cli_ui import print_header
        print_header(f"🚀 运行项目: {path}")
        
        # 1. 分析项目
        print_info("📋 步骤 1/3: 分析项目结构...")
        spinner = Spinner("正在扫描项目文件...", spinner_type='dots')
        spinner.start()
        analyze_tool = self.tools.get("analyze_project")
        if analyze_tool:
            result = await analyze_tool.execute(path=path)
            spinner.stop("分析完成")
            
            if result.success:
                try:
                    info = json.loads(result.content)
                    
                    # 显示项目信息
                    print_info(f"\n📊 项目分析结果:")
                    print_info(f"   项目类型: {info.get('project_type', 'unknown')}")
                    print_info(f"   入口文件: {info.get('entry_file', 'N/A')}")
                    print_info(f"   运行命令: {info.get('run_command', 'N/A')}")
                    if info.get('is_fullstack'):
                        print_info(f"   项目结构: 全栈项目 ({len(info.get('components', []))} 个组件)")
                    
                    return await self._run_project_from_info(info, path)
                except Exception as e:
                    error_msg = f"❌ 解析项目信息失败: {e}"
                    print_error(error_msg)
                    return error_msg
            else:
                print_error(f"❌ 分析失败: {result.error}")
        else:
            spinner.stop("分析工具不可用")
            print_error("❌ analyze_project 工具未找到")
        
        # 无法分析，使用默认方式
        print_info("⚠️ 使用默认运行方式...")
        return await self._run_default(path)
    
    async def _run_project_from_info(self, info: Dict, path: str) -> str:
        """根据项目信息运行"""
        results = []
        
        # Check budget before starting
        if not self.budget or not self.budget.consume():
            return f"⚠️ 迭代预算已耗尽 ({self.budget.get_summary() if self.budget else 'N/A'})"
        
        # 运行项目
        if info.get("is_fullstack") and info.get("components"):
            # 全栈项目 - 运行多个服务
            print_info(f"\n🚀 步骤 2/3: 启动全栈项目服务 ({len(info['components'])} 个组件)...")
            from pathlib import Path
            base_path = Path(path).resolve()
            
            for i, comp in enumerate(info["components"], 1):
                if not self.budget.consume():
                    results.append(f"⚠️ 预算耗尽，已启动 {len(results)} 个组件")
                    break
                    
                name = comp.get("name", "unknown")
                run_cmd = comp.get("run_command")
                comp_path = comp.get("path", path)
                port = comp.get("port")
                
                # 构建完整路径
                if not Path(comp_path).is_absolute():
                    comp_full_path = str(base_path / comp_path)
                else:
                    comp_full_path = comp_path
                
                if run_cmd:
                    print_info(f"\n   [{i}/{len(info['components'])}] 启动 {name}...")
                    print_info(f"      命令: {run_cmd}")
                    print_info(f"      路径: {comp_full_path}")
                    if port:
                        print_info(f"      端口: {port}")
                    
                    # 使用 _start_service 启动后台服务
                    success = await self._start_service(run_cmd, comp_full_path, name, port or 0)
                    if success:
                        results.append(f"✓ {name}: 已启动")
                        # 等待服务启动
                        await asyncio.sleep(2)
                    else:
                        results.append(f"✗ {name}: 启动失败")
                else:
                    print_warning(f"   [{i}/{len(info['components'])}] {name}: 未找到运行命令")
        else:
            # 单项目
            run_cmd = info.get("run_command")
            port = info.get("port")
            
            if run_cmd:
                print_info(f"\n🚀 步骤 2/3: 启动项目...")
                print_info(f"   命令: {run_cmd}")
                print_info(f"   路径: {path}")
                if port:
                    print_info(f"   端口: {port}")
                
                # 使用 _start_service 启动后台服务
                success = await self._start_service(run_cmd, path, "项目", port or 0)
                if success:
                    results.append("✓ 项目已启动")
                    # 等待服务启动
                    await asyncio.sleep(2)
                else:
                    results.append("✗ 项目启动失败")
            else:
                print_error("\n❌ 未找到项目的运行命令")
                results.append("✗ 未找到运行命令")
                print_info("\n💡 建议:")
                print_info("   1. 检查项目是否有 package.json、pyproject.toml 等配置文件")
                print_info("   2. 查看 README.md 了解如何运行项目")
                print_info("   3. 手动运行项目并告诉我运行命令")
        
        # 步骤 3: 测试服务
        print_info(f"\n🔍 步骤 3/3: 测试服务状态...")
        await self._test_services(info, path)
        
        # 显示使用指南
        print_info(f"\n📖 使用指南")
        self._print_usage_guide(info, path)
        
        return "\n".join(results)
    
    async def _test_services(self, info: Dict, path: str):
        """测试服务是否正常运行 - 带重试机制"""

        async def test_port_with_retry(name: str, port: int, project_type: str = "", max_retries: int = 3, delay: float = 2.0):
            """测试单个端口，带重试"""
            # 根据项目类型选择测试路径
            if project_type == "fastapi":
                test_paths = ["/docs", "/", "/health"]
            elif project_type == "flask":
                test_paths = ["/", "/health"]
            else:
                test_paths = ["/"]

            for test_path in test_paths:
                url = f"http://localhost:{port}{test_path}"

                for attempt in range(max_retries):
                    try:
                        timeout = aiohttp.ClientTimeout(total=3)
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.get(url) as response:
                                if response.status in [200, 307, 308]:
                                    print_success(f"   ✓ {name} (端口 {port}): 运行正常")
                                    return True
                                else:
                                    # 有响应就算成功
                                    print_success(f"   ✓ {name} (端口 {port}): 有响应 (状态码 {response.status})")
                                    return True
                    except (ClientError, ClientConnectorError, asyncio.TimeoutError) as e:
                        if attempt < max_retries - 1:
                            print_info(f"   ⏳ {name} (端口 {port}): 等待服务启动... ({attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                        else:
                            continue  # 尝试下一个路径
                    except Exception as e:
                        print_warning(f"   ⚠ {name} (端口 {port}): 测试失败 - {e}")
                        return False

            print_error(f"   ✗ {name} (端口 {port}): 无法连接")
            return False
        
        # 测试各个组件
        all_success = True
        if info.get("is_fullstack") and info.get("components"):
            for comp in info["components"]:
                name = comp.get("name", "unknown")
                port = comp.get("port")
                project_type = comp.get("project_type", "")
                if port:
                    success = await test_port_with_retry(name, port, project_type)
                    if not success:
                        all_success = False
        else:
            port = info.get("port")
            project_type = info.get("project_type", "")
            if port:
                success = await test_port_with_retry("服务", port, project_type)
                if not success:
                    all_success = False
        
        # 如果测试失败，给出建议
        if not all_success:
            print_info("\n   💡 服务可能仍在启动中，建议:")
            print_info("      1. 等待 5-10 秒后刷新浏览器")
            print_info("      2. 检查独立窗口是否有错误信息")
            print_info("      3. 手动访问 http://localhost:PORT 测试")
    
    def _print_usage_guide(self, info: Dict, path: str):
        """打印项目使用指南"""
        project_type = info.get('project_type', 'unknown')
        port = info.get('port')
        
        print_info(f"\n   项目类型: {project_type}")
        
        if port:
            print_info(f"   访问地址: http://localhost:{port}")
        
        # 根据项目类型给出具体建议
        if project_type == 'fastapi' or project_type == 'flask':
            print_info("\n   常用操作:")
            print_info("   • 查看 API 文档: 访问 /docs (Swagger UI) 或 /redoc")
            print_info("   • 测试接口: 使用 curl 或 Postman")
        elif project_type == 'react' or project_type == 'vue':
            print_info("\n   常用操作:")
            print_info("   • 浏览器会自动打开，或手动访问 localhost:3000")
            print_info("   • 修改代码后页面会自动热更新")
        elif project_type == 'html_static':
            print_info("\n   常用操作:")
            print_info(f"   • 访问: http://localhost:{port or 8080}")
            print_info("   • 按 Ctrl+C 停止服务器")
        elif project_type == 'python_script':
            print_info("\n   常用操作:")
            print_info("   • 这是一个 Python 应用程序")
            print_info("   • 查看日志输出了解运行状态")
            if info.get('entry_file'):
                print_info(f"   • 入口文件: {info.get('entry_file')}")
        
        print_info("\n   停止项目:")
        print_info("   • 按 Ctrl+C 停止")
        print_info("   • 或在另一个终端运行: taskkill /F /IM python.exe (Windows)")
    
    async def _run_default(self, path: str) -> str:
        """默认运行方式"""
        # 尝试常见命令
        commands = [
            "python main.py",
            "python app.py",
            "npm start",
            "npm run dev",
        ]
        for cmd in commands:
            result = await self._run_bash(cmd, cwd=path)
            if "error" not in result.lower():
                return f"Started with: {cmd}\n{result}"
        return "Could not determine how to run this project"
    
    async def _read_file(self, path: str) -> str:
        """读取文件"""
        tool = self.tools.get("read_file")
        if tool:
            result = await tool.execute(path=path)
            return result.content if result.success else result.error
        return "Read tool not available"
    
    async def _write_file(self, path: str, content: str) -> str:
        """写入文件"""
        tool = self.tools.get("write_file")
        if tool:
            result = await tool.execute(file_path=path, content=content)
            return result.content if result.success else result.error
        return "Write tool not available"
    
    async def _execute_command(self, command: str) -> str:
        """执行命令"""
        return await self._run_bash(command)
    
    async def _search(self, query: str) -> str:
        """搜索代码"""
        tool = self.tools.get("search_files")
        if tool:
            result = await tool.execute(query=query)
            return result.content if result.success else result.error
        return "Search tool not available"
    
    async def _chat(self, message: str) -> str:
        """普通聊天 - 带记忆和工具调用"""

        # 1. 保存用户消息到记忆
        if self.memory:
            self.memory.store_short_term(f"用户: {message}", importance=0.6)

        # 2. 构建系统提示，告知 LLM 可用工具
        system_prompt = """你是一个智能助手。你可以使用以下工具来获取信息：

可用工具：
1. web_search - 网络搜索（用于获取实时信息如天气、价格、新闻等）
2. web_fetch - 获取网页内容

当你需要实时信息时，请使用工具。格式：
<tool>web_search</tool>
<query>搜索内容</query>

或者直接回答用户问题。"""

        # 3. 构建消息
        messages = [{"role": "system", "content": system_prompt}]

        # 添加历史记忆
        if self.memory:
            short_term = self.memory.get_short_term(limit=5)
            if short_term:
                history = "\n".join([f"- {mem.content}" for mem in short_term])
                messages.append({
                    "role": "system",
                    "content": f"对话历史:\n{history}"
                })

        messages.append({"role": "user", "content": message})

        # 4. 第一次调用 LLM
        response = await self.llm.send_message(messages=messages)
        print_info(f"LLM first response: {response[:200]}...")

        # 5. 检查是否需要使用工具
        if "<tool>web_search</tool>" in response or "<tool>web_fetch</tool>" in response:
            print_info("Tool call detected, executing...")
            # 提取工具调用
            tool_result = await self._execute_tool_from_response(response)
            print_info(f"Tool result length: {len(tool_result)}")

            # 截断过长的结果
            max_tool_result = 2000
            if len(tool_result) > max_tool_result:
                tool_result = tool_result[:max_tool_result] + "\n... (内容已截断)"
                print_info(f"Truncated tool result to {max_tool_result} chars")

            # 构建新的对话：系统提示 + 用户问题 + 工具结果
            final_messages = [
                {"role": "system", "content": "你是一个智能助手。基于提供的搜索结果回答用户问题。"},
                {"role": "user", "content": f"用户问题: {message}\n\n搜索结果:\n{tool_result}\n\n请基于以上搜索结果回答用户的问题。"}
            ]
            print_info("Calling LLM with tool results...")

            # 再次调用 LLM
            response = await self.llm.send_message(messages=final_messages)
            print_info(f"Final response length: {len(response)}")

        # 6. 保存回复到记忆
        if self.memory:
            self.memory.store_short_term(f"助手: {response}", importance=0.6)

        return response

    async def _execute_tool_from_response(self, response: str) -> str:
        """从 LLM 响应中提取并执行工具调用"""
        import re

        # 提取 web_search 调用
        search_match = re.search(r'<tool>web_search</tool>\s*<query>(.*?)</query>', response, re.DOTALL)
        if search_match:
            query = search_match.group(1).strip()
            print_info(f"LLM requested search: {query}")
            # 只获取原始搜索结果，不调用 LLM 分析
            result = await self._get_search_results(query)
            return result

        # 提取 web_fetch 调用
        fetch_match = re.search(r'<tool>web_fetch</tool>\s*<url>(.*?)</url>', response, re.DOTALL)
        if fetch_match:
            url = fetch_match.group(1).strip()
            print_info(f"LLM requested fetch: {url}")
            fetch_tool = self.tools.get("web_fetch")
            if fetch_tool:
                result = await fetch_tool.execute(url=url)
                return result.content if result.success else result.error
            return "Web fetch tool not available"

        return "No tool executed"

    async def _get_search_results(self, query: str) -> str:
        """获取原始搜索结果（不调用 LLM 分析）"""
        print_info(f"Getting search results for: {query}")

        try:
            # 执行搜索 - 优先使用 Tavily
            search_tool = None
            tavily_tool = self.tools.get("tavily_search")
            if tavily_tool and hasattr(tavily_tool, 'api_key') and tavily_tool.api_key:
                search_tool = tavily_tool
                print_info("Using Tavily search")

            if not search_tool:
                search_tool = self.tools.get("duckduckgo_search")
                if not search_tool:
                    return "Search tool not available"
                print_info("Using DuckDuckGo search")

            print_info("Executing search...")
            result = await search_tool.execute(query=query, max_results=5)
            if not result.success:
                print_error(f"Search failed: {result.error}")
                return f"Search failed: {result.error}"

            search_results = result.content
            print_info(f"Search results length: {len(search_results)}")

            # 尝试获取网页内容
            web_fetch_tool = self.tools.get("web_fetch")
            if web_fetch_tool:
                import re
                urls = re.findall(r'URL:\s*(https?://[^\s\n]+)', search_results)
                webpage_contents = []

                for url in urls[:2]:  # 只取前2个
                    skip_patterns = ['/search?', 'bing.com/search', 'google.com/search',
                                   'duckduckgo.com/html', 'baidu.com/s?wd=']
                    if any(pattern in url for pattern in skip_patterns):
                        continue

                    try:
                        fetch_result = await web_fetch_tool.execute(url=url, max_length=3000)
                        if fetch_result.success and len(fetch_result.content) > 200:
                            webpage_contents.append(f"=== {url} ===\n{fetch_result.content[:2000]}")
                    except Exception:
                        continue

                if webpage_contents:
                    final_result = f"=== Search Results ===\n{search_results}\n\n" + "\n\n".join(webpage_contents)
                    print_info(f"Returning result with webpage content, length: {len(final_result)}")
                    return final_result

            print_info(f"Returning search results only, length: {len(search_results)}")
            return search_results

        except Exception as e:
            print_error(f"Error in _get_search_results: {e}")
            return f"Error: {str(e)}"
    
    async def _web_search(self, query: str) -> str:
        """网络搜索 - 使用 web 工具执行搜索和获取网页内容"""
        print_info("Starting web search...")
        
        try:
            # 1. 执行搜索 - 优先使用 Tavily（如果配置了 API key）
            search_tool = None
            tavily_tool = self.tools.get("tavily_search")
            if tavily_tool:
                # 检查是否配置了 API key
                from code_gen.core.config import Settings
                settings = Settings()
                if settings.tavily_api_key:
                    search_tool = tavily_tool
                    print_info("Using Tavily search (high-quality AI-powered search)...")
            
            # 如果没有 Tavily，使用 DuckDuckGo
            if not search_tool:
                search_tool = self.tools.get("duckduckgo_search")
                if not search_tool:
                    return "Web search tool not available"
                print_info("Using DuckDuckGo search...")
            
            print_info("Searching...")
            result = await search_tool.execute(query=query, max_results=5)
            if not result.success:
                return f"Search failed: {result.error}"
            
            search_results = result.content
            print_info("Search completed, analyzing results...")
            
            # 2. 从搜索结果中提取 URL
            import re
            urls = re.findall(r'URL:\s*(https?://[^\s\n]+)', search_results)
            
            if not urls:
                # 没有 URL，直接基于搜索结果回答
                return await self._analyze_search_results(query, search_results)
            
            # 3. 访问相关网页获取详细内容
            print_info(f"Found {len(urls)} URLs, fetching content...")
            web_fetch_tool = self.tools.get("web_fetch")
            webpage_contents = []
            
            # 根据查询内容，直接访问相关官方网站
            query_lower = query.lower()
            if 'iphone' in query_lower or 'apple' in query_lower or 'ipad' in query_lower or 'mac' in query_lower:
                # 访问苹果中国官网
                apple_url = "https://www.apple.com.cn/iphone/"
                print_info(f"Fetching Apple China website: {apple_url}")
                try:
                    fetch_result = await web_fetch_tool.execute(url=apple_url, max_length=5000)
                    if fetch_result.success and len(fetch_result.content) > 300:
                        print_success(f"Successfully fetched Apple website ({len(fetch_result.content)} chars)")
                        webpage_contents.append(f"=== Apple China iPhone Page ({apple_url}) ===\n{fetch_result.content[:4000]}")
                    else:
                        print_warning(f"Apple website returned empty or short content")
                except Exception as e:
                    print_warning(f"Failed to fetch Apple: {e}")
                
                # 访问京东搜索
                jd_url = f"https://search.jd.com/Search?keyword={quote('iPhone')}&enc=utf-8"
                print_info(f"Fetching JD.com: {jd_url[:60]}...")
                try:
                    fetch_result = await web_fetch_tool.execute(url=jd_url, max_length=5000)
                    if fetch_result.success and len(fetch_result.content) > 300:
                        print_success(f"Successfully fetched JD.com ({len(fetch_result.content)} chars)")
                        webpage_contents.append(f"=== JD.com Search Results ({jd_url}) ===\n{fetch_result.content[:4000]}")
                    else:
                        print_warning(f"JD.com returned empty or short content")
                except Exception as e:
                    print_warning(f"Failed to fetch JD: {e}")
            else:
                # 通用查询：尝试访问搜索结果中的 URL
                for url in urls[:3]:
                    # 跳过纯搜索引擎结果页面
                    skip_patterns = [
                        '/search?', 'bing.com/search', 'google.com/search',
                        'duckduckgo.com/html', 'baidu.com/s?wd=', 'top.baidu.com'
                    ]
                    if any(pattern in url for pattern in skip_patterns):
                        continue
                        
                    print_info(f"Fetching: {url[:60]}...")
                    try:
                        fetch_result = await web_fetch_tool.execute(url=url, max_length=4000)
                        if fetch_result.success and len(fetch_result.content) > 300:
                            webpage_contents.append(f"=== Content from {url} ===\n{fetch_result.content[:3000]}")
                            if len(webpage_contents) >= 2:
                                break
                    except Exception as e:
                        print_warning(f"Failed to fetch {url}: {e}")
            
            # 4. 综合分析所有信息
            print_info("Analyzing information...")
            
            if webpage_contents:
                full_context = f"=== Search Results ===\n{search_results}\n\n" + "\n\n".join(webpage_contents)
            else:
                full_context = search_results
            
            return await self._analyze_search_results(query, full_context)
            
        except Exception as e:
            print_error(f"Web search error: {e}")
            return f"Error during web search: {str(e)}"
    
    async def _analyze_search_results(self, query: str, context: str) -> str:
        """使用 LLM 分析搜索结果并回答"""
        system_prompt = f"""You are a helpful assistant. The user asked: "{query}"

I have gathered web search results and webpage content to answer this question. Please analyze the information below and provide a comprehensive answer.

Important:
1. Provide specific details found in the search results (prices, dates, facts, etc.)
2. If you find pricing information, list it clearly
3. Mention the source websites
4. If information is incomplete, say so but provide what you found
5. Answer in the same language as the user's question

Information:"""

        messages = [
            {"role": "system", "content": system_prompt + "\n\n" + context},
            {"role": "user", "content": f"Based on the information above, please answer: {query}"}
        ]
        
        answer = await self.llm.send_message(messages=messages)
        return answer
    
    def _load_skill(self, skill_name: str) -> str:
        """加载 skill 文件内容"""
        try:
            skill_path = Path(f"d:/LX/code-gen/.code_gen/skills/{skill_name}/SKILL.md")
            if skill_path.exists():
                return skill_path.read_text(encoding='utf-8')
            return f"# Skill {skill_name} not found"
        except Exception as e:
            return f"# Error loading skill: {e}"
    
    async def _run_bash(self, command: str, cwd: Optional[str] = None) -> str:
        """运行 bash 命令"""
        tool = self.tools.get("bash")
        if tool:
            if cwd:
                command = f"cd {cwd} && {command}"
            result = await tool.execute(command=command)
            return result.content if result.success else result.error
        return "Bash tool not available"
    
    async def _start_service(self, command: str, cwd: str, name: str, port: int) -> bool:
        """启动后台服务 - 使用 subprocess 启动后台进程并记录日志"""
        import subprocess
        import os
        from pathlib import Path
        
        try:
            # 确保 cwd 是绝对路径
            cwd_path = Path(cwd).resolve()
            if not cwd_path.exists():
                print_error(f"      ✗ 目录不存在: {cwd_path}")
                return False
            
            # 创建日志目录
            log_dir = Path(".code_gen/logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # 日志文件路径 - 使用绝对路径
            stdout_log = log_dir.resolve() / f"{name}_{port}.log"
            stderr_log = log_dir.resolve() / f"{name}_{port}.err"
            
            # 在 Windows 上，使用 STARTUPINFO 来隐藏窗口
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # 解析命令 - 分割成列表形式，不使用 shell=True
            # 例如: "python -m http.server 8080" -> ["python", "-m", "http.server", "8080"]
            import shlex
            try:
                cmd_parts = shlex.split(command)
            except ValueError:
                # 如果解析失败，使用简单分割
                cmd_parts = command.split()
            
            # 打开日志文件
            with open(stdout_log, 'w') as out, open(stderr_log, 'w') as err:
                # 启动进程 - 不使用 shell=True，cwd 参数才能生效
                process = subprocess.Popen(
                    cmd_parts,
                    cwd=str(cwd_path),
                    stdout=out,
                    stderr=err,
                    shell=False,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                )
            
            print_info(f"      🚀 已启动 {name} (PID: {process.pid})")
            print_info(f"      📝 日志: {stdout_log}")
            return True
            
        except Exception as e:
            print_error(f"      ✗ 启动 {name} 失败: {e}")
            return False
    
    async def _plan_and_execute(self, user_input: str) -> str:
        """复杂任务 - 使用 LLM 规划"""
        # 简单实现：直接问 LLM
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_input}
        ]
        return await self.llm.send_message(messages=messages)
