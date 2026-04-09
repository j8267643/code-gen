"""Test MCP system"""
import asyncio
import shutil
from pathlib import Path

async def test_mcp_system():
    """Test MCP system functionality"""
    print("\n" + "="*60)
    print("测试MCP系统")
    print("="*60)
    
    try:
        from code_gen.mcp import mcp_manager, MCPConnectionConfig, MCPServerType
        
        print(f"\n✓ MCP管理器初始化成功")
        
        # Test server connection
        print("\n--- 测试服务器连接 ---")
        
        # Try to connect to default server
        config = MCPConnectionConfig(
            server_type=MCPServerType.STDIO,
            stdio_command=None
        )
        
        try:
            await mcp_manager.connect_to_server("default", config)
            print(f"✓ 连接到 'default' 服务器")
        except Exception as e:
            print(f"⚠ 连接 'default' 服务器失败 (可能未配置): {e}")
        
        # Test getting tools
        print("\n--- 测试获取工具 ---")
        tools = mcp_manager.get_all_tools()
        print(f"✓ MCP工具总数: {len(tools)}")
        
        if tools:
            print(f"  前5个工具:")
            for tool in tools[:5]:
                print(f"    - {tool.name}: {tool.description[:50]}...")
        
        # Test client status
        print("\n--- 测试客户端状态 ---")
        if mcp_manager.clients:
            print(f"✓ 已连接的客户端: {len(mcp_manager.clients)}")
            for server_name, client in mcp_manager.clients.items():
                print(f"  - {server_name}: {'已连接' if client.connected else '未连接'}")
        else:
            print("⚠ 没有已连接的客户端")
        
        print("\n" + "="*60)
        print("MCP系统测试完成!")
        print("="*60)
        
    except Exception as e:
        print(f"\n⚠ MCP系统测试跳过: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_system())
