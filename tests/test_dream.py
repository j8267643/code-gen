"""Test Dream system"""
import asyncio
import shutil
from pathlib import Path
from code_gen.dream import DreamMemorySystem

async def test_dream_system():
    """Test Dream system functionality"""
    print("\n" + "="*60)
    print("测试Dream系统")
    print("="*60)
    
    # Create test directory
    test_dir = Path(__file__).parent.parent / "test_workspace"
    test_dir.mkdir(exist_ok=True)
    
    try:
        # Initialize dream system
        dream_system = DreamMemorySystem(test_dir)
        print(f"\n✓ DreamMemorySystem 初始化成功")
        print(f"  梦想目录: {dream_system.dream_dir}")
        
        # Add some test memories first
        from code_gen.memory import MemorySystem
        memory_system = MemorySystem(test_dir)
        
        memory_system.add_memory(
            content="用户喜欢使用Python进行Web开发",
            memory_type="user",
            tags=["python", "web", "preference"]
        )
        
        memory_system.add_memory(
            content="项目使用FastAPI框架",
            memory_type="project",
            tags=["fastapi", "framework", "backend"]
        )
        
        memory_system.add_memory(
            content="数据库使用PostgreSQL",
            memory_type="reference",
            tags=["database", "postgresql"]
        )
        
        print(f"✓ 添加了 {len(memory_system.memories)} 个测试记忆")
        
        # Test dream process
        print("\n--- 测试Dream过程 ---")
        result = await dream_system.run_dream_process()
        
        if result.get("status") == "skipped":
            print(f"⚠ Dream过程跳过: {result.get('message')}")
        else:
            print(f"✓ Dream过程完成!")
            print(f"  阶段统计:")
            print(f"    - 原始片段: {result['stages']['fragment_collection']}")
            print(f"    - 关联分析: {result['stages']['association_analysis']}")
            print(f"    - 知识提取: {result['stages']['knowledge_extraction']}")
            print(f"    - 记忆索引: {result['stages']['memory_indexing']}")
        
        # Test dream history
        print("\n--- 测试Dream历史 ---")
        print(f"✓ Dream历史条数: {len(dream_system.dream_history)}")
        
        if dream_system.dream_history:
            last_dream = dream_system.dream_history[-1]
            print(f"  最后一次Dream:")
            print(f"    时间: {last_dream['timestamp']}")
            print(f"    状态: {last_dream.get('status', 'completed')}")
        
        print("\n" + "="*60)
        print("Dream系统测试完成!")
        print("="*60)
        
    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)
        print(f"\n✓ 测试目录已清理: {test_dir}")

if __name__ == "__main__":
    asyncio.run(test_dream_system())
