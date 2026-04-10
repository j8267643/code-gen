"""
测试 Skill Executor - 验证技能执行功能
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.skills import SkillSystem, Skill
from code_gen.skill_executor import SkillExecutor, SkillResultStatus


async def test_skill_executor():
    """测试技能执行器"""
    print("=" * 60)
    print("测试 Skill Executor")
    print("=" * 60)

    # 创建工作目录
    work_dir = Path.cwd()

    # 初始化技能系统
    skill_system = SkillSystem(work_dir)
    skill_system.load_bundled_skills()

    print(f"\n已加载技能数: {len(skill_system.skills)}")
    for name, skill in skill_system.skills.items():
        print(f"  - {name}: {skill.description}")

    # 初始化技能执行器
    executor = SkillExecutor(skill_system)

    # 测试1: 代码审查技能
    print("\n" + "-" * 60)
    print("测试1: 代码审查技能")
    print("-" * 60)

    test_input = "请帮我 review 一下 main.py 的代码"
    results = await executor.execute_matching_skills(test_input)

    if results:
        for result in results:
            print(f"\n技能: {result.skill_name}")
            print(f"状态: {result.status.value}")
            print(f"输出:\n{result.output[:500]}...")
            print(f"耗时: {result.execution_time_ms:.0f}ms")
    else:
        print("没有匹配的技能")

    # 测试2: Git 提交技能
    print("\n" + "-" * 60)
    print("测试2: Git 提交技能")
    print("-" * 60)

    test_input = "帮我生成 commit message"
    results = await executor.execute_matching_skills(test_input)

    if results:
        for result in results:
            print(f"\n技能: {result.skill_name}")
            print(f"状态: {result.status.value}")
            print(f"输出:\n{result.output[:500]}...")
    else:
        print("没有匹配的技能")

    # 测试3: 代码搜索技能
    print("\n" + "-" * 60)
    print("测试3: 代码搜索技能")
    print("-" * 60)

    test_input = "search for SkillExecutor"
    results = await executor.execute_matching_skills(test_input)

    if results:
        for result in results:
            print(f"\n技能: {result.skill_name}")
            print(f"状态: {result.status.value}")
            print(f"输出:\n{result.output[:500]}...")
    else:
        print("没有匹配的技能")

    # 测试4: 文件读取技能
    print("\n" + "-" * 60)
    print("测试4: 文件读取技能")
    print("-" * 60)

    test_input = "read file code_gen/skill_executor.py"
    results = await executor.execute_matching_skills(test_input)

    if results:
        for result in results:
            print(f"\n技能: {result.skill_name}")
            print(f"状态: {result.status.value}")
            print(f"输出:\n{result.output[:500]}...")
    else:
        print("没有匹配的技能")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_skill_executor())
