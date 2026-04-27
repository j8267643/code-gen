"""
Browser Automation Tool - 浏览器自动化工具

基于 Playwright 实现，支持网页导航、元素操作、截图等功能
"""
import asyncio
import base64
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from code_gen.tools.base import Tool, ToolResult


class BrowserManager:
    """浏览器管理器 - 管理 Playwright 实例"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.console_messages: List[Dict[str, Any]] = []
        self.network_requests: List[Dict[str, Any]] = []
        self._initialized = False
    
    async def initialize(self, headless: bool = False):
        """初始化浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not installed. Run: pip install playwright && playwright install")
        
        if self._initialized:
            return
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        self.page = await self.context.new_page()
        
        # 设置事件监听
        self.page.on("console", self._on_console)
        self.page.on("request", self._on_request)
        self.page.on("response", self._on_response)
        
        self._initialized = True
    
    def _on_console(self, msg):
        """监听控制台消息"""
        self.console_messages.append({
            "type": msg.type,
            "text": msg.text,
            "timestamp": datetime.now().isoformat()
        })
    
    def _on_request(self, request):
        """监听网络请求"""
        self.network_requests.append({
            "type": "request",
            "url": request.url,
            "method": request.method,
            "timestamp": datetime.now().isoformat()
        })
    
    def _on_response(self, response):
        """监听网络响应"""
        self.network_requests.append({
            "type": "response",
            "url": response.url,
            "status": response.status,
            "timestamp": datetime.now().isoformat()
        })
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self._initialized = False
    
    def is_initialized(self) -> bool:
        return self._initialized


