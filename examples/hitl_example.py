"""
Human-in-the-loop (HITL) Example - 人机协作示例

展示 PraisonAI 风格的人机协作功能
支持配置化开关，灵活控制是否需要人工干预
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.agents import (
    HumanInTheLoop,
    HITLConfig,
    HITLMode,
    HITLResponseType,
    ConsoleHITLHandler,
    AutoHITLHandler,
    create_hitl,
    create_disabled_hitl,
    create_manual_hitl
)


async def example_1_basic_hitl():
    """示例1: 基础人机协作"""
    print("\n" + "="*60)
    print("示例1: 基础人机协作")
    print("="*60 + "\n")
    
    # 创建 HITL 管理器（默认 AUTO 模式）
    hitl = create_hitl(enabled=True, mode="auto")
    
    print(f"HITL 状态: {'启用' if hitl.is_enabled() else '禁用'}")
    print(f"当前模式: {hitl.config.mode.value}")
    
    # 模拟危险代码检测场景
    dangerous_code = """
import os
os.system('rm -rf /')
"""
    
    print("\n模拟场景: AI 生成了危险代码")
    print(f"代码:\n{dangerous_code}")
    
    # 检查是否应该触发 HITL
    should_trigger = hitl.should_trigger(
        "dangerous_code",
        {"code": dangerous_code, "detected_functions": ["os.system"]}
    )
    print(f"\n是否应该触发 HITL: {'是' if should_trigger else '否'}")
    
    if should_trigger:
        print("(在 AUTO 模式下，此场景会触发人工确认)")
        print("(运行完整示例时会显示交互界面)")


async def example_2_disabled_hitl():
    """示例2: 禁用的人机协作（自动通过）"""
    print("\n" + "="*60)
    print("示例2: 禁用的人机协作（自动通过）")
    print("="*60 + "\n")
    
    # 创建禁用的 HITL
    hitl = create_disabled_hitl()
    
    print(f"HITL 状态: {'启用' if hitl.is_enabled() else '禁用'}")
    
    # 请求审批（会自动通过）
    response = await hitl.request_approval(
        title="测试审批",
        content="这是测试内容",
        severity="high"
    )
    
    print(f"请求结果: {response.response_type.value}")
    print(f"反馈: {response.feedback}")
    print("\n✅ 禁用模式下所有请求自动通过，适合自动化场景")


async def example_3_hitl_modes():
    """示例3: 不同模式对比"""
    print("\n" + "="*60)
    print("示例3: HITL 模式对比")
    print("="*60 + "\n")
    
    modes = [
        ("DISABLED", "完全禁用，自动通过所有请求"),
        ("AUTO", "自动模式，仅在必要时触发"),
        ("MANUAL", "手动模式，所有关键操作都触发"),
        ("AUDIT", "审计模式，记录但不阻塞"),
    ]
    
    print("可用模式:")
    for mode, desc in modes:
        print(f"  - {mode}: {desc}")
    
    print("\n模式选择建议:")
    print("  • DISABLED: 开发测试、完全自动化场景")
    print("  • AUTO: 生产环境推荐（平衡安全和效率）")
    print("  • MANUAL: 高风险操作、合规要求严格场景")
    print("  • AUDIT: 需要记录但不阻塞的场景")


async def example_4_trigger_conditions():
    """示例4: 触发条件配置"""
    print("\n" + "="*60)
    print("示例4: 触发条件配置")
    print("="*60 + "\n")
    
    # 创建自定义配置的 HITL
    config = HITLConfig(
        enabled=True,
        mode=HITLMode.AUTO,
        trigger_on_dangerous_code=True,
        trigger_on_file_operations=True,
        trigger_on_low_confidence=True,
        confidence_threshold=0.7,
        trigger_on_api_cost=True,
        api_cost_threshold=5.0
    )
    
    hitl = HumanInTheLoop(config)
    
    print("触发条件测试:")
    
    # 测试各种触发条件
    test_cases = [
        ("dangerous_code", {"detected": True}, "危险代码"),
        ("file_operation", {"path": "/etc/passwd"}, "文件操作"),
        ("low_confidence", {"confidence": 0.5}, "低置信度 (0.5 < 0.7)"),
        ("low_confidence", {"confidence": 0.9}, "高置信度 (0.9 >= 0.7)"),
        ("api_cost", {"estimated_cost": 10.0}, "高 API 成本 ($10 > $5)"),
        ("api_cost", {"estimated_cost": 1.0}, "低 API 成本 ($1 <= $5)"),
    ]
    
    for trigger_type, context, desc in test_cases:
        should_trigger = hitl.should_trigger(trigger_type, context)
        status = "🔴 触发" if should_trigger else "🟢 不触发"
        print(f"  {status} {desc}")


async def example_5_auto_handler():
    """示例5: 自动处理器"""
    print("\n" + "="*60)
    print("示例5: 自动处理器")
    print("="*60 + "\n")
    
    # 创建自动处理器
    config = HITLConfig(mode=HITLMode.AUTO)
    auto_handler = AutoHITLHandler(config)
    hitl = HumanInTheLoop(config, handler=auto_handler)
    
    print("使用自动处理器（无需人工干预）:\n")
    
    # 低风险请求
    print("1. 低风险请求:")
    response = await hitl.request_approval(
        title="低风险操作",
        content="打印日志信息",
        severity="low"
    )
    print(f"   结果: {response.response_type.value}")
    print(f"   反馈: {response.feedback}")
    
    # 高风险请求
    print("\n2. 高风险请求:")
    response = await hitl.request_approval(
        title="高风险操作",
        content="删除数据库",
        severity="critical"
    )
    print(f"   结果: {response.response_type.value}")
    print(f"   反馈: {response.feedback}")


async def example_6_hitl_with_callbacks():
    """示例6: 带回调的 HITL"""
    print("\n" + "="*60)
    print("示例6: 带回调的 HITL")
    print("="*60 + "\n")
    
    # 定义回调函数
    def on_approval(request, response):
        print(f"   📋 回调: 请求 '{request.title}' 已批准")
    
    def on_rejection(request, response):
        print(f"   📋 回调: 请求 '{request.title}' 被拒绝")
    
    def on_timeout(request):
        print(f"   📋 回调: 请求 '{request.title}' 超时")
    
    # 创建带回调的配置
    config = HITLConfig(
        enabled=True,
        mode=HITLMode.DISABLED,  # 使用禁用模式演示回调
        on_approval=on_approval,
        on_rejection=on_rejection,
        on_timeout=on_timeout
    )
    
    hitl = HumanInTheLoop(config)
    
    print("自动批准触发回调:")
    await hitl.request_approval(
        title="测试回调",
        content="测试内容"
    )


async def example_7_request_history():
    """示例7: 请求历史记录"""
    print("\n" + "="*60)
    print("示例7: 请求历史记录")
    print("="*60 + "\n")
    
    hitl = create_disabled_hitl()
    
    # 发送多个请求
    print("发送多个请求...")
    for i in range(3):
        await hitl.request_approval(
            title=f"请求 {i+1}",
            content=f"内容 {i+1}"
        )
    
    # 查看历史
    history = hitl.get_history()
    print(f"\n历史记录数量: {len(history)}")
    
    for i, record in enumerate(history, 1):
        req = record["request"]
        resp = record["response"]
        print(f"  {i}. {req.title} -> {resp.response_type.value if resp else '无响应'}")
    
    # 清空历史
    hitl.clear_history()
    print(f"\n清空后历史记录: {len(hitl.get_history())}")


async def example_8_notification():
    """示例8: 通知功能"""
    print("\n" + "="*60)
    print("示例8: 通知功能")
    print("="*60 + "\n")
    
    hitl = create_hitl(enabled=True)
    
    print("发送通知（无需响应）:")
    await hitl.notify(
        title="任务完成",
        content="代码生成任务已完成，共生成 5 个文件",
        context={"files_count": 5, "duration": "30s"}
    )


async def example_9_practical_usage():
    """示例9: 实际使用场景"""
    print("\n" + "="*60)
    print("示例9: 实际使用场景（代码生成 + HITL）")
    print("="*60 + "\n")
    
    # 场景1: 完全自动化（禁用 HITL）
    print("场景1: CI/CD 流水线（完全自动化）")
    hitl_disabled = create_disabled_hitl()
    print(f"  HITL 状态: {'启用' if hitl_disabled.is_enabled() else '禁用'}")
    print("  适用: 自动化测试、夜间构建")
    
    # 场景2: 开发环境（自动模式）
    print("\n场景2: 开发环境（自动模式）")
    hitl_auto = create_hitl(mode="auto")
    print(f"  HITL 状态: {'启用' if hitl_auto.is_enabled() else '禁用'}")
    print(f"  模式: {hitl_auto.config.mode.value}")
    print("  适用: 日常开发，危险操作才提示")
    
    # 场景3: 生产环境（手动模式）
    print("\n场景3: 生产环境（手动模式）")
    hitl_manual = create_manual_hitl()
    print(f"  HITL 状态: {'启用' if hitl_manual.is_enabled() else '禁用'}")
    print(f"  模式: {hitl_manual.config.mode.value}")
    print("  适用: 生产部署，所有操作需确认")
    
    # 场景4: 审计模式
    print("\n场景4: 合规审计（审计模式）")
    hitl_audit = create_hitl(mode="audit")
    print(f"  HITL 状态: {'启用' if hitl_audit.is_enabled() else '禁用'}")
    print(f"  模式: {hitl_audit.config.mode.value}")
    print("  适用: 记录所有操作但不阻塞")


async def interactive_demo():
    """交互式演示"""
    print("\n" + "="*60)
    print("交互式演示")
    print("="*60)
    print("\n此演示将实际请求用户输入")
    print("按 Enter 开始，或输入 'skip' 跳过...")
    
    user_input = input().strip().lower()
    if user_input == 'skip':
        print("跳过交互式演示")
        return
    
    # 创建交互式 HITL
    hitl = create_hitl(enabled=True, mode="manual")
    
    print("\n场景: AI 检测到危险代码")
    response = await hitl.request_approval(
        title="危险代码检测",
        content="""
AI 生成了以下代码：

import os
result = os.system('rm -rf /important/data')

此代码将删除重要数据目录！
        """.strip(),
        severity="critical",
        trigger_reason="检测到 os.system 危险函数",
        options=["批准执行", "修改代码", "拒绝执行"]
    )
    
    print(f"\n您的选择: {response.response_type.value}")
    if response.feedback:
        print(f"反馈: {response.feedback}")
    if response.modified_content:
        print(f"修改后的内容: {response.modified_content}")


async def main():
    """运行所有示例"""
    print("\n" + "👤"*30)
    print("Human-in-the-loop (人机协作) 示例")
    print("👤"*30)
    
    await example_1_basic_hitl()
    await example_2_disabled_hitl()
    await example_3_hitl_modes()
    await example_4_trigger_conditions()
    await example_5_auto_handler()
    await example_6_hitl_with_callbacks()
    await example_7_request_history()
    await example_8_notification()
    await example_9_practical_usage()
    
    # 可选的交互式演示
    # await interactive_demo()
    
    print("\n" + "="*60)
    print("所有示例完成!")
    print("="*60)
    print("\n提示: 取消注释 interactive_demo() 可体验交互式演示")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
