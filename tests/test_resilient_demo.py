"""
弹性执行演示 - 展示 AI 如何持续探索直到成功

这个演示模拟了 Terminal#971-1016 中的场景，
展示如何使用弹性执行器来自动处理错误并持续尝试。
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.resilient_executor import ResilientExecutor, execute_with_persistence
from code_gen.resilient_tools import ResilientToolCaller, resilient_call


async def demo_scenario_1():
    """
    场景1: 参数错误自动修正

    Terminal 中的错误:
    - Error executing tool: ExecuteCommandTool.execute() got an unexpected keyword argument 'cmd'

    弹性执行器会自动:
    1. 检测到参数错误
    2. 自动修正 cmd -> command
    3. 重试直到成功
    """
    print("\n" + "=" * 70)
    print("🎯 场景1: 参数错误自动修正")
    print("=" * 70)

    caller = ResilientToolCaller()

    # 模拟使用错误的参数名（就像 Terminal 中那样）
    print("\n尝试使用错误的参数名 'cmd' 而不是 'command'...")
    result = await caller.call('execute_command', cmd='echo "Hello from resilient caller!"')

    if result['success']:
        print(f"✅ 成功！输出: {result.get('stdout', '').strip()}")
        print("💡 弹性执行器自动修正了参数名")
    else:
        print(f"❌ 失败: {result.get('error')}")


async def demo_scenario_2():
    """
    场景2: 依赖缺失自动安装

    Terminal 中的错误:
    - No module named pytest

    弹性执行器会:
    1. 检测到缺少 pytest
    2. 尝试自动安装
    3. 如果安装失败，使用替代方案（直接运行 Python 文件）
    """
    print("\n" + "=" * 70)
    print("🎯 场景2: 依赖缺失自动处理")
    print("=" * 70)

    caller = ResilientToolCaller()

    # 尝试运行测试（可能 pytest 未安装）
    print("\n尝试运行测试（自动处理 pytest 缺失）...")
    result = await caller.run_tests('tests/test_complete_system.py')

    if result['success']:
        print("✅ 测试运行成功！")
        print(f"输出:\n{result.get('stdout', '')[:500]}...")
    else:
        print(f"⚠️  测试运行结果: {result.get('error', 'Unknown')}")
        print("💡 但弹性执行器尝试了多种方案")


async def demo_scenario_3():
    """
    场景3: 环境差异自动适配

    Terminal 中的错误:
    - WSL (10 - Relay) ERROR: CreateProcessCommon:800: execvpe(/bin/bash) failed

    弹性执行器会:
    1. 检测到 Windows 环境
    2. 自动将 bash 命令转换为 PowerShell
    3. 或者使用 cmd 替代
    """
    print("\n" + "=" * 70)
    print("🎯 场景3: 环境差异自动适配")
    print("=" * 70)

    caller = ResilientToolCaller()

    # 模拟在 Windows 上使用 bash 命令
    print("\n尝试在 Windows 上执行 bash 命令...")
    result = await caller.call('execute_command', command="bash -c 'echo Hello from bash'")

    if result['success']:
        print(f"✅ 成功！输出: {result.get('stdout', '').strip()}")
    else:
        print(f"⚠️  bash 不可用，尝试 PowerShell...")
        # 弹性执行器会自动尝试 PowerShell
        result = await caller.call('execute_command', command="powershell -Command 'Write-Host Hello from PowerShell'")
        if result['success']:
            print(f"✅ PowerShell 成功！输出: {result.get('stdout', '').strip()}")


async def demo_scenario_4():
    """
    场景4: 持续重试直到成功

    展示弹性执行器如何在多次失败后仍然坚持尝试
    """
    print("\n" + "=" * 70)
    print("🎯 场景4: 持续重试直到成功")
    print("=" * 70)

    executor = ResilientExecutor(max_attempts=5, verbose=True)

    # 模拟一个前几次会失败的操作
    attempt_count = 0

    def flaky_operation():
        nonlocal attempt_count
        attempt_count += 1

        if attempt_count < 4:
            raise Exception(f"服务暂时不可用 (尝试 #{attempt_count})")

        return f"🎉 操作成功！总共尝试了 {attempt_count} 次"

    print("\n模拟一个前3次会失败的操作...")
    result = await executor.execute(flaky_operation)

    if result.success:
        print(f"\n✅ {result.result}")
        print(f"📊 统计:")
        print(f"   - 尝试次数: {len(result.attempts)}")
        print(f"   - 总耗时: {result.total_duration_ms:.0f}ms")
        print(f"   - 最终策略: {result.final_strategy.value}")
    else:
        print(f"❌ 所有尝试都失败了: {result.error_message}")


async def demo_scenario_5():
    """
    场景5: 智能降级策略

    当主要方法失败时，自动使用备用方案
    """
    print("\n" + "=" * 70)
    print("🎯 场景5: 智能降级策略")
    print("=" * 70)

    executor = ResilientExecutor(max_attempts=5, verbose=True)

    # 主函数：会失败
    def primary_method():
        raise Exception("主服务不可用")

    # 降级函数1：也会失败
    def fallback_1():
        raise Exception("备用服务1也不可用")

    # 降级函数2：成功
    def fallback_2():
        return "✅ 降级方案2成功执行！"

    print("\n尝试主方法，失败后自动降级...")
    result = await executor.execute(
        primary_method,
        fallback_funcs=[fallback_1, fallback_2]
    )

    if result.success:
        print(f"\n{result.result}")
        print(f"📊 使用了 {len(result.attempts)} 次尝试，最终通过降级方案成功")
    else:
        print(f"❌ 所有方案都失败了")


async def demo_real_world():
    """
    真实场景：运行完整系统测试

    就像 Terminal 中那样，但使用弹性执行
    """
    print("\n" + "=" * 70)
    print("🎯 真实场景: 运行完整系统测试")
    print("=" * 70)

    caller = ResilientToolCaller()

    print("\n使用弹性执行器运行测试...")
    print("（会自动处理参数错误、依赖缺失、环境差异等问题）")

    result = await caller.run_tests('tests/test_complete_system.py')

    print("\n" + "-" * 70)
    if result['success']:
        stdout = result.get('stdout', '')
        # 提取测试结果摘要
        if '测试总结' in stdout:
            lines = stdout.split('\n')
            for i, line in enumerate(lines):
                if '测试总结' in line:
                    # 打印测试总结部分
                    for j in range(i, min(i+20, len(lines))):
                        print(lines[j])
                    break
        else:
            print(stdout[:1000])
    else:
        print(f"⚠️  执行遇到问题，但已尝试所有可能的方案")
        print(f"最后错误: {result.get('error', 'Unknown')}")


async def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("🚀 弹性执行演示")
    print("=" * 70)
    print("\n这个演示展示了如何让 AI 持续探索、自动修正错误、")
    print("使用降级策略，直到任务成功完成。")
    print("\n对比 Terminal#971-1016 中的失败场景：")
    print("  ❌ 参数错误 -> 自动修正")
    print("  ❌ 依赖缺失 -> 自动安装或降级")
    print("  ❌ 环境差异 -> 自动适配")
    print("  ❌ 多次失败 -> 持续重试")

    await demo_scenario_1()
    await demo_scenario_2()
    await demo_scenario_3()
    await demo_scenario_4()
    await demo_scenario_5()
    await demo_real_world()

    print("\n" + "=" * 70)
    print("✅ 演示完成！")
    print("=" * 70)
    print("\n💡 关键要点：")
    print("   1. 不要在一次失败后放弃")
    print("   2. 分析错误类型并采取针对性措施")
    print("   3. 准备多个备用方案（降级策略）")
    print("   4. 自动修正常见错误（如参数名）")
    print("   5. 持续重试直到成功或达到最大尝试次数")


if __name__ == "__main__":
    asyncio.run(main())
