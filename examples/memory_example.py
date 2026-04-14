"""
Memory System Example - 记忆系统示例

展示 PraisonAI 风格的记忆系统功能
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.agents import AgentMemory, MemoryConfig, MemoryType, StorageBackend, create_memory


async def example_1_basic_memory():
    """示例1: 基础记忆存储"""
    print("\n" + "="*60)
    print("示例1: 基础记忆存储")
    print("="*60 + "\n")
    
    # 创建记忆系统（使用文件存储）
    memory = create_memory(
        backend="file",
        storage_path=".memory_example",
        user_id="user_001"
    )
    
    # 存储短期记忆
    print("存储短期记忆...")
    id1 = memory.store_short_term("用户询问Python编程问题", importance=0.6)
    id2 = memory.store_short_term("用户喜欢使用VS Code编辑器", importance=0.5)
    print(f"  已存储2条短期记忆")
    
    # 存储长期记忆
    print("\n存储长期记忆...")
    id3 = memory.store_long_term("用户是高级Python开发者", importance=0.9)
    id4 = memory.store_long_term("用户在科技公司工作", importance=0.85)
    print(f"  已存储2条长期记忆")
    
    # 存储实体记忆
    print("\n存储实体记忆...")
    id5 = memory.store_entity(
        name="张三",
        entity_type="person",
        attributes={"role": "developer", "company": "TechCorp", "skills": ["Python", "AI"]}
    )
    print(f"  已存储1个实体")
    
    # 存储情景记忆
    print("\n存储情景记忆...")
    id6 = memory.store_episodic(
        event="完成了第一个AI项目",
        context={"project": "chatbot", "result": "success"}
    )
    print(f"  已存储1个情景")
    
    # 查看统计
    stats = memory.get_stats()
    print(f"\n记忆统计:")
    for mem_type, count in stats.items():
        print(f"  {mem_type}: {count} 条")


async def example_2_memory_retrieval():
    """示例2: 记忆检索"""
    print("\n" + "="*60)
    print("示例2: 记忆检索")
    print("="*60 + "\n")
    
    memory = create_memory(
        backend="file",
        storage_path=".memory_example",
        user_id="user_002"
    )
    
    # 先存储一些记忆
    memory.store_short_term("最近学习了FastAPI框架", importance=0.7)
    memory.store_short_term("正在研究机器学习", importance=0.6)
    memory.store_long_term("有5年Python开发经验", importance=0.9)
    memory.store_long_term("精通Django和Flask", importance=0.85)
    
    # 检索短期记忆
    print("短期记忆（最近）:")
    short_term = memory.get_short_term(limit=3)
    for entry in short_term:
        print(f"  - {entry.content} (重要性: {entry.importance})")
    
    # 检索长期记忆
    print("\n长期记忆（高重要性）:")
    long_term = memory.get_long_term(limit=3, min_importance=0.8)
    for entry in long_term:
        print(f"  - {entry.content} (重要性: {entry.importance})")
    
    # 搜索记忆
    print("\n搜索包含'Python'的记忆:")
    results = memory.search("Python", limit=5)
    for entry in results:
        print(f"  - [{entry.memory_type.value}] {entry.content}")


async def example_3_context_building():
    """示例3: 上下文构建"""
    print("\n" + "="*60)
    print("示例3: 上下文构建")
    print("="*60 + "\n")
    
    memory = create_memory(
        backend="file",
        storage_path=".memory_example",
        user_id="user_003"
    )
    
    # 存储用户相关信息
    memory.store_short_term("用户: 我想学习AI编程", importance=0.6)
    memory.store_short_term("用户: 推荐一些学习资源", importance=0.5)
    memory.store_long_term("用户偏好: 喜欢视频教程", importance=0.8)
    memory.store_long_term("用户水平: 中级Python开发者", importance=0.85)
    memory.store_entity("李华", "person", {"role": "student", "interests": ["AI", "Python"]})
    
    # 构建上下文
    print("构建上下文（查询: AI学习）:")
    context = memory.build_context(query="AI学习", max_items=5)
    print(context)
    
    print("\n" + "-"*60)
    print("构建上下文（无查询）:")
    context2 = memory.build_context()
    print(context2)


async def example_4_sqlite_backend():
    """示例4: SQLite存储后端"""
    print("\n" + "="*60)
    print("示例4: SQLite存储后端")
    print("="*60 + "\n")
    
    # 使用SQLite后端
    memory = create_memory(
        backend="sqlite",
        storage_path=".memory_sqlite",
        user_id="user_004"
    )
    
    # 存储记忆
    print("使用SQLite存储记忆...")
    memory.store_short_term("测试SQLite存储", importance=0.6)
    memory.store_long_term("SQLite是轻量级数据库", importance=0.8)
    memory.store_episodic("完成了SQLite测试")
    
    # 检索
    print("\n检索结果:")
    short_term = memory.get_short_term(limit=5)
    for entry in short_term:
        print(f"  - {entry.content}")
    
    # 搜索
    print("\n搜索'SQLite':")
    results = memory.search("SQLite")
    for entry in results:
        print(f"  - [{entry.memory_type.value}] {entry.content}")


async def example_5_memory_management():
    """示例5: 记忆管理"""
    print("\n" + "="*60)
    print("示例5: 记忆管理")
    print("="*60 + "\n")
    
    memory = create_memory(
        backend="file",
        storage_path=".memory_example",
        user_id="user_005"
    )
    
    # 存储多条记忆
    print("存储多条记忆...")
    for i in range(5):
        memory.store_short_term(f"测试记忆 {i+1}", importance=0.5)
    
    stats_before = memory.get_stats()
    print(f"\n清空前统计:")
    for mem_type, count in stats_before.items():
        print(f"  {mem_type}: {count} 条")
    
    # 清空短期记忆
    print("\n清空短期记忆...")
    memory.clear(memory_type=MemoryType.SHORT_TERM)
    
    stats_after = memory.get_stats()
    print(f"\n清空后统计:")
    for mem_type, count in stats_after.items():
        print(f"  {mem_type}: {count} 条")
    
    # 导出记忆
    print("\n导出所有记忆...")
    exported = memory.export()
    print(f"  导出 {len(exported)} 种记忆类型")


async def example_6_auto_promotion():
    """示例6: 自动晋升长期记忆"""
    print("\n" + "="*60)
    print("示例6: 自动晋升长期记忆")
    print("="*60 + "\n")
    
    # 创建配置，启用自动晋升
    config = MemoryConfig(
        backend=StorageBackend.FILE,
        storage_path=Path(".memory_example"),
        user_id="user_006",
        auto_promote=True,
        importance_threshold=0.7  # 重要性>=0.7自动晋升
    )
    
    memory = AgentMemory(config)
    
    print("存储不同重要性的记忆...")
    
    # 低重要性 - 不会晋升
    memory.store_short_term("普通对话内容1", importance=0.5)
    memory.store_short_term("普通对话内容2", importance=0.6)
    
    # 高重要性 - 会自动晋升
    memory.store_short_term("用户密码: secret123", importance=0.9)
    memory.store_short_term("用户API密钥: sk-xxx", importance=0.95)
    
    # 查看统计
    stats = memory.get_stats()
    print(f"\n记忆统计:")
    for mem_type, count in stats.items():
        print(f"  {mem_type}: {count} 条")
    
    print("\n注意: 高重要性记忆已自动晋升到长期记忆！")


async def main():
    """运行所有示例"""
    print("\n" + "🧠"*30)
    print("Memory System (记忆系统) 示例")
    print("🧠"*30)
    
    await example_1_basic_memory()
    await example_2_memory_retrieval()
    await example_3_context_building()
    await example_4_sqlite_backend()
    await example_5_memory_management()
    await example_6_auto_promotion()
    
    print("\n" + "="*60)
    print("所有示例完成!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
