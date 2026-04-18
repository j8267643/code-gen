"""
技能系统演示 - 展示技能匹配和执行
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.skills import SkillSystem
from code_gen.skill_executor import SkillExecutor


async def demo_skills():
    """演示技能系统"""
    print("=" * 70)
    print("技能系统演示")
    print("=" * 70)

    # 初始化
    work_dir = Path.cwd()
    skill_system = SkillSystem(work_dir)
    skill_system.load_bundled_skills()
    executor = SkillExecutor(skill_system)

    print(f"\n已加载 {len(skill_system.skills)} 个技能:")
    for name, skill in skill_system.skills.items():
        print(f"  - {name}: {skill.description}")
        print(f"    匹配模式: {skill.patterns}")

    # 测试场景
    test_cases = [
        {
            'name': '代码审查',
            'input': '请帮我 review code_gen/client.py',
            'expected_skill': 'code_review'
        },
        {
            'name': 'Git 提交',
            'input': '帮我生成 commit message',
            'expected_skill': 'git_commit'
        },
        {
            'name': '代码搜索',
            'input': 'search for OllamaClient',
            'expected_skill': 'code_search'
        },
        {
            'name': '文件读取',
            'input': 'read file README.md',
            'expected_skill': 'file_read'
        },
        {
            'name': '无匹配',
            'input': '今天天气怎么样？',
            'expected_skill': None
        }
    ]

    for test in test_cases:
        print("\n" + "-" * 70)
        print(f"测试: {test['name']}")
        print(f"输入: {test['input']}")
        print("-" * 70)

        # 匹配技能
        matching = skill_system.get_matching_skills(test['input'])

        if matching:
            print(f"匹配到 {len(matching)} 个技能:")
            for skill in matching:
                print(f"  - {skill.name}")

            # 执行技能
            print("\n执行技能...")
            results = await executor.execute_matching_skills(test['input'])

            for result in results:
                print(f"\n  [{result.status.value.upper()}] {result.skill_name}")
                if result.output:
                    print(f"  输出: {result.output[:300]}...")
                if result.error:
                    print(f"  错误: {result.error}")
                print(f"  耗时: {result.execution_time_ms:.0f}ms")
        else:
            print("没有匹配的技能")

    print("\n" + "=" * 70)
    print("演示完成!")
    print("=" * 70)
    print("\n技能系统工作流程:")
    print("1. 用户输入 -> 技能匹配 (get_matching_skills)")
    print("2. 匹配技能 -> 技能执行 (execute_skill)")
    print("3. 执行结果 -> 返回给用户")


async def test_skills_demo():
    """技能系统演示 - test_skills_demo 入口"""
    return await demo_skills()


if __name__ == "__main__":
    asyncio.run(test_skills_demo())
