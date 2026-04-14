"""
Context Window Management Example - 上下文窗口管理示例

展示 Claude Code 风格的上下文压缩功能
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.agents.context_manager import (
    ContextWindow,
    ContextManager,
    ContextBudget,
    CompressionLevel,
    MessageRole,
    create_context_window,
    compact_context
)


async def example_1_basic_usage():
    """示例1: 基本使用"""
    print("\n" + "="*60)
    print("示例1: 基本使用")
    print("="*60 + "\n")
    
    # 创建上下文窗口
    window = create_context_window(
        max_tokens=4000,
        system_prompt="你是一个专业的 Python 开发助手"
    )
    
    # 添加对话
    window.add_user_message("帮我写一个排序函数")
    window.add_assistant_message("""
这是一个快速排序的实现：

```python
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
```
""")
    
    window.add_user_message("能优化一下吗？")
    window.add_assistant_message("可以使用原地排序来优化空间复杂度...")
    
    # 查看统计
    stats = window.get_stats()
    print(f"消息数: {stats['total_messages']}")
    print(f"Token 数: {stats['total_tokens']}")
    print(f"使用率: {stats['usage_ratio']:.1%}")
    print(f"状态: {stats['status']}")


async def example_2_compression_levels():
    """示例2: 不同压缩级别对比"""
    print("\n" + "="*60)
    print("示例2: 不同压缩级别对比")
    print("="*60 + "\n")
    
    # 创建一个包含大量消息的窗口
    window = create_context_window(max_tokens=10000)
    
    # 模拟长对话
    for i in range(20):
        window.add_user_message(f"问题 {i+1}: 如何优化代码性能？")
        window.add_assistant_message(f"""
针对问题 {i+1}，我建议：
1. 使用更高效的数据结构
2. 减少不必要的循环
3. 使用缓存机制

示例代码：
```python
def optimized_function_{i}():
    # 优化后的代码
    cache = {{}}
    return cache
```
""")
    
    print(f"压缩前:")
    print(f"  消息数: {len(window.messages)}")
    print(f"  Token: {window.total_tokens}")
    
    # 测试不同压缩级别
    for level in [CompressionLevel.LIGHT, CompressionLevel.MEDIUM, 
                  CompressionLevel.HEAVY, CompressionLevel.AGGRESSIVE]:
        # 复制窗口进行测试
        test_window = ContextWindow.import_context(window.export())
        
        result = test_window.compact(level=level, preserve_recent=2)
        
        print(f"\n{level.value.upper()} 压缩:")
        print(f"  原始消息: {result['original_count']}")
        print(f"  压缩后: {result['new_count']}")
        print(f"  Token: {result['new_tokens']}")
        print(f"  压缩率: {result['compression_ratio']:.1%}")


async def example_3_budget_management():
    """示例3: 预算管理"""
    print("\n" + "="*60)
    print("示例3: 预算管理")
    print("="*60 + "\n")
    
    # 创建小预算窗口
    budget = ContextBudget(
        max_tokens=2000,
        warning_threshold=0.7,
        critical_threshold=0.9,
        reserve_tokens=200
    )
    
    window = ContextWindow(budget=budget)
    
    print(f"预算配置:")
    print(f"  最大 Token: {budget.max_tokens}")
    print(f"  有效最大: {budget.effective_max}")
    print(f"  警告阈值: {budget.warning_limit} ({budget.warning_threshold:.0%})")
    print(f"  临界阈值: {budget.critical_limit} ({budget.critical_threshold:.0%})")
    
    # 逐步添加消息，观察状态变化
    for i in range(10):
        window.add_user_message(f"这是第 {i+1} 条用户消息，包含一些内容来占用 token")
        window.add_assistant_message(f"这是第 {i+1} 条助手回复，" * 10)
        
        stats = window.get_stats()
        if stats['status'] != 'normal':
            print(f"\n第 {i+1} 轮 - 状态: {stats['status'].upper()}")
            print(f"  Token: {stats['total_tokens']}/{stats['budget']['effective']}")
            print(f"  使用率: {stats['usage_ratio']:.1%}")


async def example_4_context_manager():
    """示例4: 多窗口管理"""
    print("\n" + "="*60)
    print("示例4: 多窗口管理")
    print("="*60 + "\n")
    
    manager = ContextManager()
    
    # 创建多个窗口
    manager.create_window(
        name="feature-auth",
        system_prompt="实现用户认证功能"
    )
    
    manager.create_window(
        name="bugfix-login",
        system_prompt="修复登录问题"
    )
    
    manager.create_window(
        name="refactor-db",
        system_prompt="重构数据库层"
    )
    
    print(f"创建了 {len(manager.windows)} 个上下文窗口:")
    for name in manager.windows.keys():
        print(f"  - {name}")
    
    # 在不同窗口添加内容
    auth_window = manager.get_window("feature-auth")
    auth_window.add_user_message("设计 JWT 认证流程")
    auth_window.add_assistant_message("建议采用 access token + refresh token 方案...")
    
    # 切换窗口
    manager.switch_window("bugfix-login")
    current = manager.get_window()
    current.add_user_message("登录超时问题")
    
    print(f"\n当前活动窗口: {manager.active_window}")
    
    # 查看所有窗口统计
    print("\n所有窗口统计:")
    for name, stats in manager.get_all_stats().items():
        print(f"  {name}: {stats['total_messages']} 消息, {stats['total_tokens']} tokens")


async def example_5_compact_command():
    """示例5: /compact 命令模拟"""
    print("\n" + "="*60)
    print("示例5: /compact 命令")
    print("="*60 + "\n")
    
    window = create_context_window(max_tokens=8000)
    
    # 添加大量对话
    for i in range(15):
        window.add_user_message(f"需求 {i+1}: 添加新功能")
        window.add_assistant_message(f"""
