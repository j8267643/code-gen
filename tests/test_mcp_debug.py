#!/usr/bin/env python3
"""Debug MCP connection"""
import asyncio
from code_gen.mcp import mcp_manager, MCPConnectionConfig, MCPServerType

async def test_mcp():
    """Test MCP connection"""
    print("Testing MCP connection...")

    # Test code-gen-tools
    config1 = MCPConnectionConfig(
        server_type=MCPServerType.STDIO,
        stdio_command="python .code_gen/mcp_tools.py"
    )

    client1 = await mcp_manager.connect_to_server("code-gen-tools", config1)
    if client1:
        print(f"✓ code-gen-tools connected")
        tools1 = await client1.list_tools()
        print(f"  Tools: {len(tools1)}")
        for tool in tools1:
            print(f"    - {tool.name}: {tool.description}")
    else:
        print("✗ code-gen-tools failed")

    print(f"\nMCP Manager clients: {list(mcp_manager.clients.keys())}")
    for name, client in mcp_manager.clients.items():
        print(f"  {name}: connected={client.connected}, tools={len(client.tools)}")

if __name__ == "__main__":
    asyncio.run(test_mcp())
