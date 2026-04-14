"""
功能演示

演示如何将事件总线和 Blob 存储集成到 UnifiedAgent 中
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.agents.unified_agent import UnifiedAgent, UnifiedAgentConfig, create_unified_agent
from code_gen.agents.agent import Agent
from code_gen.agents.event_bus import AgentEvents, EventPriority, get_event_bus


async def demo_event_bus():
    """演示事件总线功能"""
    print("\n" + "="*60)
    print("🎯 演示 1: 事件总线 (Event Bus)")
    print("="*60)
    
    # 创建 Agent
    agent = Agent(
        name="DemoAgent",
        role="assistant",
        goal="演示事件总线功能"
    )
    
    # 创建 UnifiedAgent
    unified = create_unified_agent(
        agent,
        mode="standard",
        agent_id="demo_001",
        verbose=True
    )
    
    # 订阅任务事件
    def on_task_started(data):
        print(f"📢 [事件] 任务开始: {data.get('task', 'N/A')[:30]}...")
    
    def on_task_completed(data):
        print(f"📢 [事件] 任务完成! 耗时: {data.get('execution_time', 0):.2f}s")
    
    def on_task_failed(data):
        print(f"📢 [事件] 任务失败: {data.get('error', 'Unknown')}")
    
    # 注册事件处理器
    unified.on_event(AgentEvents.TASK_STARTED, on_task_started, EventPriority.HIGH)
    unified.on_event(AgentEvents.TASK_COMPLETED, on_task_completed)
    unified.on_event(AgentEvents.TASK_FAILED, on_task_failed)
    
    print("\n📝 执行任务...")
    result = await unified.execute("生成一个 Python 函数，计算斐波那契数列")
    
    print(f"\n✅ 执行结果:")
    print(f"   成功: {result['success']}")
    print(f"   输出: {str(result.get('output', 'N/A'))[:100]}...")
    
    # 获取事件总线统计
    if unified.event_bus:
        stats = unified.event_bus.get_stats()
        print(f"\n📊 事件总线统计:")
        print(f"   总发布: {stats['total_emitted']}")
        print(f"   总处理: {stats['total_handled']}")
        print(f"   处理器数: {stats['handlers_count']}")
    
    return unified


async def demo_blob_store(unified: UnifiedAgent):
    """演示 Blob 存储功能"""
    print("\n" + "="*60)
    print("💾 演示 2: Blob 存储 (Blob Store)")
    print("="*60)
    
    # 存储代码
    code_content = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# 测试
print([fibonacci(i) for i in range(10)])
"""
    
    print("\n📝 存储代码到 Blob...")
    ref = unified.store_blob("fibonacci.py", code_content, track=True)
    
    if ref:
        print(f"✅ 存储成功!")
        print(f"   引用: {ref[:50]}...")
        
        # 读取回来
        print("\n📖 从 Blob 读取...")
        retrieved = unified.get_blob(ref)
        
        if retrieved:
            print(f"✅ 读取成功!")
            print(f"   内容预览: {str(retrieved)[:100]}...")
        
        # 存储二进制数据
        print("\n📝 存储二进制数据...")
        binary_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"  # 模拟 PNG 头
        ref2 = unified.store_blob("image.png", binary_data, track=True)
        
        if ref2:
            print(f"✅ 二进制数据存储成功!")
        
        # 获取统计
        if unified.blob_store:
            stats = unified.blob_store.get_stats()
            print(f"\n📊 Blob 存储统计:")
            print(f"   Blob 数量: {stats['count']}")
            print(f"   总大小: {stats['total_size_mb']:.2f} MB")
            print(f"   存储目录: {stats['dir']}")
        
        # 测试去重
        print("\n📝 测试内容去重...")
        ref3 = unified.store_blob("fibonacci_copy.py", code_content, track=True)
        print(f"   相同内容的引用相同: {ref == ref3}")
    
    return unified


async def demo_cross_agent_events():
    """演示跨 Agent 事件通信"""
    print("\n" + "="*60)
    print("🌐 演示 3: 跨 Agent 事件通信")
    print("="*60)
    
    # 创建共享的事件总线
    shared_bus = get_event_bus("shared")
    
    # 创建两个 Agent
    agent1 = Agent(name="Agent1", role="generator", goal="生成代码")
    agent2 = Agent(name="Agent2", role="validator", goal="验证代码")
    
    unified1 = UnifiedAgent(
        agent1,
        UnifiedAgentConfig(
            agent_id="agent_001",
            event_bus=shared_bus,
            enable_blob_store=False
        ),
        name="GeneratorAgent"
    )
    
    unified2 = UnifiedAgent(
        agent2,
        UnifiedAgentConfig(
            agent_id="agent_002",
            event_bus=shared_bus,
            enable_blob_store=False
        ),
        name="ValidatorAgent"
    )
    
    # Agent2 监听 Agent1 的事件
    def validate_task(data):
        print(f"🔍 [Validator] 收到生成任务: {data.get('task', 'N/A')[:30]}...")
        print(f"   正在验证...")
    
    unified2.on_event(AgentEvents.TASK_STARTED, validate_task)
    
    print("\n📝 Agent1 执行任务...")
    await unified1.execute("生成代码")
    
    print("\n📝 Agent2 执行任务...")
    await unified2.execute("验证代码")


async def demo_event_history():
    """演示事件历史查询"""
    print("\n" + "="*60)
    print("📜 演示 4: 事件历史查询")
    print("="*60)
    
    # 获取全局事件总线
    bus = get_event_bus()
    
    # 发布一些事件
    print("\n📝 发布测试事件...")
    bus.emit("test:event1", {"data": 1})
    bus.emit("test:event2", {"data": 2})
    bus.emit("test:event1", {"data": 3})
    
    # 查询历史
    history = bus.get_history(event_name="test:event1", limit=10)
    
    print(f"\n📜 事件 'test:event1' 历史:")
    for event in history:
        print(f"   - {event.timestamp.strftime('%H:%M:%S')}: {event.data}")
    
    # 获取统计
    stats = bus.get_stats()
    print(f"\n📊 事件总线统计:")
    print(f"   总发布: {stats['total_emitted']}")
    print(f"   总处理: {stats['total_handled']}")
    print(f"   错误数: {stats['errors']}")


async def main():
    """主函数"""
    print("🚀 GSD-2 功能演示")
    print("="*60)
    
    try:
        # 演示 1: 事件总线
        unified = await demo_event_bus()
        
        # 演示 2: Blob 存储
        await demo_blob_store(unified)
        
        # 演示 3: 跨 Agent 事件
        await demo_cross_agent_events()
        
        # 演示 4: 事件历史
        await demo_event_history()
        
        print("\n" + "="*60)
        print("✅ 所有演示完成!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
