"""Test history system"""
import asyncio
import shutil
from pathlib import Path
from code_gen.history import HistorySystem

async def test_history_system():
    """Test history system functionality"""
    print("\n" + "="*60)
    print("测试历史系统")
    print("="*60)
    
    # Create test directory
    test_dir = Path(__file__).parent.parent / "test_workspace"
    test_dir.mkdir(exist_ok=True)
    
    try:
        # Initialize history system
        history_system = HistorySystem(test_dir)
        print(f"\n✓ HistorySystem 初始化成功")
        print(f"  历史文件: {history_system.history_path}")
        
        # Test adding items
        print("\n--- 测试添加历史项 ---")
        
        item1 = history_system.add_item(
            item_type="message",
            content="用户: 你好",
            role="user",
            session_id="test_session_1"
        )
        print(f"✓ 添加历史项: {item1.id}")
        
        item2 = history_system.add_item(
            item_type="message",
            content="助手: 你好！有什么可以帮助你的吗？",
            role="assistant",
            session_id="test_session_1"
        )
        print(f"✓ 添加历史项: {item2.id}")
        
        item3 = history_system.add_item(
            item_type="command",
            content="/files",
            session_id="test_session_1"
        )
        print(f"✓ 添加历史项: {item3.id}")
        
        item4 = history_system.add_item(
            item_type="tool",
            content="read_file: README.md",
            session_id="test_session_1"
        )
        print(f"✓ 添加历史项: {item4.id}")
        
        # Test getting recent items
        print("\n--- 测试获取最近项 ---")
        recent = history_system.get_recent_items(3)
        print(f"✓ 最近 {len(recent)} 个历史项:")
        for item in recent:
            print(f"  - [{item.type}] {item.id}")
            print(f"    {item.content[:50]}...")
        
        # Test filtering by type
        print("\n--- 测试按类型过滤 ---")
        messages = history_system.get_recent_items(10, item_type="message")
        print(f"✓ 消息类型历史: {len(messages)} 个")
        
        commands = history_system.get_recent_items(10, item_type="command")
        print(f"✓ 命令类型历史: {len(commands)} 个")
        
        tools = history_system.get_recent_items(10, item_type="tool")
        print(f"✓ 工具类型历史: {len(tools)} 个")
        
        # Test search
        print("\n--- 测试搜索历史 ---")
        results = history_system.search("你好", limit=5)
        print(f"✓ 搜索 '你好' 找到 {len(results)} 个结果:")
        for item in results:
            print(f"  - [{item.type}] {item.id}")
        
        results = history_system.search("read_file", limit=5)
        print(f"✓ 搜索 'read_file' 找到 {len(results)} 个结果:")
        for item in results:
            print(f"  - [{item.type}] {item.id}")
        
        # Test duplicate prevention
        print("\n--- 测试重复项防止 ---")
        original_count = len(history_system.items)
        history_system.add_item(
            item_type="message",
            content="用户: 你好",
            role="user",
            session_id="test_session_1"
        )
        new_count = len(history_system.items)
        print(f"✓ 重复项添加后数量: {original_count} → {new_count}")
        
        print("\n" + "="*60)
        print("历史系统测试完成!")
        print("="*60)
        
    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)
        print(f"\n✓ 测试目录已清理: {test_dir}")

if __name__ == "__main__":
    asyncio.run(test_history_system())
