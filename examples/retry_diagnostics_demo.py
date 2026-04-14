"""
重试处理器和诊断系统演示

演示如何将 GSD-2 的重试处理器和诊断系统集成到 UnifiedAgent 中
"""
import asyncio
import sys
import random
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.agents.unified_agent import UnifiedAgent, UnifiedAgentConfig, create_unified_agent
from code_gen.agents.agent import Agent
from code_gen.agents.retry_handler import RetryConfig
from code_gen.agents.diagnostics import DiagnosticLevel


# 模拟不稳定的 API 调用
async def unstable_api_call(fail_rate: float = 0.7) -> str:
    """
    模拟不稳定的 API 调用
    
    Args:
        fail_rate: 失败概率 (0-1)
    
    Returns:
        API 响应
    
    Raises:
        Exception: 随机失败
    """
    if random.random() < fail_rate:
        raise ConnectionError(f"API 连接失败 (模拟)")
    return "API 调用成功!"


async def demo_retry_handler():
    """演示重试处理器功能"""
    print("\n" + "="*60)
    print("🔄 演示 1: 重试处理器 (Retry Handler)")
    print("="*60)
    
    # 创建 Agent
    agent = Agent(
        name="RetryDemoAgent",
        role="assistant",
        goal="演示重试功能"
    )
    
    # 创建 UnifiedAgent，启用重试
    unified = create_unified_agent(
        agent,
        mode="standard",
        agent_id="retry_demo_001",
        verbose=True
    )
    
    print("\n📝 方法 1: 使用装饰器添加重试")
    print("-" * 40)
    
    # 使用装饰器
    @unified.with_retry(max_retries=3, base_delay=0.5)
    async def call_api_with_retry():
        return await unstable_api_call(fail_rate=0.6)
    
    try:
        result = await call_api_with_retry()
        print(f"✅ 最终结果: {result}")
    except Exception as e:
        print(f"❌ 最终失败: {e}")
    
    # 获取重试统计
    retry_stats = unified.get_retry_stats()
    print(f"\n📊 重试统计:")
    print(f"   启用状态: {retry_stats['enabled']}")
    if retry_stats['enabled']:
        print(f"   总尝试: {retry_stats.get('total_attempts', 0)}")
        print(f"   成功重试: {retry_stats.get('successful_retries', 0)}")
        print(f"   永久失败: {retry_stats.get('failed_permanently', 0)}")
    
    print("\n📝 方法 2: 使用 execute_with_retry 方法")
    print("-" * 40)
    
    # 直接使用 execute_with_retry
    try:
        result = await unified.execute_with_retry(
            unstable_api_call,
            fail_rate=0.5
        )
        print(f"✅ 执行成功: {result}")
    except Exception as e:
        print(f"❌ 执行失败: {e}")
    
    # 再次查看统计
    retry_stats = unified.get_retry_stats()
    print(f"\n📊 更新后的重试统计:")
    print(f"   总尝试: {retry_stats.get('total_attempts', 0)}")
    print(f"   成功重试: {retry_stats.get('successful_retries', 0)}")
    
    return unified


async def demo_diagnostics(unified: UnifiedAgent):
    """演示诊断系统功能"""
    print("\n" + "="*60)
    print("🔍 演示 2: 诊断系统 (Diagnostics)")
    print("="*60)
    
    print("\n📝 记录诊断信息")
    print("-" * 40)
    
    # 记录不同级别的诊断信息
    unified.log_diagnostic(
        level="info",
        category="initialization",
        message="Agent 初始化完成",
        details={"agent_id": unified.config.agent_id}
    )
    
    unified.log_diagnostic(
        level="warning",
        category="performance",
        message="API 响应较慢",
        details={"latency_ms": 2500}
    )
    
    unified.log_diagnostic(
        level="error",
        category="network",
        message="连接超时",
        details={"endpoint": "api.example.com", "timeout": 30}
    )
    
    unified.log_diagnostic(
        level=DiagnosticLevel.DEBUG,
        category="execution",
        message="开始执行任务",
        details={"task_id": "task_001"}
    )
    
    print("✅ 已记录 4 条诊断信息")
    
    # 运行健康检查
    print("\n📝 运行健康检查")
    print("-" * 40)
    
    health = await unified.run_health_check()
    
    print(f"系统状态: {health['status']}")
    print(f"总体延迟: {health['overall_latency_ms']:.2f} ms")
    
    if health['checks']:
        print("\n检查项:")
        for name, check in health['checks'].items():
            status = "✅" if check['healthy'] else "❌"
            print(f"   {status} {name}: {check['message']}")
    
    # 获取诊断报告
    print("\n📝 获取诊断报告")
    print("-" * 40)
    
    report = unified.get_diagnostics_report()
    
    print(f"报告生成时间: {report['generated_at']}")
    print(f"条目总数: {report['entries_count']}")
    print(f"统计: {report['stats']}")
    
    if report['recent_entries']:
        print("\n最近 10 条诊断:")
        for entry in report['recent_entries']:
            level_emoji = {
                'debug': '🔍',
                'info': 'ℹ️',
                'warning': '⚠️',
                'error': '❌',
                'critical': '🔥'
            }.get(entry['level'], '•')
            print(f"   {level_emoji} [{entry['timestamp'][11:19]}] "
                  f"[{entry['level'].upper()}] {entry['category']}: {entry['message']}")


