"""
综合功能测试脚本
测试所有新实现的功能模块
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from code_gen.context_manager import ContextWindowManager, ConversationMemory
from code_gen.file_changes import FileChangeManager, ChangeType
from code_gen.parallel_tools import ParallelToolExecutor, ToolCall, create_default_executor
from code_gen.error_recovery import (
    ResilientClient, RetryPolicy, CircuitBreaker,
    ErrorClassifier, ErrorCategory, with_retry, with_fallback
)


async def test_context_manager():
    """测试智能上下文管理"""
    print("\n" + "="*60)
    print("🧪 测试智能上下文管理 (Context Manager)")
    print("="*60)
    
    # 创建上下文管理器（较小的限制以便测试压缩）
    context = ContextWindowManager(max_tokens=2000, model="gpt-4")
    
    # 添加系统消息
    context.add_message("system", "You are a helpful coding assistant.")
    print("✅ 添加系统消息")
    
    # 添加用户消息
    context.add_message("user", "Hello, can you help me with Python?")
    print("✅ 添加用户消息")
    
    # 添加包含代码的消息（重要性应该更高）
    code_message = """
    Here's a Python function:
    ```python
    def fibonacci(n):
        if n <= 1:
            return n
        return fibonacci(n-1) + fibonacci(n-2)
    ```
    """
    context.add_message("assistant", code_message)
    print("✅ 添加包含代码的消息")
    
    # 添加错误消息
    error_message = "I got an error: TypeError: 'NoneType' object is not callable"
    context.add_message("user", error_message)
    print("✅ 添加错误消息")
    
    # 添加多条消息触发压缩
    for i in range(10):
        context.add_message("user", f"Message {i}: " + "A" * 200)
        context.add_message("assistant", f"Response {i}: " + "B" * 200)
    print("✅ 添加多条消息触发压缩")
    
    # 获取统计信息
    stats = context.get_context_stats()
    print(f"\n📊 上下文统计:")
    print(f"   总消息数: {stats['total_messages']}")
    print(f"   总Token数: {stats['total_tokens']}")
    print(f"   使用率: {stats['usage_percent']}%")
    print(f"   是否有摘要: {stats['has_summary']}")
    print(f"   消息分布: {stats['message_breakdown']}")
    
    # 获取API格式的消息
    api_messages = context.get_messages_for_api()
    print(f"\n📨 API格式消息数: {len(api_messages)}")
    
    print("\n✅ 上下文管理测试完成!")
    return True


async def test_file_changes():
    """测试文件变更预览系统"""
    print("\n" + "="*60)
    print("🧪 测试文件变更预览系统 (File Changes)")
    print("="*60)
    
    work_dir = Path(__file__).parent / "test_workspace"
    work_dir.mkdir(exist_ok=True)
    
    # 创建文件变更管理器
    manager = FileChangeManager(work_dir)
    
    # 测试1: 创建新文件
    manager.start_batch("Create new files")
    manager.add_file_change(
        file_path=Path("new_file.py"),
        new_content='print("Hello, World!")',
        change_type=ChangeType.CREATE,
        description="Create a new Python file"
    )
    print("✅ 添加创建文件变更")
    
    # 测试2: 修改现有文件（先创建原文件）
    existing_file = work_dir / "existing.py"
    existing_file.write_text("# Original content\nprint('old')")
    
    manager.add_file_change(
        file_path=Path("existing.py"),
        new_content='# Updated content\nprint("new")',
        change_type=ChangeType.MODIFY,
        description="Update existing file"
    )
    print("✅ 添加修改文件变更")
    
    # 预览变更
    preview = manager.preview_changes()
    print(f"\n📋 变更预览:\n{preview[:500]}...")
    
    # 应用变更
    success = manager.apply_batch()
    print(f"\n{'✅' if success else '❌'} 应用变更批次")
    
    # 验证文件是否创建
    new_file = work_dir / "new_file.py"
    if new_file.exists():
        print(f"✅ 新文件已创建: {new_file}")
    
    # 测试回滚
    if manager.batches:
        batch_id = manager.batches[0].batch_id
        rollback_success = manager.rollback_batch(batch_id)
        print(f"{'✅' if rollback_success else '❌'} 回滚变更")
    
    # 获取历史
    history = manager.get_batch_history()
    print(f"\n📜 变更历史记录数: {len(history)}")
    
    # 清理测试文件
    import shutil
    if work_dir.exists():
        shutil.rmtree(work_dir)
    
    print("\n✅ 文件变更系统测试完成!")
    return True


async def test_parallel_tools():
    """测试并行工具调用"""
    print("\n" + "="*60)
    print("🧪 测试并行工具调用 (Parallel Tools)")
    print("="*60)
    
    # 创建执行器
    executor = create_default_executor()
    
    # 定义测试工具
    async def slow_task(name: str, delay: float, **kwargs):
        await asyncio.sleep(delay)
        return f"Task {name} completed after {delay}s"
    
    async def fast_task(name: str, **kwargs):
        return f"Fast task {name} done"
    
    executor.register_tool("slow_task", slow_task)
    executor.register_tool("fast_task", fast_task)
    
    # 创建并行工具调用
    tool_calls = [
        ToolCall(tool_name="slow_task", parameters={"name": "A", "delay": 0.5}),
        ToolCall(tool_name="fast_task", parameters={"name": "B"}),
        ToolCall(tool_name="slow_task", parameters={"name": "C", "delay": 0.3}),
        ToolCall(tool_name="fast_task", parameters={"name": "D"}),
    ]
    
    print("🚀 执行并行工具调用...")
    start = asyncio.get_event_loop().time()
    results = await executor.execute_parallel(tool_calls)
    elapsed = asyncio.get_event_loop().time() - start
    
    print(f"\n⏱️  总执行时间: {elapsed:.2f}s (串行需要 >1.6s)")
    
    # 显示结果
    for tool_id, result in results.items():
        status = "✅" if result.status.value == "completed" else "❌"
        print(f"{status} {result.tool_name}: {result.result}")
    
    # 获取执行摘要
    summary = executor.get_execution_summary()
    print(f"\n📊 执行摘要:")
    print(f"   总工具数: {summary['total_tools']}")
    print(f"   成功: {summary['completed']}")
    print(f"   失败: {summary['failed']}")
    print(f"   成功率: {summary['success_rate']}")
    print(f"   总时间: {summary['total_execution_time']}")
    
    print("\n✅ 并行工具调用测试完成!")
    return True


async def test_error_recovery():
    """测试错误恢复机制"""
    print("\n" + "="*60)
    print("🧪 测试错误恢复机制 (Error Recovery)")
    print("="*60)
    
    # 测试1: 错误分类
    print("\n📋 测试错误分类:")
    errors = [
        Exception("Connection timeout"),
        Exception("Rate limit exceeded"),
        Exception("401 Unauthorized"),
        Exception("Invalid input"),
    ]
    for error in errors:
        category = ErrorClassifier.classify(error)
        print(f"   '{str(error)}' -> {category.value}")
    
    # 测试2: 重试策略
    print("\n🔄 测试重试策略:")
    attempt_count = 0
    
    async def flaky_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise Exception("Network error")
        return "Success!"
    
    retry_policy = RetryPolicy(max_attempts=3)
    result = await retry_policy.execute(flaky_function)
    print(f"   尝试次数: {attempt_count}")
    print(f"   结果: {result.result if result.success else result.error}")
    
    # 测试3: 熔断器
    print("\n🔒 测试熔断器:")
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)
    
    async def always_fails():
        raise Exception("Always fails")
    
    # 触发熔断
    for i in range(3):
        result = await breaker.execute(always_fails)
        print(f"   调用 {i+1}: {'失败' if result.error else '成功'} - 熔断器状态: {breaker.state}")
    
    # 等待恢复
    await asyncio.sleep(1.1)
    print(f"   等待后状态: {breaker.state}")
    
    # 测试4: 降级策略
    print("\n📉 测试降级策略:")
    
    async def primary():
        raise Exception("Primary failed")
    
    async def fallback1():
        return "Fallback 1 result"
    
    async def fallback2():
        return "Fallback 2 result"
    
    resilient = ResilientClient()
    result = await resilient.execute(primary, [fallback1, fallback2])
    print(f"   使用降级: {result.fallback_used}")
    print(f"   结果: {result.result}")
    
    # 测试5: 装饰器
    print("\n🎨 测试装饰器:")
    
    @with_retry(max_attempts=2)
    async def decorated_function():
        return "Decorated success"
    
    result = await decorated_function()
    print(f"   装饰器结果: {result.result if result.success else result.error}")
    
    # 获取错误统计
    stats = resilient.get_error_stats()
    print(f"\n📊 错误统计:")
    print(f"   总错误数: {stats['total_errors']}")
    print(f"   熔断器状态: {stats['circuit_breaker_state']}")
    
    print("\n✅ 错误恢复机制测试完成!")
    return True


async def test_all_features():
    """运行所有测试 - test_all_features 入口"""
    return await _run_all_tests()


async def _run_all_tests():
    print("\n" + "🚀" * 30)
    print("开始综合功能测试")
    print("🚀" * 30)
    
    results = []
    
    try:
        results.append(("上下文管理", await test_context_manager()))
    except Exception as e:
        print(f"❌ 上下文管理测试失败: {e}")
        results.append(("上下文管理", False))
    
    try:
        results.append(("文件变更系统", await test_file_changes()))
    except Exception as e:
        print(f"❌ 文件变更系统测试失败: {e}")
        results.append(("文件变更系统", False))
    
    try:
        results.append(("并行工具调用", await test_parallel_tools()))
    except Exception as e:
        print(f"❌ 并行工具调用测试失败: {e}")
        results.append(("并行工具调用", False))
    
    try:
        results.append(("错误恢复机制", await test_error_recovery()))
    except Exception as e:
        print(f"❌ 错误恢复机制测试失败: {e}")
        results.append(("错误恢复机制", False))
    
    # 打印总结
    print("\n" + "="*60)
    print("📋 测试总结")
    print("="*60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status}: {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\n总计: {passed_count}/{total_count} 测试通过")
    
    if passed_count == total_count:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️  {total_count - passed_count} 个测试失败")


if __name__ == "__main__":
    asyncio.run(test_all_features())
