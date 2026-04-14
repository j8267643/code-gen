"""
AutoDev Integration Example - 自主开发集成使用示例

展示如何使用 AutoDev 集成功能
"""
import asyncio
from pathlib import Path

from code_gen.autodev import AutoDevIntegration, AutoDevConfig
from code_gen.autodev.prd_parser import PRDParser
from code_gen.autodev.task_router import TaskRouter
from code_gen.autodev.progress_tracker import ProgressTracker


async def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("示例 1: 基本使用")
    print("=" * 60)
    
    # 配置
    config = AutoDevConfig(
        work_dir=Path("./example-project"),
        auto_commit=False,  # 演示模式，不提交
        max_iterations=10
    )
    
    # 创建 AutoDev 实例
    autodev = AutoDevIntegration(config)
    
    # 创建 PRD 模板
    prd_path = autodev.create_prd("实现用户认证系统")
    print(f"✅ 创建 PRD: {prd_path}")
    
    # 模拟 PRD 内容（实际使用时应编辑生成的文件）
    prd_content = """# PRD: 实现用户认证系统

## 概述
实现完整的用户认证系统，包括注册、登录、密码重置功能。

## 目标
- 提供安全的用户认证
- 支持邮箱验证
- 实现密码重置流程

## 用户故事

### US-001: 用户注册
**描述**: 作为新用户，我想要注册账号，以便使用系统功能。

**验收标准**:
- [ ] 用户可以通过邮箱注册
- [ ] 密码需要符合安全要求
- [ ] 注册后发送验证邮件
- [ ] 类型检查通过
- [ ] 测试通过

**优先级**: 1

### US-002: 用户登录
**描述**: 作为已注册用户，我想要登录系统，以便访问个人数据。

**验收标准**:
- [ ] 用户可以通过邮箱和密码登录
- [ ] 登录成功后返回 token
- [ ] 密码错误时返回适当错误
- [ ] 类型检查通过

**优先级**: 2

---

## 技术方案
使用 JWT 进行身份验证，密码使用 bcrypt 加密。

## 非功能需求
- 响应时间 < 200ms
- 密码加密强度符合 OWASP 标准
"""
    
    # 写入 PRD 文件
    prd_path.write_text(prd_content, encoding='utf-8')
    
    # 转换 PRD
    prd_data = autodev.convert_prd(prd_path)
    print(f"✅ 转换完成: {len(prd_data.user_stories)} 个用户故事")
    
    # 显示用户故事
    for story in prd_data.user_stories:
        print(f"  - {story['id']}: {story['title']} (优先级: {story['priority']})")
    
    return autodev


async def example_task_routing():
    """任务路由示例"""
    print("\n" + "=" * 60)
    print("示例 2: 任务路由")
    print("=" * 60)
    
    router = TaskRouter()
    
    # 测试不同的用户故事
    stories = [
        {
            "id": "US-001",
            "title": "创建登录页面",
            "description": "实现用户登录界面，包含邮箱和密码输入框",
            "acceptanceCriteria": ["UI 组件", "表单验证"],
            "priority": 1
        },
        {
            "id": "US-002",
            "title": "添加用户表",
            "description": "创建数据库表存储用户信息",
            "acceptanceCriteria": ["迁移文件", "模型定义"],
            "priority": 1
        },
        {
            "id": "US-003",
            "title": "实现登录 API",
            "description": "创建登录接口，验证用户凭证",
            "acceptanceCriteria": ["API 端点", "JWT token"],
            "priority": 2
        }
    ]
    
    for story in stories:
        result = router.route(story)
        analysis = result["analysis"]
        
        print(f"\n📋 {story['id']}: {story['title']}")
        print(f"   类别: {analysis['category']}")
        print(f"   复杂度: {analysis['complexity']}/5")
        print(f"   预计时间: {analysis['estimated_time']} 分钟")
        print(f"   推荐 Agent: {analysis['suggested_agent']}")
        print(f"   所需技能: {', '.join(analysis['required_skills'])}")


async def example_progress_tracking():
    """进度跟踪示例"""
    print("\n" + "=" * 60)
    print("示例 3: 进度跟踪")
    print("=" * 60)
    
    progress_file = Path("./example-progress.txt")
    tracker = ProgressTracker(progress_file=progress_file)
    
    # 添加执行记录
    tracker.add_entry(
        story_id="US-001",
        story_title="创建登录页面",
        status="completed",
        output="成功创建登录页面组件",
        learnings=[
            "使用 React Hook Form 进行表单处理",
            "项目使用 Tailwind CSS 进行样式"
        ],
        files_changed=["src/pages/Login.tsx", "src/components/LoginForm.tsx"]
    )
    
    tracker.add_entry(
        story_id="US-002",
        story_title="添加用户表",
        status="completed",
        output="创建用户表和迁移",
        learnings=[
            "使用 Prisma 进行数据库操作",
            "迁移文件放在 prisma/migrations/"
        ],
        files_changed=["prisma/schema.prisma", "prisma/migrations/xxx/migration.sql"]
    )
    
    # 添加代码库模式
    tracker.add_pattern(
        pattern="使用 React Hook Form",
        description="所有表单都使用 react-hook-form 库",
        category="pattern"
    )
    
    tracker.add_pattern(
        pattern="Prisma 迁移",
        description="运行 npx prisma migrate dev 创建迁移",
        category="gotcha"
    )
    
    # 生成摘要
    summary = tracker.generate_summary()
    print(summary)
    
    # 清理
    if progress_file.exists():
        progress_file.unlink()


async def example_prd_parsing():
    """PRD 解析示例"""
    print("\n" + "=" * 60)
    print("示例 4: PRD 解析")
    print("=" * 60)
    
    parser = PRDParser()
    
    # 创建示例 PRD
    prd_content = """# PRD: 实现购物车功能

## 概述
为电商网站添加购物车功能。

## 用户故事

### US-001: 添加商品到购物车
**描述**: As a shopper, I want to add items to cart so that I can purchase them later.

**验收标准**:
- [ ] 点击"添加到购物车"按钮
- [ ] 商品出现在购物车中
- [ ] 显示商品数量

**优先级**: 1

### US-002: 修改购物车数量
**描述**: As a shopper, I want to change item quantity so that I can buy the right amount.

**Acceptance Criteria**:
- [ ] Can increase quantity
- [ ] Can decrease quantity
- [ ] Cannot go below 1

**Priority**: 2
"""
    
    prd_path = Path("./example-prd.md")
    prd_path.write_text(prd_content, encoding='utf-8')
    
    # 解析
    prd_data = parser.parse(prd_path)
    
    print(f"项目: {prd_data.project}")
    print(f"分支: {prd_data.branch_name}")
    print(f"描述: {prd_data.description}")
    print(f"\n用户故事 ({len(prd_data.user_stories)} 个):")
    
    for story_data in prd_data.user_stories:
        story = story_data if isinstance(story_data, dict) else story_data.to_dict()
        print(f"\n  {story['id']}: {story['title']}")
        print(f"    描述: {story['description'][:80]}...")
        print(f"    验收标准: {len(story['acceptanceCriteria'])} 项")
        print(f"    优先级: {story['priority']}")
    
    # 清理
    prd_path.unlink()


async def main():
    """主函数"""
    print("AutoDev Integration Examples")
    print("自主开发集成使用示例\n")
    
    try:
        # 运行示例
        await example_basic_usage()
        await example_task_routing()
        await example_progress_tracking()
        await example_prd_parsing()
        
        print("\n" + "=" * 60)
        print("所有示例完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 示例失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