async def demo_retry_with_diagnostics():
    """演示重试与诊断结合"""
    print("\n" + "="*60)
    print("🔄🔍 演示 3: 重试与诊断结合")
    print("="*60)
    
    # 创建 Agent，自定义重试配置
    agent = Agent(
        name="CombinedDemoAgent",
        role="assistant",
        goal="演示重试和诊断结合"
    )
    
    # 自定义重试配置
    retry_config = RetryConfig(
        max_retries=5,
        base_delay=0.2,
        max_delay=2.0,
        exponential_base=2.0,
        jitter=True
    )
    
    unified = UnifiedAgent(
        agent,
        UnifiedAgentConfig(
            agent_id="combined_demo_001",
            enable_reflection=False,
            enable_memory=False,
            enable_guardrails=False,
            enable_hitl=False,
            enable_retry=True,
            retry_config=retry_config,
            enable_diagnostics=True,
            verbose=True
        ),
        name="CombinedDemo"
    )
    
    print("\n📝 执行带重试和诊断的函数")
    print("-" * 40)
    
    attempt_count = 0
    
    @unified.with_retry(max_retries=5, base_delay=0.2)
    async def flaky_operation():
        nonlocal attempt_count
        attempt_count += 1
        
        # 70% 概率失败，但第 3 次后必定成功
        if attempt_count < 3 and random.random() < 0.7:
            raise ConnectionError(f"第 {attempt_count} 次尝试失败")
        
        return f"第 {attempt_count} 次尝试成功!"
    
    try:
        result = await flaky_operation()
        print(f"✅ {result}")
    except Exception as e:
        print(f"❌ 最终失败: {e}")
    
    # 查看重试统计
    retry_stats = unified.get_retry_stats()
    print(f"\n📊 重试统计:")
    print(f"   总尝试: {retry_stats.get('total_attempts', 0)}")
    print(f"   成功重试: {retry_stats.get('successful_retries', 0)}")
    print(f"   总等待时间: {retry_stats.get('total_wait_time', 0):.2f}s")
    
    # 查看诊断报告
    report = unified.get_diagnostics_report()
    print(f"\n📊 诊断统计:")
    print(f"   条目数: {report['entries_count']}")
    
    if report['recent_entries']:
        print("\n重试相关诊断:")
        for entry in report['recent_entries']:
            if entry['category'] == 'retry':
                print(f"   • [{entry['level']}] {entry['message']}")


async def demo_disabled_features():
    """演示禁用功能的情况"""
    print("\n" + "="*60)
    print("🚫 演示 4: 禁用功能的情况")
    print("="*60)
    
    agent = Agent(
        name="DisabledDemoAgent",
        role="assistant",
        goal="演示禁用功能"
    )
    
    # 创建禁用重试和诊断的 Agent
    unified = UnifiedAgent(
        agent,
        UnifiedAgentConfig(
            agent_id="disabled_demo_001",
            enable_retry=False,       # 禁用重试
            enable_diagnostics=False,  # 禁用诊断
            enable_event_bus=False,
            enable_blob_store=False,
            enable_reflection=False,
            enable_memory=False,
            enable_guardrails=False,
            enable_hitl=False,
        ),
        name="DisabledDemo"
    )
    
    print("\n📝 检查功能状态")
    print("-" * 40)
    
    retry_stats = unified.get_retry_stats()
    print(f"重试处理器: {'✅ 启用' if retry_stats['enabled'] else '❌ 禁用'}")
    
    diag_report = unified.get_diagnostics_report()
    print(f"诊断系统: {'✅ 启用' if diag_report['enabled'] else '❌ 禁用'}")
    
    # 尝试使用禁用功能
    print("\n📝 尝试使用禁用功能")
    print("-" * 40)
    
    # 记录诊断（应该无效果）
    unified.log_diagnostic("info", "test", "这条消息不会被记录")
    print("✅ 记录诊断信息（无效果，因为诊断被禁用）")
    
    # 使用重试装饰器（应该直接执行，无重试）
    @unified.with_retry(max_retries=3)
    async def simple_func():
        return "直接执行"
    
    result = await simple_func()
    print(f"✅ 执行结果: {result}（无重试，因为重试被禁用）")


async def main():
    """主函数"""
    print("🚀 重试处理器和诊断系统演示")
    print("="*60)
    
    try:
        # 演示 1: 重试处理器
        unified = await demo_retry_handler()
        
        # 演示 2: 诊断系统
        await demo_diagnostics(unified)
        
        # 演示 3: 重试与诊断结合
        await demo_retry_with_diagnostics()
        
        # 演示 4: 禁用功能
        await demo_disabled_features()
        
        print("\n" + "="*60)
        print("✅ 所有演示完成!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