实现方案 {i+1}:
1. 修改 models.py 添加字段
2. 更新 views.py 处理逻辑
3. 添加测试用例

代码示例：
```python
class Feature{i}(models.Model):
    name = models.CharField(max_length=100)
    enabled = models.BooleanField(default=True)
```
""")
    
    print("执行 /compact 命令...")
    print(f"压缩前: {len(window.messages)} 条消息, {window.total_tokens} tokens")
    
    # 执行压缩
    result = window.compact(level=CompressionLevel.MEDIUM, preserve_recent=2)
    
    print(f"\n压缩结果:")
    print(f"  级别: {result['level']}")
    print(f"  原始: {result['original_count']} 条")
    print(f"  压缩后: {result['new_count']} 条")
    print(f"  Token: {result['new_tokens']}")
    print(f"  压缩率: {result['compression_ratio']:.1%}")
    
    # 查看压缩后的消息
    print(f"\n压缩后的消息结构:")
    for i, msg in enumerate(window.messages):
        role = msg.role.value
        content_preview = msg.content[:60].replace('\n', ' ')
        print(f"  [{i}] {role}: {content_preview}...")


async def example_6_export_import():
    """示例6: 导出导入"""
    print("\n" + "="*60)
    print("示例6: 导出导入")
    print("="*60 + "\n")
    
    # 创建并填充窗口
    window = create_context_window(
        max_tokens=4000,
        system_prompt="系统提示"
    )
    window.add_user_message("用户问题")
    window.add_assistant_message("助手回答")
    
    # 导出
    exported = window.export()
    print("导出数据:")
    print(f"  消息数: {len(exported['messages'])}")
    print(f"  预算: {exported['budget']['max_tokens']} tokens")
    
    # 导入
    new_window = ContextWindow.import_context(exported)
    print(f"\n导入成功:")
    print(f"  消息数: {len(new_window.messages)}")
    print(f"  Token: {new_window.total_tokens}")


async def example_7_convenient_function():
    """示例7: 便捷函数"""
    print("\n" + "="*60)
    print("示例7: 便捷函数")
    print("="*60 + "\n")
    
    # 原始消息列表
    messages = [
        {"role": "user", "content": "问题1: 如何学习 Python？"},
        {"role": "assistant", "content": "建议从基础语法开始..." * 20},
        {"role": "user", "content": "问题2: 推荐什么框架？"},
        {"role": "assistant", "content": "Django 和 Flask 都不错..." * 20},
    ]
    
    print(f"原始消息: {len(messages)} 条")
    
    # 压缩
    compressed = compact_context(messages, level="heavy")
    
    print(f"压缩后: {len(compressed)} 条")
    print("\n压缩后的内容:")
    for i, msg in enumerate(compressed):
        preview = msg['content'][:80].replace('\n', ' ')
        print(f"  [{i}] {msg['role']}: {preview}...")


async def example_8_smart_compression():
    """示例8: 智能压缩策略"""
    print("\n" + "="*60)
    print("示例8: 智能压缩策略")
    print("="*60 + "\n")
    
    window = create_context_window(max_tokens=5000)
    
    # 添加不同类型的消息
    window.add_system_message("你是一个代码助手")
    
    # 添加代码（应该保留）
    window.add_user_message("帮我写个函数")
    window.add_assistant_message("""
```python
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
```
""")
    
    # 添加讨论（可以压缩）
    for i in range(5):
        window.add_user_message(f"讨论点 {i+1}: 这个实现有什么优缺点？")
        window.add_assistant_message(f"""
关于讨论点 {i+1}：
优点：
1. 代码简洁易懂
2. 数学表达清晰

缺点：
1. 时间复杂度高 O(2^n)
2. 存在重复计算

建议：使用动态规划优化
""")
    
    print("压缩前:")
    print(f"  消息: {len(window.messages)}")
    print(f"  Token: {window.total_tokens}")
    
    # 智能压缩：保留代码，压缩讨论
    result = window.compact(level=CompressionLevel.MEDIUM, preserve_recent=3)
    
    print(f"\n压缩后:")
    print(f"  消息: {len(window.messages)}")
    print(f"  Token: {window.total_tokens}")
    print(f"  压缩率: {result['compression_ratio']:.1%}")
    
    # 检查是否保留了代码
    has_code = any("```" in msg.content for msg in window.messages)
    print(f"  代码保留: {'✅' if has_code else '❌'}")


async def main():
    """运行所有示例"""
    print("\n" + "🚀"*30)
    print("Context Window Management (上下文窗口管理)")
    print("Claude Code 风格的上下文压缩")
    print("🚀"*30)
    
    await example_1_basic_usage()
    await example_2_compression_levels()
    await example_3_budget_management()
    await example_4_context_manager()
    await example_5_compact_command()
    await example_6_export_import()
    await example_7_convenient_function()
    await example_8_smart_compression()
    
    print("\n" + "="*60)
    print("所有示例完成!")
    print("="*60)
    print("\n核心特性:")
    print("  • 四层压缩级别 (light/medium/heavy/aggressive)")
    print("  • Token 预算管理")
    print("  • 自动压缩触发")
    print("  • 多窗口管理")
    print("  • 导出/导入支持")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
