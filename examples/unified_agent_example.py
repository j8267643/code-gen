"""
Unified Agent Example - 统一智能体示例

展示所有 PraisonAI 功能的整合使用：
- Self-Reflection (自反思)
- Memory System (记忆系统)
- Guardrails (护栏验证)
- Human-in-the-loop (人机协作)
- Evaluator-Optimizer (评估优化)
- Prompt Chaining (提示链)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.agents import (
    # 基础组件
    Agent,
    AgentRole,
    # 统一智能体
    UnifiedAgent,
    UnifiedAgentConfig,
    create_unified_agent,
    # 配置
    ReflectionConfig,
    MemoryConfig,
    HITLConfig,
    HITLMode,
    # 工具
    PerformanceMonitor,
    timing_decorator,
    generate_id
)


async def example_1_minimal_agent():
    """示例1: 最小化 Agent（仅核心功能）"""
    print("\n" + "="*60)
    print("示例1: 最小化 Agent 模式")
    print("="*60 + "\n")
    
    # 创建基础 Agent
    agent = Agent(
        name="MinimalAgent",
        role=AgentRole.DEVELOPER,
        instructions="你是一个高效的代码生成助手"
    )
    
    # 创建最小化统一 Agent（仅启用必要功能）
    unified = create_unified_agent(
        agent=agent,
        mode="minimal",
        verbose=True
    )
    
    print("配置:")
    print(f"  自反思: {unified.config.enable_reflection}")
    print(f"  记忆系统: {unified.config.enable_memory}")
    print(f"  护栏: {unified.config.enable_guardrails}")
    print(f"  人机协作: {unified.config.enable_hitl}")
    
    # 执行任务
    result = await unified.execute(
        task="生成一个 Python 函数，计算斐波那契数列"
    )
    
    print(f"\n执行结果:")
    print(f"  成功: {result['success']}")
    print(f"  使用模块: {', '.join(result['modules_used'])}")
    print(f"  耗时: {result['execution_time']:.2f}s")


async def example_2_standard_agent():
    """示例2: 标准 Agent（推荐配置）"""
    print("\n" + "="*60)
    print("示例2: 标准 Agent 模式（推荐）")
    print("="*60 + "\n")
    
    agent = Agent(
        name="StandardAgent",
        role=AgentRole.ARCHITECT,
        instructions="你是一个软件架构师，擅长设计和实现高质量代码"
    )
    
    # 创建标准统一 Agent
    unified = create_unified_agent(
        agent=agent,
        mode="standard",
        verbose=True
    )
    
    print("标准模式启用功能:")
    for module in unified._get_used_modules():
        print(f"  ✅ {module}")
    
    # 执行多个任务
    tasks = [
        "设计一个用户认证系统",
        "实现一个日志记录模块",
    ]
    
    for task in tasks:
        print(f"\n执行任务: {task}")
        result = await unified.execute(task=task)
        print(f"  结果: {'✅ 成功' if result['success'] else '❌ 失败'}")
    
    # 查看统计
    stats = unified.get_stats()
    print(f"\n执行统计:")
    print(f"  总任务: {stats['total_executions']}")
    print(f"  成功: {stats['successful']}")
    print(f"  成功率: {stats['success_rate']:.1%}")


async def example_3_full_agent():
    """示例3: 完整 Agent（所有功能）"""
    print("\n" + "="*60)
    print("示例3: 完整 Agent 模式（所有功能）")
    print("="*60 + "\n")
    
    agent = Agent(
        name="FullAgent",
        role=AgentRole.DEVELOPER,
        instructions="你是一个全栈开发专家"
    )
    
    # 创建完整统一 Agent
    unified = create_unified_agent(
        agent=agent,
        mode="full",
        verbose=True
    )
    
    print("完整模式启用功能:")
    print(f"  模块: {', '.join(unified._get_used_modules())}")
    
    # 执行复杂任务
    result = await unified.execute(
        task="创建一个完整的 REST API 项目结构",
        context={
            "language": "Python",
            "framework": "FastAPI",
            "features": ["auth", "crud", "logging"]
        }
    )
    
    print(f"\n执行完成!")
    print(f"  成功: {result['success']}")
    print(f"  耗时: {result['execution_time']:.2f}s")
    
    if 'reflection' in result:
        reflection = result['reflection']
        print(f"  自反思评分: {reflection['score']}")


async def example_4_custom_config():
    """示例4: 自定义配置"""
    print("\n" + "="*60)
    print("示例4: 自定义配置")
    print("="*60 + "\n")
    
    # 创建自定义配置
    config = UnifiedAgentConfig(
        enable_reflection=True,
        enable_memory=True,
        enable_guardrails=True,
        enable_hitl=True,
        enable_optimizer=True,  # 启用优化器
        enable_chaining=False,  # 禁用提示链
        reflection_config=ReflectionConfig(
            max_iterations=2,
            min_score=85.0
        ),
        memory_config=MemoryConfig(
            backend="sqlite",
            auto_promote=True
        ),
        hitl_config=HITLConfig(
            mode=HITLMode.AUTO,
            trigger_on_dangerous_code=True
        ),
        verbose=True
    )
    
    agent = Agent(name="CustomAgent", role=AgentRole.DEVELOPER)
    unified = UnifiedAgent(agent, config)
    
    print("自定义配置:")
    print(f"  最大迭代: {config.max_iterations}")
    print(f"  自反思阈值: {config.reflection_config.min_score}")
    print(f"  记忆后端: {config.memory_config.backend}")
    print(f"  HITL 模式: {config.hitl_config.mode.value}")
    
    result = await unified.execute(
        task="优化以下代码的性能",
        context={"code": "def slow_func(): pass"}
    )
    
    print(f"\n执行结果: {result['success']}")


async def example_5_performance_monitoring():
    """示例5: 性能监控"""
    print("\n" + "="*60)
    print("示例5: 性能监控")
    print("="*60 + "\n")
    
    from code_gen.agents import performance_monitor
    
    agent = Agent(name="PerfAgent", role=AgentRole.DEVELOPER)
    unified = create_unified_agent(agent, mode="standard")
    
    # 执行任务并监控性能
    with performance_monitor.track("batch_execution", task_count=3):
        for i in range(3):
            await unified.execute(task=f"任务 {i+1}")
    
    # 获取性能报告
    summary = performance_monitor.get_summary()
    print("性能监控报告:")
    print(f"  总操作: {summary['total_operations']}")
    print(f"  成功率: {summary['success_rate']:.1%}")
    print(f"  平均耗时: {summary['avg_duration']:.2f}s")
    
    if 'by_operation' in summary:
        print("\n按操作统计:")
        for op, stats in summary['by_operation'].items():
            print(f"  {op}:")
            print(f"    次数: {stats['count']}")
            print(f"    平均: {stats['avg_duration']:.2f}s")


async def example_6_with_timing():
    """示例6: 使用计时装饰器"""
    print("\n" + "="*60)
    print("示例6: 计时装饰器")
    print("="*60 + "\n")
    
    @timing_decorator("custom_task")
    async def custom_task():
        await asyncio.sleep(0.5)
        return "完成"
    
    result = await custom_task()
    print(f"任务结果: {result}")


async def example_7_id_generation():
    """示例7: ID 生成工具"""
    print("\n" + "="*60)
    print("示例7: ID 生成工具")
    print("="*60 + "\n")
    
    # 生成不同类型的 ID
    ids = {
        "任务": generate_id("task_"),
        "会话": generate_id("session_"),
        "记忆": generate_id("mem_"),
        "日志": generate_id("log_")
    }
    
    print("生成的 ID:")
    for name, id_val in ids.items():
        print(f"  {name}: {id_val}")


async def example_8_comparison():
    """示例8: 三种模式对比"""
    print("\n" + "="*60)
    print("示例8: 三种模式对比")
    print("="*60 + "\n")
    
    agent = Agent(name="CompareAgent", role=AgentRole.DEVELOPER)
    
    modes = ["minimal", "standard", "full"]
    results = {}
    
    for mode in modes:
        unified = create_unified_agent(agent, mode=mode)
        
        start = asyncio.get_event_loop().time()
        result = await unified.execute(task="简单计算任务")
        duration = asyncio.get_event_loop().time() - start
        
        results[mode] = {
            "modules": len(unified._get_used_modules()),
            "duration": duration,
            "success": result['success']
        }
    
    print("模式对比:")
    print(f"{'模式':<10} {'模块数':<8} {'耗时':<10} {'状态'}")
    print("-" * 40)
    for mode, data in results.items():
        status = "✅" if data['success'] else "❌"
        print(f"{mode:<10} {data['modules']:<8} {data['duration']:.2f}s{'':<6} {status}")
    
    print("\n建议:")
    print("  • minimal: 快速任务、资源受限环境")
    print("  • standard: 生产环境推荐（平衡）")
    print("  • full: 复杂任务、高质量要求")


async def main():
    """运行所有示例"""
    print("\n" + "🚀"*30)
    print("Unified Agent (统一智能体) 示例")
    print("整合所有 PraisonAI 功能")
    print("🚀"*30)
    
    await example_1_minimal_agent()
    await example_2_standard_agent()
    await example_3_full_agent()
    await example_4_custom_config()
    await example_5_performance_monitoring()
    await example_6_with_timing()
    await example_7_id_generation()
    await example_8_comparison()
    
    print("\n" + "="*60)
    print("所有示例完成!")
    print("="*60)
    print("\n推荐:")
    print("  • 开发测试: 使用 minimal 模式")
    print("  • 生产环境: 使用 standard 模式")
    print("  • 复杂任务: 使用 full 模式")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
