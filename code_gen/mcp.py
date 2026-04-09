"""
MCP Client for external capabilities
Based on services/mcp/client.ts from TypeScript project
"""
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
import httpx
import logging
import uuid
import time
from collections import defaultdict

logger = logging.getLogger(__name__)


class MCPServerType(str, Enum):
    """MCP server types"""
    SSE = "sse"
    SSE_IDE = "sse-ide"
    WS_IDE = "ws-ide"
    WS = "ws"
    HTTP = "http"
    STDIO = "stdio"
    IN_PROCESS = "in-process"


@dataclass
class MCPConnectionConfig:
    """MCP connection configuration"""
    server_type: MCPServerType
    url: Optional[str] = None
    stdio_command: Optional[str] = None
    headers: dict = None
    timeout: int = 30
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


@dataclass
class MCPTool:
    """MCP tool"""
    name: str
    description: str
    input_schema: dict
    capabilities: list = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
    
    def to_claude_format(self) -> dict:
        """Convert to Claude tool format"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema
        }


@dataclass
class MCPResult:
    """MCP result"""
    success: bool
    content: str
    error: Optional[str] = None
    data: Optional[dict] = None
    _meta: Optional[dict] = None


class JSONRPCRequest:
    """JSON-RPC 2.0 request"""
    
    def __init__(self, method: str, params: dict = None, request_id: str = None):
        self.method = method
        self.params = params or {}
        self.id = request_id or str(uuid.uuid4())
        self.jsonrpc = "2.0"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        result = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "id": self.id
        }
        if self.params:
            result["params"] = self.params
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class JSONRPCResponse:
    """JSON-RPC 2.0 response"""
    
    def __init__(self, result: dict = None, error: dict = None, request_id: str = None):
        self.result = result
        self.error = error
        self.id = request_id
        self.jsonrpc = "2.0"
    
    @classmethod
    def from_dict(cls, data: dict) -> 'JSONRPCResponse':
        """Create from dictionary"""
        return cls(
            result=data.get("result"),
            error=data.get("error"),
            request_id=data.get("id")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'JSONRPCResponse':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def is_error(self) -> bool:
        """Check if response is an error"""
        return self.error is not None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        result = {
            "jsonrpc": self.jsonrpc,
            "id": self.id
        }
        if self.result is not None:
            result["result"] = self.result
        if self.error is not None:
            result["error"] = self.error
        return result


class MCPTransport:
    """MCP transport layer"""
    
    def __init__(self, config: MCPConnectionConfig):
        self.config = config
        self.connected = False
        self._message_handlers: List[Callable] = []
        self._pending_requests: Dict[str, asyncio.Future] = {}
    
    async def connect(self) -> bool:
        """Connect to transport"""
        raise NotImplementedError
    
    async def disconnect(self):
        """Disconnect from transport"""
        self.connected = False
    
    async def send(self, message: dict):
        """Send a message"""
        raise NotImplementedError
    
    async def receive(self) -> dict:
        """Receive a message"""
        raise NotImplementedError
    
    def on_message(self, handler: Callable):
        """Register message handler"""
        self._message_handlers.append(handler)
    
    async def _handle_message(self, message: dict):
        """Handle incoming message"""
        for handler in self._message_handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Error handling message: {e}")


class HTTPTransport(MCPTransport):
    """HTTP-based MCP transport"""
    
    def __init__(self, config: MCPConnectionConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        self._request_id = 0
    
    async def connect(self) -> bool:
        """Connect via HTTP"""
        try:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Code-Gen-Python/1.0.0"
            }
            headers.update(self.config.headers)
            
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=self.config.timeout
            )
            self.connected = True
            logger.info(f"HTTP transport connected to {self.config.url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect via HTTP: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from HTTP"""
        if self._client:
            await self._client.aclose()
        await super().disconnect()
    
    async def send(self, message: dict):
        """Send a message via HTTP POST"""
        if not self._client:
            raise RuntimeError("Not connected")
        
        self._request_id += 1
        message["id"] = self._request_id
        
        try:
            response = await self._client.post(
                self.config.url,
                json=message
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise
    
    async def receive(self) -> dict:
        """HTTP doesn't support receiving messages"""
        raise NotImplementedError("HTTP transport doesn't support receiving messages")


class MCPClient:
    """MCP client for external capabilities"""
    
    def __init__(self, config: MCPConnectionConfig):
        self.config = config
        self.connected = False
        self.tools: list[MCPTool] = []
        self.transport: Optional[MCPTransport] = None
        self._message_handlers: list[Callable] = []
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._request_callbacks: Dict[str, Callable] = {}
        self._tool_cache: Dict[str, MCPTool] = {}
        self._last_request_time: float = 0
        self._request_timeout: float = 30.0
        self._max_retries: int = 3
        self._retry_delay: float = 1.0
    
    async def connect(self) -> bool:
        """Connect to MCP server"""
        try:
            if self.config.server_type == MCPServerType.STDIO:
                if not await self._connect_stdio():
                    return False
            elif self.config.server_type in [MCPServerType.SSE, MCPServerType.WS]:
                if not await self._connect_streaming():
                    return False
            elif self.config.server_type == MCPServerType.HTTP:
                if not await self._connect_http():
                    return False
            else:
                if not await self._connect_in_process():
                    return False
            
            self.connected = True
            self._last_request_time = time.time()
            
            # List tools after connection
            await self._discover_tools()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False
    
    async def _connect_stdio(self) -> bool:
        """Connect via stdio"""
        try:
            logger.info(f"Starting MCP server: {self.config.stdio_command}")
            
            import subprocess
            import sys
            
            if self.config.stdio_command:
                process = await asyncio.create_subprocess_exec(
                    *self.config.stdio_command.split(),
                    stdout=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.PIPE
                )
                
                async def stdio_receive():
                    while process.stdout and not process.stdout.at_eof():
                        line = await process.stdout.readline()
                        if line:
                            message = json.loads(line.decode())
                            await self._handle_message(message)
                
                async def stdio_send(message: dict):
                    if process.stdin:
                        json_line = json.dumps(message) + "\n"
                        process.stdin.write(json_line.encode())
                        await process.stdin.drain()
                
                self.transport = MCPTransport(self.config)
                self.transport.send = stdio_send
                self.transport.receive = stdio_receive
            else:
                self.transport = MCPTransport(self.config)
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect via stdio: {e}")
            return False
    
    async def _connect_streaming(self) -> bool:
        """Connect via SSE/WebSocket"""
        try:
            if self.config.server_type == MCPServerType.SSE:
                return await self._connect_sse()
            elif self.config.server_type == MCPServerType.WS:
                return await self._connect_websocket()
            return True
        except Exception as e:
            logger.error(f"Failed to connect via streaming: {e}")
            return False
    
    async def _connect_sse(self) -> bool:
        """Connect via SSE"""
        try:
            logger.info(f"Connecting to SSE server: {self.config.url}")
            
            import sse_starlette
            from starlette.applications import Starlette
            from starlette.routing import Route
            
            self.transport = HTTPTransport(self.config)
            return await self.transport.connect()
        except Exception as e:
            logger.error(f"Failed to connect via SSE: {e}")
            return False
    
    async def _connect_websocket(self) -> bool:
        """Connect via WebSocket"""
        try:
            logger.info(f"Connecting to WebSocket server: {self.config.url}")
            
            import websockets
            
            async def ws_send(message: dict):
                if self.transport and hasattr(self.transport, '_ws'):
                    await self.transport._ws.send(json.dumps(message))
            
            async def ws_receive():
                if self.transport and hasattr(self.transport, '_ws'):
                    message = await self.transport._ws.recv()
                    return json.loads(message)
                raise RuntimeError("Not connected")
            
            self.transport = MCPTransport(self.config)
            self.transport.send = ws_send
            self.transport.receive = ws_receive
            
            self.transport._ws = await websockets.connect(self.config.url)
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect via WebSocket: {e}")
            return False
    
    async def _connect_http(self) -> bool:
        """Connect via HTTP"""
        try:
            logger.info(f"Connecting to HTTP server: {self.config.url}")
            
            self.transport = HTTPTransport(self.config)
            return await self.transport.connect()
        except Exception as e:
            logger.error(f"Failed to connect via HTTP: {e}")
            return False
    
    async def _connect_in_process(self) -> bool:
        """Connect in-process"""
        try:
            logger.info("Connecting to in-process server")
            
            self.transport = MCPTransport(self.config)
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect in-process: {e}")
            return False
    
    async def _discover_tools(self):
        """Discover tools from MCP server"""
        try:
            request = JSONRPCRequest(
                method="tools/list",
                request_id=str(uuid.uuid4())
            )
            
            if self.transport:
                response = await self.transport.send(request.to_dict())
                
                if response and "result" in response:
                    tools_data = response["result"].get("tools", [])
                    self.tools = [
                        MCPTool(
                            name=tool.get("name", ""),
                            description=tool.get("description", ""),
                            input_schema=tool.get("inputSchema", {})
                        )
                        for tool in tools_data
                    ]
                    
                    for tool in self.tools:
                        self._tool_cache[tool.name] = tool
                    
                    logger.info(f"Discovered {len(self.tools)} tools")
            else:
                self.tools = [
                    MCPTool(
                        name="mcp__file_read",
                        description="Read a file from the filesystem",
                        input_schema={
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "File path"}
                            },
                            "required": ["path"]
                        }
                    ),
                    MCPTool(
                        name="mcp__file_write",
                        description="Write content to a file",
                        input_schema={
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "File path"},
                                "content": {"type": "string", "description": "File content"}
                            },
                            "required": ["path", "content"]
                        }
                    ),
                    MCPTool(
                        name="mcp__execute_command",
                        description="Execute a shell command",
                        input_schema={
                            "type": "object",
                            "properties": {
                                "command": {"type": "string", "description": "Command to execute"}
                            },
                            "required": ["command"]
                        }
                    )
                ]
                
                for tool in self.tools:
                    self._tool_cache[tool.name] = tool
                
                logger.info(f"Loaded {len(self.tools)} default tools")
        except Exception as e:
            logger.error(f"Failed to discover tools: {e}")
    
    async def disconnect(self):
        """Disconnect from MCP server"""
        self.connected = False
        if self.transport:
            await self.transport.disconnect()
    
    async def list_tools(self) -> list[MCPTool]:
        """List available tools"""
        if not self.connected:
            if not await self.connect():
                return []
        
        if not self.tools:
            await self._discover_tools()
        
        return self.tools
    
    async def _send_request(self, method: str, params: dict = None) -> dict:
        """Send a JSON-RPC request"""
        if not self.connected:
            if not await self.connect():
                raise RuntimeError("Failed to connect to MCP server")
        
        if not self.transport:
            raise RuntimeError("No transport available")
        
        request = JSONRPCRequest(method=method, params=params)
        
        for attempt in range(self._max_retries):
            try:
                response_data = await self.transport.send(request.to_dict())
                response = JSONRPCResponse.from_dict(response_data)
                
                if response.is_error():
                    error = response.error
                    raise RuntimeError(f"MCP error: {error.get('message', 'Unknown error')}")
                
                return response.result
                
            except Exception as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
                    if not self.connected:
                        await self.connect()
        
        raise RuntimeError(f"Failed to send request after {self._max_retries} attempts")
    
    async def call_tool(self, tool_name: str, params: dict) -> MCPResult:
        """Call an MCP tool"""
        if not self.connected:
            if not await self.connect():
                return MCPResult(False, "", "Failed to connect to MCP server")
        
        if not self.transport:
            return MCPResult(False, "", "No transport available")
        
        try:
            request = JSONRPCRequest(
                method="tools/call",
                params={
                    "name": tool_name,
                    "arguments": params
                },
                request_id=str(uuid.uuid4())
            )
            
            for attempt in range(self._max_retries):
                try:
                    response_data = await self.transport.send(request.to_dict())
                    response = JSONRPCResponse.from_dict(response_data)
                    
                    if response.is_error():
                        error = response.error
                        return MCPResult(
                            success=False,
                            content="",
                            error=error.get("message", "Unknown error"),
                            _meta=error
                        )
                    
                    result = response.result
                    content = result.get("content", "")
                    
                    return MCPResult(
                        success=True,
                        content=content,
                        _meta=result.get("_meta")
                    )
                    
                except Exception as e:
                    logger.warning(f"Tool call attempt {attempt + 1} failed: {e}")
                    
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(self._retry_delay * (attempt + 1))
                        if not self.connected:
                            await self.connect()
            
            return MCPResult(
                success=False,
                content="",
                error=f"Failed to call tool after {self._max_retries} attempts"
            )
            
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            return MCPResult(False, "", str(e))
    
    def on_message(self, handler: Callable):
        """Register message handler"""
        self._message_handlers.append(handler)
    
    async def send_message(self, message: dict):
        """Send a message to MCP server"""
        if not self.connected:
            raise RuntimeError("Not connected to MCP server")
        
        if not self.transport:
            raise RuntimeError("No transport available")
        
        await self.transport.send(message)
    
    async def ensure_connected(self) -> bool:
        """Ensure connection is active, reconnect if needed"""
        if not self.connected:
            return await self.connect()
        
        if self.transport and hasattr(self.transport, '_last_activity'):
            elapsed = time.time() - self.transport._last_activity
            if elapsed > self._request_timeout:
                logger.info("Connection timeout, reconnecting...")
                await self.disconnect()
                return await self.connect()
        
        return True


