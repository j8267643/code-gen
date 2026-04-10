#!/usr/bin/env python3
"""Test system prompt building"""
import asyncio
from code_gen.mcp import mcp_manager, MCPConnectionConfig, MCPServerType

async def test_prompt():
    """Test building MCP tools section"""
    # First connect to MCP
    config = MCPConnectionConfig(
        server_type=MCPServerType.STDIO,
        stdio_command="python .code_gen/mcp_tools.py"
    )

    client = await mcp_manager.connect_to_server("code-gen-tools", config)
    if client:
        print("✓ MCP connected")
        tools = await client.list_tools()
        print(f"✓ Got {len(tools)} tools")
    else:
        print("✗ MCP failed")
        return

    # Now test building the section
    print("\nBuilding MCP tools section...")
    print(f"Clients: {list(mcp_manager.clients.keys())}")

    lines = ["Available MCP tools:"]
    all_tools = []

    for server_name, client in mcp_manager.clients.items():
        print(f"  Checking {server_name}: connected={client.connected}, tools={len(client.tools)}")
        if client.connected and client.tools:
            for tool in client.tools:
                all_tools.append((server_name, tool))

    if all_tools:
        for server_name, tool in all_tools:
            desc = tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
            lines.append(f"- {tool.name} ({server_name}): {desc}")
    else:
        lines.append("- No MCP servers connected")

    print("\n" + "="*50)
    print("MCP Tools Section:")
    print("="*50)
    print("\n".join(lines))

if __name__ == "__main__":
    asyncio.run(test_prompt())
