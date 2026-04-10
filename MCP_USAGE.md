# MCP 使用指南

## 什么是 MCP

MCP (Model Context Protocol) 是一个协议，允许 AI 助手连接外部工具和服务，扩展其能力。

Code Gen 内置了 MCP 支持，你只需在配置文件中添加服务器，无需编写代码即可使用外部工具。

## 快速开始

### 1. 配置 MCP 服务器

编辑 `.code_gen/config.yaml` 文件，在 `mcp.servers` 部分添加服务器：

```yaml
mcp:
  servers:
    # 内置工具服务器（已默认启用）
    - name: code-gen-tools
      type: stdio
      command: python .code_gen/mcp_tools.py
```

### 2. 启动 Code Gen

```bash
python -m code_gen chat
```

启动时会自动连接配置的所有 MCP 服务器：
```
Connected to MCP server: code-gen-tools (3 tools)
Connected to MCP server: windows (18 tools)
Connected to 2 MCP server(s)
```

### 3. 使用 MCP 工具

连接成功后，AI 会自动使用可用的 MCP 工具。例如：

```
[You]: 现在几点了？
[AI]: 当前时间是 2026-04-10 09:30:15

[You]: 计算 123 * 456
[AI]: 123 * 456 = 56088

[You]: 打开记事本
[AI]: 已启动记事本应用程序
```

## 添加更多 MCP 服务器

### 常用服务器配置

#### Windows-MCP (Windows 系统控制)
```yaml
mcp:
  servers:
    - name: windows
      type: stdio
      command: uv
      args:
        - --directory
        - D:\LX\Windows-MCP
        - run
        - windows-mcp
```

#### 文件系统服务器
```yaml
mcp:
  servers:
    - name: filesystem
      type: stdio
      command: npx
      args:
        - -y
        - @modelcontextprotocol/server-filesystem
        - D:\LX\code-gen
```

#### GitHub 服务器
```yaml
mcp:
  servers:
    - name: github
      type: stdio
      command: npx
      args:
        - -y
        - @modelcontextprotocol/server-github
      env:
        GITHUB_PERSONAL_ACCESS_TOKEN: your-token-here
```

#### PostgreSQL 服务器
```yaml
mcp:
  servers:
    - name: postgres
      type: stdio
      command: npx
      args:
        - -y
        - @modelcontextprotocol/server-postgres
        - postgresql://localhost/mydb
```

#### SQLite 服务器
```yaml
mcp:
  servers:
    - name: sqlite
      type: stdio
      command: npx
      args:
        - -y
        - @modelcontextprotocol/server-sqlite
        - /path/to/database.db
```

#### 自定义 HTTP 服务器
```yaml
mcp:
  servers:
    - name: my-api
      type: http
      url: http://localhost:3000/mcp
```

## 服务器类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| `stdio` | 通过标准输入/输出通信 | 本地工具、Python/Node.js 脚本 |
| `http` | HTTP 请求/响应 | REST API 服务 |
| `sse` | Server-Sent Events | 流式数据服务 |
| `ws` | WebSocket | 双向实时通信 |

## 内置工具服务器

`.code_gen/mcp_tools.py` 提供以下工具：

| 工具名 | 功能 | 示例 |
|--------|------|------|
| `get_current_time` | 获取当前时间 | 现在几点？ |
| `calculate` | 数学计算 | 计算 1+2*3 |
| `get_system_info` | 系统信息 | 查看系统信息 |

## 查看已连接的服务器

启动时会在控制台显示：
```
Connected to MCP server: code-gen-tools (3 tools)
Connected to MCP server: windows (18 tools)
Connected to 2 MCP server(s)
```

## 开发者指南

### 使用 MCP 客户端编程

#### 简单客户端示例
```python
from code_gen.mcp_simple import SimpleMCPClient
import asyncio

async def main():
    # 创建客户端
    client = SimpleMCPClient("python tests/mcp_server_example.py")

    # 连接
    await client.connect()

    # 列出工具
    tools = await client.list_tools()
    print(f"可用工具: {len(tools)}")

    # 调用工具
    result = await client.call_tool("calculate", {"expression": "1 + 2 * 3"})
    print(f"结果: {result}")

    # 断开连接
    await client.disconnect()

asyncio.run(main())
```

#### 高级客户端示例
```python
from code_gen.mcp import mcp_manager, MCPConnectionConfig, MCPServerType
import asyncio

async def main():
    # 配置
    config = MCPConnectionConfig(
        server_type=MCPServerType.STDIO,
        stdio_command="python tests/mcp_server_example.py"
    )

    # 连接
    await mcp_manager.connect_to_server("my_server", config)

    # 获取工具
    tools = mcp_manager.get_all_tools()
    print(f"可用工具: {len(tools)}")

    # 调用工具
    result = await mcp_manager.call_tool("my_server", "calculate", {"expression": "1 + 2 * 3"})
    print(f"结果: {result.content}")

asyncio.run(main())
```

