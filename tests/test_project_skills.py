"""
测试项目特定技能加载
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.skills import SkillSystem


def test_project_skills():
    """测试加载 .code_gen/skills 目录下的技能"""
    print("=" * 70)
    print("测试项目特定技能加载")
    print("=" * 70)

    work_dir = Path.cwd()
    skill_system = SkillSystem(work_dir)

    # 只加载项目特定技能
    print("\n1. 加载项目特定技能 (.code_gen/skills)...")
    skill_system.load_project_skills()

    print(f"\n加载的技能数: {len(skill_system.skills)}")

    if skill_system.skills:
        print("\n技能列表:")
        for name, skill in skill_system.skills.items():
            print(f"  - {name}")
            print(f"    描述: {skill.description}")
            print(f"    路径: {skill.path}")
            print(f"    来源: {skill.source}")
            print()
    else:
        print("\n没有加载到技能，检查目录结构...")
        skills_dir = work_dir / ".code_gen" / "skills"
        if skills_dir.exists():
            print(f"\n目录存在: {skills_dir}")
            print("子目录:")
            for item in skills_dir.iterdir():
                if item.is_dir():
                    skill_file = item / "SKILL.md"
                    print(f"  - {item.name}/")
                    print(f"    SKILL.md 存在: {skill_file.exists()}")
        else:
            print(f"\n目录不存在: {skills_dir}")

    # 测试完整加载
    print("\n" + "=" * 70)
    print("2. 测试完整技能加载 (load_skills)...")
    print("=" * 70)

    skill_system2 = SkillSystem(work_dir)
    skill_system2.load_skills()

    print(f"\n总技能数: {len(skill_system2.skills)}")

    # 分类统计
    bundled = [s for s in skill_system2.skills.values() if s.source == "bundled"]
    local = [s for s in skill_system2.skills.values() if s.source == "local"]

    print(f"  - 内置技能: {len(bundled)}")
    for s in bundled:
        print(f"    * {s.name}")

    print(f"  - 项目技能: {len(local)}")
    for s in local:
        print(f"    * {s.name}")


if __name__ == "__main__":
    test_project_skills()
