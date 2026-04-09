"""Test memory system"""
import asyncio
import shutil
from pathlib import Path
from code_gen.memory import MemorySystem, MemoryType

async def test_memory_system():
    """Test memory system functionality"""
    print("\n" + "="*60)
    print("测试记忆系统")
    print("="*60)
    
    # Create test directory
    test_dir = Path(__file__).parent.parent / "test_workspace"
    test_dir.mkdir(exist_ok=True)
    
    try:
        # Initialize memory system
        memory_system = MemorySystem(test_dir)
        print(f"\n✓ MemorySystem 初始化成功")
        print(f"  内存目录: {memory_system.memdir_path}")
        
        # Test adding memories
        print("\n--- 测试添加记忆 ---")
        memory1 = memory_system.add_memory(
            content="用户偏好使用Python进行后端开发",
            memory_type="user",
            tags=["preference", "language", "backend"]
        )
        print(f"✓ 添加用户记忆: {memory1.id}")
        
        memory2 = memory_system.add_memory(
            content="项目使用FastAPI框架",
            memory_type="project",
            tags=["framework", "backend", "python"]
        )
        print(f"✓ 添加项目记忆: {memory2.id}")
        
        memory3 = memory_system.add_memory(
            content="数据库使用PostgreSQL",
            memory_type="reference",
            tags=["database", "postgresql"]
        )
        print(f"✓ 添加参考记忆: {memory3.id}")
        
        # Test searching memories
        print("\n--- 测试搜索记忆 ---")
        results = memory_system.search_memories("Python")
        print(f"✓ 搜索 'Python' 找到 {len(results)} 个结果")
        for mem in results:
            print(f"  - {mem.type}: {mem.id}")
        
        results = memory_system.search_memories("database")
        print(f"✓ 搜索 'database' 找到 {len(results)} 个结果")
        for mem in results:
            print(f"  - {mem.type}: {mem.id}")
        
        # Test memory types
        print("\n--- 测试记忆类型 ---")
        user_memories = [m for m in memory_system.memories if m.type == "user"]
        project_memories = [m for m in memory_system.memories if m.type == "project"]
        reference_memories = [m for m in memory_system.memories if m.type == "reference"]
        
        print(f"✓ 用户记忆: {len(user_memories)} 个")
        print(f"✓ 项目记忆: {len(project_memories)} 个")
        print(f"✓ 参考记忆: {len(reference_memories)} 个")
        
        # Test saving and loading
        print("\n--- 测试保存和加载 ---")
        memory_system2 = MemorySystem(test_dir)
        print(f"✓ 重新加载后共有 {len(memory_system2.memories)} 个记忆")
        
        print("\n" + "="*60)
        print("记忆系统测试完成!")
        print("="*60)
        
    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)
        print(f"\n✓ 测试目录已清理: {test_dir}")

if __name__ == "__main__":
    asyncio.run(test_memory_system())