class MCPClientManager:
    """Manager for MCP clients"""
    
    def __init__(self):
        self.clients: dict[str, MCPClient] = {}
        self.tool_cache: dict[str, list[MCPTool]] = {}
        self._connection_cache: dict[str, tuple[MCPConnectionConfig, float]] = {}
        self._cache_ttl: float = 300.0
    
    async def connect_to_server(self, server_name: str, config: MCPConnectionConfig) -> Optional[MCPClient]:
        """Connect to MCP server"""
        if server_name in self.clients:
            client = self.clients[server_name]
            if await client.ensure_connected():
                return client
        
        client = MCPClient(config)
        if await client.connect():
            self.clients[server_name] = client
            
            # Cache tools
            tools = await client.list_tools()
            self.tool_cache[server_name] = tools
            
            # Cache connection config
            self._connection_cache[server_name] = (config, time.time())
            
            logger.info(f"Connected to MCP server: {server_name}, tools: {len(tools)}")
            return client
        
        logger.error(f"Failed to connect to MCP server: {server_name}")
        return None
    
    async def get_client(self, server_name: str) -> Optional[MCPClient]:
        """Get MCP client by server name"""
        client = self.clients.get(server_name)
        if client and await client.ensure_connected():
            return client
        return None
    
    async def get_tools(self, server_name: str) -> list[MCPTool]:
        """Get tools for a server"""
        if server_name in self.tool_cache:
            return self.tool_cache[server_name]
        
        client = self.clients.get(server_name)
        if client:
            tools = await client.list_tools()
            self.tool_cache[server_name] = tools
            return tools
        
        return []
    
    async def call_tool(self, server_name: str, tool_name: str, params: dict) -> MCPResult:
        """Call a tool on a server"""
        client = self.clients.get(server_name)
        if not client:
            return MCPResult(False, "", f"Client not found: {server_name}")
        
        return await client.call_tool(tool_name, params)
    
    async def disconnect_all(self):
        """Disconnect all clients"""
        for client in self.clients.values():
            await client.disconnect()
        self.clients.clear()
        self.tool_cache.clear()
        self._connection_cache.clear()
    
    def get_all_tools(self) -> list[MCPTool]:
        """Get all tools from all connected servers"""
        all_tools = []
        for tools in self.tool_cache.values():
            all_tools.extend(tools)
        return all_tools
    
    async def refresh_connection(self, server_name: str) -> bool:
        """Refresh connection if cache is stale"""
        if server_name not in self._connection_cache:
            return False
        
        config, timestamp = self._connection_cache[server_name]
        elapsed = time.time() - timestamp
        
        if elapsed > self._cache_ttl:
            if server_name in self.clients:
                await self.clients[server_name].disconnect()
                del self.clients[server_name]
            if server_name in self.tool_cache:
                del self.tool_cache[server_name]
            return True
        
        return False


# Global MCP client manager
mcp_manager = MCPClientManager()