# 全局浏览器管理器实例
_browser_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    """获取浏览器管理器实例"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager


class BrowserNavigateTool(Tool):
    """浏览器导航工具"""
    
    name = "browser_navigate"
    description = "Navigate to a URL in the browser"
    
    input_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to navigate to",
            },
            "headless": {
                "type": "boolean",
                "description": "Run browser in headless mode (default: false)",
                "default": False,
            },
        },
        "required": ["url"],
    }
    
    async def execute(self, url: str, headless: bool = False) -> ToolResult:
        try:
            manager = get_browser_manager()
            
            if not manager.is_initialized():
                await manager.initialize(headless=headless)
            
            response = await manager.page.goto(url, wait_until="networkidle")
            
            title = await manager.page.title()
            
            return ToolResult(
                success=True,
                content=f"✅ Navigated to: {url}\n📄 Title: {title}\n📊 Status: {response.status if response else 'N/A'}",
                data={"url": url, "title": title, "status": response.status if response else None}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Navigation failed: {str(e)}"
            )


class BrowserClickTool(Tool):
    """浏览器点击工具"""
    
    name = "browser_click"
    description = "Click on an element in the browser"
    
    input_schema = {
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "CSS selector or XPath of the element to click",
            },
            "wait_for_navigation": {
                "type": "boolean",
                "description": "Wait for navigation after click (default: false)",
                "default": False,
            },
        },
        "required": ["selector"],
    }
    
    async def execute(self, selector: str, wait_for_navigation: bool = False) -> ToolResult:
        try:
            manager = get_browser_manager()
            
            if not manager.is_initialized():
                return ToolResult(
                    success=False,
                    content="",
                    error="Browser not initialized. Use browser_navigate first."
                )
            
            if wait_for_navigation:
                async with manager.page.expect_navigation():
                    await manager.page.click(selector)
            else:
                await manager.page.click(selector)
            
            return ToolResult(
                success=True,
                content=f"✅ Clicked element: {selector}",
                data={"selector": selector}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Click failed: {str(e)}"
            )


class BrowserTypeTool(Tool):
    """浏览器输入工具"""
    
    name = "browser_type"
    description = "Type text into an input field"
    
    input_schema = {
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "CSS selector of the input field",
            },
            "text": {
                "type": "string",
                "description": "Text to type",
            },
            "submit": {
                "type": "boolean",
                "description": "Press Enter after typing (default: false)",
                "default": False,
            },
        },
        "required": ["selector", "text"],
    }
    
    async def execute(self, selector: str, text: str, submit: bool = False) -> ToolResult:
        try:
            manager = get_browser_manager()
            
            if not manager.is_initialized():
                return ToolResult(
                    success=False,
                    content="",
                    error="Browser not initialized. Use browser_navigate first."
                )
            
            await manager.page.fill(selector, text)
            
            if submit:
                await manager.page.press(selector, "Enter")
            
            return ToolResult(
                success=True,
                content=f"✅ Typed '{text}' into {selector}",
                data={"selector": selector, "text": text, "submitted": submit}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Type failed: {str(e)}"
            )


class BrowserScreenshotTool(Tool):
    """浏览器截图工具"""
    
    name = "browser_take_screenshot"
    description = "Take a screenshot of the current page"
    
    input_schema = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Filename for the screenshot (default: auto-generated)",
            },
            "full_page": {
                "type": "boolean",
                "description": "Capture full page or just viewport (default: false)",
                "default": False,
            },
            "selector": {
                "type": "string",
                "description": "CSS selector of specific element to screenshot (optional)",
            },
        },
        "required": [],
    }
    
    async def execute(
        self,
        filename: Optional[str] = None,
        full_page: bool = False,
        selector: Optional[str] = None
    ) -> ToolResult:
        try:
            manager = get_browser_manager()
            
            if not manager.is_initialized():
                return ToolResult(
                    success=False,
                    content="",
                    error="Browser not initialized. Use browser_navigate first."
                )
            
            # 生成文件名
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            # 确保目录存在
            screenshot_dir = Path("screenshots")
            screenshot_dir.mkdir(exist_ok=True)
            filepath = screenshot_dir / filename
            
            # 截图
            if selector:
                element = await manager.page.query_selector(selector)
                if element:
                    await element.screenshot(path=str(filepath))
                else:
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"Element not found: {selector}"
                    )
            else:
                await manager.page.screenshot(path=str(filepath), full_page=full_page)
            
            return ToolResult(
                success=True,
                content=f"✅ Screenshot saved: {filepath}",
                data={"filepath": str(filepath), "filename": filename}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Screenshot failed: {str(e)}"
            )


class BrowserSnapshotTool(Tool):
    """浏览器页面快照工具"""
    
    name = "browser_snapshot"
    description = "Get a text snapshot of the current page content"
    
    input_schema = {
        "type": "object",
        "properties": {
            "include_html": {
                "type": "boolean",
                "description": "Include HTML structure (default: false, returns text only)",
                "default": False,
            },
        },
        "required": [],
    }
    
    async def execute(self, include_html: bool = False) -> ToolResult:
        try:
            manager = get_browser_manager()
            
            if not manager.is_initialized():
                return ToolResult(
                    success=False,
                    content="",
                    error="Browser not initialized. Use browser_navigate first."
                )
            
            if include_html:
                content = await manager.page.content()
            else:
                # 获取可见文本内容
                content = await manager.page.evaluate("""() => {
                    return document.body.innerText;
                }""")
            
            # 截断过长的内容
            if len(content) > 5000:
                content = content[:5000] + "\n... (content truncated)"
            
            title = await manager.page.title()
            url = manager.page.url
            
            return ToolResult(
                success=True,
                content=f"📄 Page: {title}\n🔗 URL: {url}\n\n{content}",
                data={"title": title, "url": url, "content_length": len(content)}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Snapshot failed: {str(e)}"
            )


class BrowserConsoleMessagesTool(Tool):
    """浏览器控制台消息工具"""
    
    name = "browser_console_messages"
    description = "Get browser console messages"
    
    input_schema = {
        "type": "object",
        "properties": {
            "clear": {
                "type": "boolean",
                "description": "Clear messages after retrieval (default: false)",
                "default": False,
            },
        },
        "required": [],
    }
    
    async def execute(self, clear: bool = False) -> ToolResult:
        try:
            manager = get_browser_manager()
            
            if not manager.is_initialized():
                return ToolResult(
                    success=False,
                    content="",
                    error="Browser not initialized. Use browser_navigate first."
                )
            
            messages = manager.console_messages.copy()
            
            if clear:
                manager.console_messages.clear()
            
            if not messages:
                return ToolResult(
                    success=True,
                    content="No console messages",
                    data={"messages": []}
                )
            
            # 格式化消息
            result = "📋 Console Messages:\n\n"
            for msg in messages[-20:]:  # 只显示最近20条
                emoji = {"log": "📝", "error": "❌", "warn": "⚠️", "info": "ℹ️"}.get(msg["type"], "📝")
                result += f"{emoji} [{msg['type']}] {msg['text'][:200]}\n"
            
            return ToolResult(
                success=True,
                content=result,
                data={"messages": messages, "count": len(messages)}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Failed to get console messages: {str(e)}"
            )


class BrowserCloseTool(Tool):
    """关闭浏览器工具"""
    
    name = "browser_close"
    description = "Close the browser"
    
    input_schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    
    async def execute(self) -> ToolResult:
        try:
            manager = get_browser_manager()
            
            if not manager.is_initialized():
                return ToolResult(
                    success=True,
                    content="Browser was not running",
                    data={}
                )
            
            await manager.close()
            
            return ToolResult(
                success=True,
                content="✅ Browser closed",
                data={}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Failed to close browser: {str(e)}"
            )


def get_browser_tools() -> List[Tool]:
    """获取所有浏览器工具"""
    return [
        BrowserNavigateTool(),
        BrowserClickTool(),
        BrowserTypeTool(),
        BrowserScreenshotTool(),
        BrowserSnapshotTool(),
        BrowserConsoleMessagesTool(),
        BrowserCloseTool(),
    ]
