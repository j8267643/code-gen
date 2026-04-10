#!/usr/bin/env python3
"""
MCP 客户端使用示例
演示如何连接和使用 MCP 服务器
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from code_gen.mcp import mcp_manager, MCPConnectionConfig, MCPServerType


async def test_mcp():
    """测试 MCP 连接和工具调用"""
    print("=" * 70)
    print("MCP 客户端测试")
    print("=" * 70)

    # 配置 MCP 服务器 (STDIO 模式)
    config = MCPConnectionConfig(
        server_type=MCPServerType.STDIO,
        stdio_command="python mcp_server_example.py"
    )

    print("\n1. 连接到 MCP 服务器...")
    try:
        connected = await mcp_manager.connect_to_server("simple", config)
        if connected:
            print("连接成功!")
        else:
            print("连接失败")
            return
    except Exception as e:
        print(f"连接错误: {e}")
        return

    # 获取可用工具
    print("\n2. 获取可用工具...")
    tools = mcp_manager.get_all_tools()
    print(f"可用工具数: {len(tools)}")

    for tool in tools:
        print(f"\n  - {tool.name}")
        print(f"    描述: {tool.description}")
        print(f"    参数: {list(tool.input_schema.get('properties', {}).keys())}")

    # 测试调用工具
    print("\n3. 测试工具调用...")

    # 测试 get_current_time
    print("\n  调用 get_current_time:")
    try:
        result = await mcp_manager.call_tool("simple", "get_current_time", {})
        if result.success:
            print(f"    结果: {result.content}")
        else:
            print(f"    错误: {result.error}")
    except Exception as e:
        print(f"    异常: {e}")

    # 测试 calculate
    print("\n  调用 calculate (1 + 2 * 3):")
    try:
        result = await mcp_manager.call_tool("simple", "calculate", {"expression": "1 + 2 * 3"})
        if result.success:
            print(f"    结果: {result.content}")
        else:
            print(f"    错误: {result.error}")
    except Exception as e:
        print(f"    异常: {e}")

    # 测试 echo
    print("\n  调用 echo ('Hello MCP!'):")
    try:
        result = await mcp_manager.call_tool("simple", "echo", {"message": "Hello MCP!"})
        if result.success:
            print(f"    结果: {result.content}")
        else:
            print(f"    错误: {result.error}")
    except Exception as e:
        print(f"    异常: {e}")

    # 断开连接
    print("\n4. 断开连接...")
    await mcp_manager.disconnect_server("simple")
    print("已断开")

    print("\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_mcp())
