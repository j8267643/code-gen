#!/usr/bin/env python3
"""Test MCP connection and tools"""
import asyncio
from code_gen.mcp import mcp_manager, MCPConnectionConfig, MCPServerType

async def test_mcp():
    """Test MCP connection"""
    print("Testing MCP connection...")
    print(f"Current clients: {mcp_manager.clients}")
    print(f"Current tool cache: {mcp_manager.tool_cache}")

    # Try to connect to built-in tools
    config = MCPConnectionConfig(
        server_type=MCPServerType.STDIO,
        stdio_command="python .code_gen/mcp_tools.py"
    )

    client = await mcp_manager.connect_to_server("test-tools", config)

    if client:
        print(f"✓ Connected to MCP server")
        print(f"  Connected: {client.connected}")
        print(f"  Tools: {len(client.tools)}")
        for tool in client.tools:
            print(f"    - {tool.name}: {tool.description}")
    else:
        print("✗ Failed to connect")

    print(f"\nAfter connection:")
    print(f"Clients: {list(mcp_manager.clients.keys())}")
    print(f"Tool cache: {list(mcp_manager.tool_cache.keys())}")

if __name__ == "__main__":
    asyncio.run(test_mcp())
