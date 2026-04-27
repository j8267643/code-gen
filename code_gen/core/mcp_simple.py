"""
简单的 MCP 客户端 - 用于测试 MCP 服务器连接
"""
import asyncio
import json
import subprocess
import sys
from typing import Dict, Any, Optional


class SimpleMCPClient:
    """简单的 MCP 客户端"""

    def __init__(self, command: str):
        self.command = command
        self.process: Optional[asyncio.subprocess.Process] = None
        self.request_id = 0

    async def connect(self) -> bool:
        """连接到 MCP 服务器"""
        try:
            self.process = await asyncio.create_subprocess_exec(
                *self.command.split(),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            print(f"Started MCP server with PID: {self.process.pid}", file=sys.stderr)

            # 初始化
            init_response = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "clientInfo": {
                    "name": "code-gen",
                    "version": "1.0.0"
                }
            })

            print(f"Initialized: {init_response}", file=sys.stderr)
            return True
        except Exception as e:
            print(f"Failed to connect: {e}", file=sys.stderr)
            return False

    async def list_tools(self) -> list:
        """列出可用工具"""
        response = await self._send_request("tools/list", {})
        if response and "result" in response:
            return response["result"].get("tools", [])
        return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """调用工具"""
        response = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })

        if response and "result" in response:
            content = response["result"].get("content", [])
            if content:
                return content[0].get("text", "")
        return ""

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict]:
        """发送请求"""
        if not self.process:
            return None

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": str(self.request_id),
            "method": method,
            "params": params
        }

        try:
            # 发送请求
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()

            # 读取响应
            line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=30
            )

            if line:
                response = json.loads(line.decode())
                return response
        except asyncio.TimeoutError:
            print(f"Timeout waiting for response to {method}", file=sys.stderr)
        except Exception as e:
            print(f"Error sending request: {e}", file=sys.stderr)

        return None

    async def disconnect(self):
        """断开连接"""
        if self.process:
            self.process.terminate()
            await self.process.wait()


async def test_simple_mcp():
    """测试简单的 MCP 客户端"""
    print("=" * 70)
    print("Simple MCP Client Test")
    print("=" * 70)

    # 创建客户端
    client = SimpleMCPClient("python mcp_server_example.py")

    # 连接
    print("\n1. Connecting to MCP server...")
    if await client.connect():
        print("Connected!")
    else:
        print("Failed to connect")
        return

    # 列出工具
    print("\n2. Listing tools...")
    tools = await client.list_tools()
    print(f"Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")

    # 调用工具
    print("\n3. Calling tools...")

    print("\n  get_current_time:")
    result = await client.call_tool("get_current_time", {})
    print(f"  {result}")

    print("\n  calculate (1 + 2 * 3):")
    result = await client.call_tool("calculate", {"expression": "1 + 2 * 3"})
    print(f"  {result}")

    print("\n  echo ('Hello!'):")
    result = await client.call_tool("echo", {"message": "Hello!"})
    print(f"  {result}")

    # 断开
    print("\n4. Disconnecting...")
    await client.disconnect()
    print("Disconnected")

    print("\n" + "=" * 70)
    print("Test completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_simple_mcp())