### 创建自定义 MCP 服务器

你可以创建自己的 MCP 服务器来提供特定功能：

```python
#!/usr/bin/env python3
"""
自定义 MCP 服务器示例
"""
import asyncio
import json
import sys

class MyMCPServer:
    def __init__(self):
        self.tools = {
            "my_tool": {
                "description": "我的自定义工具",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "param": {"type": "string"}
                    },
                    "required": ["param"]
                }
            }
        }

    async def handle_request(self, request):
        method = request.get("method")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "my-server", "version": "1.0.0"},
                    "capabilities": {"tools": {}}
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "tools": [
                        {"name": name, "description": info["description"],
                         "inputSchema": info["input_schema"]}
                        for name, info in self.tools.items()
                    ]
                }
            }

        elif method == "tools/call":
            tool_name = request["params"]["name"]
            args = request["params"]["arguments"]

            # 执行工具逻辑
            result = f"执行了 {tool_name}，参数: {args}"

            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [{"type": "text", "text": result}]
                }
            }

    async def run(self):
        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break

            request = json.loads(line.strip())
            response = await self.handle_request(request)
            print(json.dumps(response), flush=True)

if __name__ == "__main__":
    server = MyMCPServer()
    asyncio.run(server.run())
```

保存为 `my_server.py`，然后在 `config.yaml` 中配置即可使用。

## MCP 协议说明

### 通信方式

1. **STDIO** - 通过标准输入/输出通信（推荐用于本地工具）
2. **SSE** - Server-Sent Events（用于远程服务器）
3. **WebSocket** - 双向通信
4. **HTTP** - 简单的 HTTP 请求/响应

### 消息格式

所有消息使用 JSON-RPC 2.0 格式：

**请求：**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {
    "name": "calculate",
    "arguments": {"expression": "1 + 2"}
  }
}
```

**响应：**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "content": [{"type": "text", "text": "3"}]
  }
}
```

## 完整配置示例

完整的 `config.yaml` 示例：

```yaml
model_provider: ollama

ollama:
  base_url: http://localhost:11434
  model: gpt-oss:20b
  max_tokens: 65536

# MCP 配置
enable_mcp: true
mcp:
  servers:
    # 内置工具
    - name: code-gen-tools
      type: stdio
      command: python .code_gen/mcp_tools.py

    # Windows 系统控制
    - name: windows
      type: stdio
      command: uv
      args:
        - --directory
        - D:\LX\Windows-MCP
        - run
        - windows-mcp

    # 文件系统
    - name: fs
      type: stdio
      command: npx
      args:
        - -y
        - @modelcontextprotocol/server-filesystem
        - D:\LX\code-gen

    # GitHub
    - name: github
      type: stdio
      command: npx
      args:
        - -y
        - @modelcontextprotocol/server-github
      env:
        GITHUB_PERSONAL_ACCESS_TOKEN: ghp_xxxxxxxxxxxx

# 其他配置...
features:
  auto_commit: false
  verbose: false
```

## 故障排除

### 服务器无法连接

1. 检查命令是否正确
2. 检查依赖是否安装（如 `npx` 需要 Node.js，`uv` 需要 uv）
3. 查看控制台错误信息
4. 常见错误：
   - `FileNotFoundError`：命令不存在，请检查路径
   - `PermissionError`：命令无执行权限，请检查文件权限

### 工具不生效

1. 确认服务器已连接（查看启动日志）
2. 检查工具名称是否正确
3. 尝试重启 Code Gen
4. 如果返回 0 工具，可能是：
   - 服务器还未初始化完成
   - JSON 响应解析失败

### JSON 解析错误

1. 检查服务器输出是否包含非 JSON 内容
2. 某些服务器会输出日志到 stdout，会干扰 JSON 解析
3. 确保服务器只输出 JSON-RPC 响应

### 禁用 MCP

在 `config.yaml` 中设置：
```yaml
enable_mcp: false
```

## 测试

运行 MCP 测试：

```bash
# 测试 MCP 连接和工具发现
python test_mcp_debug.py

# 测试启动和系统提示词构建
python test_startup.py
```

## 进阶用法

### 多服务器连接

```python
# 连接多个 MCP 服务器
await mcp_manager.connect_to_server("server1", config1)
await mcp_manager.connect_to_server("server2", config2)

# 获取所有工具
all_tools = mcp_manager.get_all_tools()
```

### 错误处理

```python
try:
    result = await client.call_tool("my_tool", {})
    if result.success:
        print(result.content)
    else:
        print(f"Error: {result.error}")
except Exception as e:
    print(f"Exception: {e}")
```

## 参考

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [MCP 服务器列表](https://github.com/modelcontextprotocol/servers)
- [内置工具服务器](.code_gen/mcp_tools.py)
- [示例服务器](tests/mcp_server_example.py)
- [简单客户端](code_gen/mcp_simple.py)
