#!/usr/bin/env python3
"""
Test long content memory storage
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.memory_system import AdvancedMemorySystem, MemoryCategory


def test_long_memory():
    """Test storing long content as markdown file"""
    work_dir = Path.cwd()
    memory = AdvancedMemorySystem(work_dir)
    
    long_content = """
# MCP 完整使用指南

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

### Windows-MCP (Windows 系统控制)
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

### 文件系统服务器
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

## 服务器类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| `stdio` | 通过标准输入/输出通信 | 本地工具、Python/Node.js 脚本 |
| `http` | HTTP 请求/响应 | REST API 服务 |
| `sse` | Server-Sent Events | 流式数据服务 |
| `ws` | WebSocket | 双向实时通信 |

## 故障排除

### 服务器无法连接

1. 检查命令是否正确
2. 检查依赖是否安装（如 `npx` 需要 Node.js，`uv` 需要 uv）
3. 查看控制台错误信息

### 工具不生效

1. 确认服务器已连接（查看启动日志）
2. 检查工具名称是否正确
3. 尝试重启 Code Gen

## 参考

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [MCP 服务器列表](https://github.com/modelcontextprotocol/servers)
"""
    
    print("Adding long memory content...")
    mem = memory.add_memory(
        content=long_content,
        category=MemoryCategory.KNOWLEDGE,
        tags=["mcp", "guide", "documentation"],
        importance=9
    )
    
    print(f"Memory ID: {mem.id}")
    print(f"Summary: {mem.summary}")
    print(f"Tags: {mem.tags}")
    
    # Check if file was created
    content_dir = work_dir / ".code_gen" / "memory" / "content" / "knowledge"
    if content_dir.exists():
        files = list(content_dir.glob("*.md"))
        print(f"\nMarkdown files created: {len(files)}")
        for f in files:
            print(f"  - {f.name} ({f.stat().st_size} bytes)")
    
    print("\nDone!")


if __name__ == "__main__":
    test_long_memory()
