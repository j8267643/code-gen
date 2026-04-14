"""
Git Integration Example - Git 集成示例

展示 Claude Code 风格的 Git 自动化功能
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.agents.git_integration import (
    GitIntegration,
    GitConfig,
    GitAutoCommitMode,
    create_git_integration,
    quick_commit,
    get_repo_status
)


async def example_1_basic_usage():
    """示例1: 基本使用"""
    print("\n" + "="*60)
    print("示例1: 基本使用")
    print("="*60 + "\n")
    
    # 创建 Git 集成（默认禁用自动提交）
    git = create_git_integration()
    
    print(f"自动提交模式: {git.config.auto_commit.value}")
    print(f"仓库路径: {git._repo_path}")
    
    # 查看状态
    print("\n仓库状态:")
    status = git.get_status_parsed()
    print(f"  已暂存: {len(status.get('staged', []))} 个文件")
    print(f"  未暂存: {len(status.get('unstaged', []))} 个文件")
    print(f"  未跟踪: {len(status.get('untracked', []))} 个文件")


async def example_2_auto_commit_modes():
    """示例2: 自动提交模式对比"""
    print("\n" + "="*60)
    print("示例2: 自动提交模式")
    print("="*60 + "\n")
    
    modes = [
        GitAutoCommitMode.DISABLED,
        GitAutoCommitMode.MANUAL,
        GitAutoCommitMode.ON_SUCCESS,
        GitAutoCommitMode.EVERY_TURN
    ]
    
    print("可用模式:")
    for mode in modes:
        git = create_git_integration(auto_commit=mode.value)
        should_commit = git.should_auto_commit(operation_success=True)
        print(f"  {mode.value:<15} - 操作成功时自动提交: {'✅' if should_commit else '❌'}")
    
    print("\n推荐配置:")
    print("  • disabled: 开发测试（默认）")
    print("  • manual: 需要审查的生产环境")
    print("  • on_success: 自动化任务")
    print("  • every_turn: 完整审计追踪")


async def example_3_manual_git_operations():
    """示例3: 手动 Git 操作"""
    print("\n" + "="*60)
    print("示例3: 手动 Git 操作")
    print("="*60 + "\n")
    
    git = create_git_integration()
    
    # 查看状态
    print("1. 查看状态:")
    result = git.status()
    print(f"   状态: {'✅' if result.success else '❌'}")
    if result.stdout:
        print(f"   输出:\n{result.stdout[:200]}")
    
    # 查看日志
    print("\n2. 查看日志:")
    result = git.log(n=5)
    if result.success and result.stdout:
        lines = result.stdout.strip().split('\n')[:3]
        for line in lines:
            print(f"   {line}")
    
    # 查看分支
    print("\n3. 查看分支:")
    result = git.branch()
    if result.success and result.stdout:
        lines = result.stdout.strip().split('\n')[:3]
        for line in lines:
            marker = "👉" if "*" in line else "  "
            print(f"   {marker} {line.strip()}")


async def example_4_smart_commit():
    """示例4: 智能提交"""
    print("\n" + "="*60)
    print("示例4: 智能提交")
    print("="*60 + "\n")
    
    git = create_git_integration()
    
    # 生成提交信息示例
    print("自动生成提交信息示例:")
    
    # 模拟不同变更场景
    scenarios = [
        {
            "name": "单文件修改",
            "files": ["main.py"],
            "expected": "Update main.py"
        },
        {
            "name": "多文件代码变更",
            "files": ["app.py", "utils.py", "models.py"],
            "expected": "Update code (3 files)"
        },
        {
            "name": "配置文件更新",
            "files": ["config.yaml", "settings.json"],
            "expected": "Update config (2 files)"
        },
        {
            "name": "混合变更",
            "files": ["app.py", "README.md", "config.yaml"],
            "expected": "Update code, config, docs (3 files)"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n  场景: {scenario['name']}")
        print(f"  文件: {', '.join(scenario['files'])}")
        print(f"  预期: {scenario['expected']}")


async def example_5_conversational_git():
    """示例5: 对话式 Git 操作"""
    print("\n" + "="*60)
    print("示例5: 对话式 Git 操作")
    print("="*60 + "\n")
    
    git = create_git_integration()
    
    commands = [
        "查看当前状态",
        "显示最近的提交日志",
        "提交所有更改",
        "查看文件差异",
        "切换到 main 分支",
        "创建新分支 feature-x"
    ]
    
    print("支持的对话式命令:")
    for cmd in commands:
        print(f"  💬 \"{cmd}\"")
    
    print("\n示例执行:")
    for cmd in commands[:3]:
        print(f"\n  > {cmd}")
        result = git.execute_git_command(cmd)
        print(f"  操作: {result.operation}")
        print(f"  状态: {result.status.value}")


async def example_6_auto_commit_workflow():
    """示例6: 自动提交工作流"""
    print("\n" + "="*60)
    print("示例6: 自动提交工作流")
    print("="*60 + "\n")
    
    # 启用自动提交
    config = GitConfig(
        auto_commit=GitAutoCommitMode.ON_SUCCESS,
        auto_generate_message=True,
        archive_every_turn=True
    )
    git = GitIntegration(config)
    
    print("配置:")
    print(f"  自动提交: {config.auto_commit.value}")
    print(f"  自动生成消息: {config.auto_generate_message}")
    print(f"  每轮存档: {config.archive_every_turn}")
    
    # 模拟多轮操作
    print("\n模拟多轮操作:")
    for turn in range(1, 4):
        print(f"\n  第 {turn} 轮:")
        
        # 模拟操作
        operation_success = True
        
        # 检查是否应该自动提交
        if git.should_auto_commit(operation_success, turn):
            print(f"    ✅ 触发自动提交")
            # 实际提交（这里只是演示）
            print(f"    📝 提交信息: [Auto] Turn {turn} updates")
        else:
            print(f"    ⏭️ 跳过自动提交")


async def example_7_configuration_options():
    """示例7: 配置选项"""
    print("\n" + "="*60)
    print("示例7: 配置选项")
    print("="*60 + "\n")
    
    # 生产环境配置
    production_config = GitConfig(
        auto_commit=GitAutoCommitMode.MANUAL,  # 手动触发
        auto_generate_message=True,
        require_clean_working_tree=True,
        allowed_operations=["status", "log", "diff"]  # 只允许查询
    )
    
    # 开发环境配置
    development_config = GitConfig(
        auto_commit=GitAutoCommitMode.ON_SUCCESS,
        auto_generate_message=True,
        archive_every_turn=False,
        allowed_operations=["status", "add", "commit", "log", "diff", "branch", "checkout"]
    )
    
    # CI/CD 配置
    cicd_config = GitConfig(
        auto_commit=GitAutoCommitMode.EVERY_TURN,
        auto_generate_message=True,
        commit_message_template="[CI] {summary}",
        archive_every_turn=True
    )
    
    configs = [
        ("生产环境", production_config),
        ("开发环境", development_config),
        ("CI/CD", cicd_config)
    ]
    
    for name, config in configs:
        print(f"\n{name}:")
        print(f"  自动提交: {config.auto_commit.value}")
        print(f"  提交模板: {config.commit_message_template}")
        print(f"  允许操作: {', '.join(config.allowed_operations[:3])}...")
        print(f"  存档: {'✅' if config.archive_every_turn else '❌'}")


async def example_8_statistics():
    """示例8: 统计信息"""
    print("\n" + "="*60)
    print("示例8: 统计信息")
    print("="*60 + "\n")
    
    git = create_git_integration()
    
    # 获取统计
    stats = git.get_stats()
    
    print("Git 统计:")
    for key, value in stats.items():
        if key != "operation_count":
            print(f"  {key}: {value}")
    
    # 变更摘要
    print("\n变更摘要:")
    summary = git.get_change_summary()
    for line in summary.split('\n'):
        print(f"  {line}")


async def example_9_quick_functions():
    """示例9: 快捷函数"""
    print("\n" + "="*60)
    print("示例9: 快捷函数")
    print("="*60 + "\n")
    
    print("快捷函数:")
    print("  1. quick_commit(message)")
    print("     快速提交，一行代码完成")
    print()
    print("  2. get_repo_status()")
    print("     获取解析后的仓库状态")
    print()
    print("  3. create_git_integration(auto_commit='on_success')")
    print("     快速创建配置好的集成")
    
    # 演示 get_repo_status
    print("\n获取仓库状态:")
    status = get_repo_status()
    print(f"  有变更: {status.get('has_changes', False)}")


async def main():
    """运行所有示例"""
    print("\n" + "🚀"*30)
    print("Git Integration (Git 集成)")
    print("Claude Code 风格的自动化版本控制")
    print("🚀"*30)
    
    await example_1_basic_usage()
    await example_2_auto_commit_modes()
    await example_3_manual_git_operations()
    await example_4_smart_commit()
    await example_5_conversational_git()
    await example_6_auto_commit_workflow()
    await example_7_configuration_options()
    await example_8_statistics()
    await example_9_quick_functions()
    
    print("\n" + "="*60)
    print("所有示例完成!")
    print("="*60)
    print("\n核心特性:")
    print("  • 自动提交（可配置，默认禁用）")
    print("  • 自动生成提交信息")
    print("  • 对话式 Git 操作")
    print("  • 多模式自动提交策略")
    print("  • 每轮存档支持")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
