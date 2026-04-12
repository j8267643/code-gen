#!/usr/bin/env python3
"""
Test the new advanced memory system
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.memory_system import AdvancedMemorySystem, MemoryCategory


def test_memory_system():
    """Test advanced memory features"""
    work_dir = Path.cwd()
    memory = AdvancedMemorySystem(work_dir)
    
    print("=" * 60)
    print("Advanced Memory System Test")
    print("=" * 60)
    
    # Test 1: Add memories
    print("\n1. Adding memories...")
    
    mem1 = memory.add_memory(
        content="""MCP (Model Context Protocol) 是一个协议，允许 AI 助手连接外部工具和服务。

主要特点：
- 标准化接口
- 支持多种传输方式 (stdio, http, sse, ws)
- 工具发现和调用
- 无需代码即可扩展 AI 能力

使用场景：
- 文件系统操作
- 数据库查询
- API 调用
- 系统控制""",
        category=MemoryCategory.KNOWLEDGE,
        tags=["mcp", "protocol", "ai"],
        importance=8
    )
    print(f"  Added: {mem1.id}")
    print(f"  Summary: {mem1.summary[:50]}...")
    
    mem2 = memory.add_memory(
        content="""用户偏好：
- 使用 Ollama 作为 AI 提供商
- 喜欢简洁的代码风格
- 偏好中文回复
- 经常使用 Windows-MCP 控制系统""",
        category=MemoryCategory.USER_PREF,
        tags=["preference", "ollama", "chinese"],
        importance=9
    )
    print(f"  Added: {mem2.id}")
    
    # Test 2: Search
    print("\n2. Searching memories...")
    results = memory.search_memories("MCP protocol")
    print(f"  Found {len(results)} results for 'MCP protocol'")
    for r in results:
        print(f"    - {r.summary[:40]}...")
    
    # Test 3: Get by category
    print("\n3. Getting memories by category...")
    knowledge = memory.get_memories_by_category(MemoryCategory.KNOWLEDGE)
    print(f"  Knowledge memories: {len(knowledge)}")
    
    user_prefs = memory.get_memories_by_category(MemoryCategory.USER_PREF)
    print(f"  User preference memories: {len(user_prefs)}")
    
    # Test 4: Link memories
    print("\n4. Linking memories...")
    memory.link_memories(mem1.id, mem2.id)
    print(f"  Linked {mem1.id[:20]}... <-> {mem2.id[:20]}...")
    
    # Test 5: Get related
    print("\n5. Getting related memories...")
    related = memory.get_related_memories(mem1.id)
    print(f"  Found {len(related)} related memories")
    
    # Test 6: Stats
    print("\n6. Memory statistics...")
    stats = memory.get_memory_stats()
    print(f"  Total: {stats['total']}")
    print(f"  By category: {stats['by_category']}")
    print(f"  Avg importance: {stats['avg_importance']}")
    
    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_memory_system()
