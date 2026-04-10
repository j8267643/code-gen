# 技能系统使用指南

## 概述

技能系统（Skill System）允许 Code Gen 根据用户输入自动匹配并执行特定任务。

## 工作流程

```
用户输入
    ↓
技能匹配 (SkillSystem.get_matching_skills)
    ↓
技能执行 (SkillExecutor.execute_skill)
    ↓
返回结果给用户
```

## 内置技能

| 技能名称 | 描述 | 匹配模式 | 功能 |
|---------|------|---------|------|
| `code_review` | 代码审查 | "review", "review code", "analyze code" | 分析代码文件，检查长行、TODO、调试代码等 |
| `git_commit` | Git 提交 | "commit", "git commit", "commit changes" | 获取 git 状态，生成提交信息建议 |
| `code_search` | 代码搜索 | "search", "find code", "look for" | 在项目中搜索代码模式 |
| `file_read` | 文件读取 | "read", "read file", "show file", "open file" | 读取并显示文件内容 |

## 使用示例

### 在对话中使用

当用户输入匹配技能模式时，技能会自动执行：

```
用户: 请帮我 review code_gen/client.py
AI: [自动执行 code_review 技能]
    代码审查结果 (code_gen/client.py):
    - Line 80: 发现调试代码
    - Line 144: 行太长 (105 字符)
    ...

用户: 帮我生成 commit message
AI: [自动执行 git_commit 技能]
    待提交更改 (21 个文件):
    M code_gen/cli.py
    M code_gen/client.py
    ...
    提交信息建议:
    - Update Python code
    - Update 21 files

用户: search for OllamaClient
AI: [自动执行 code_search 技能]
    搜索 'OllamaClient' 的结果:
    code_gen\client.py:106
      class OllamaClient(BaseAIClient):
    ...

用户: read file README.md
AI: [自动执行 file_read 技能]
    文件内容 (README.md):
    # Code Gen - AI 编程助手 CLI
    ...
```

### 在代码中使用

```python
from code_gen.skills import SkillSystem
from code_gen.skill_executor import SkillExecutor

# 初始化
skill_system = SkillSystem(work_dir)
skill_system.load_bundled_skills()
executor = SkillExecutor(skill_system)

# 执行匹配的技能
results = await executor.execute_matching_skills("review my code")

for result in results:
    print(f"技能: {result.skill_name}")
    print(f"状态: {result.status.value}")
    print(f"输出: {result.output}")
```

## 创建自定义技能

### 方法1: 使用内置技能函数

```python
# 在 skill_executor.py 中添加
async def _skill_my_custom(self, skill: Skill, context: Dict) -> SkillResult:
    """自定义技能"""
    # 实现技能逻辑
    return SkillResult(
        skill_name=skill.name,
        status=SkillResultStatus.SUCCESS,
        output="执行结果",
        data={}
    )

# 注册技能
def _register_builtin_skills(self):
    self.builtin_skills['my_custom'] = self._skill_my_custom
```

### 方法2: 创建技能文件

```python
# 创建技能文件
skill = skill_system.create_skill(
    name="my_skill",
    description="My custom skill",
    patterns=["my keyword", "do something"],
    commands=["my_command"]
)
```

## 技能执行结果

```python
@dataclass
class SkillResult:
    skill_name: str          # 技能名称
    status: SkillResultStatus # 状态 (success/failed/partial/skipped)
    output: str              # 输出内容
    data: Dict               # 附加数据
    error: Optional[str]     # 错误信息
    execution_time_ms: float # 执行时间
```

## 集成到 App

在 `app.py` 中，技能系统已经集成：

```python
# 初始化
self.skill_system = SkillSystem(work_dir)
self.skill_system.load_skills()
self.skill_executor = SkillExecutor(self.skill_system)

# 在对话循环中使用
matching_skills = self.skill_system.get_matching_skills(user_input)
if matching_skills:
    skill_results = await self.skill_executor.execute_matching_skills(user_input)
    # 显示结果
    for result in skill_results:
        console.print(f"[Skill: {result.skill_name}]")
        console.print(result.output)
```

## 测试

```bash
# 运行技能执行器测试
python tests/test_skill_executor.py

# 运行技能系统演示
python tests/test_skills_demo.py
```

## 扩展建议

1. **添加更多内置技能**
   - 代码格式化
   - 依赖检查
   - 测试运行
   - 文档生成

2. **支持外部技能脚本**
   - Python 脚本
   - Shell 脚本
   - 可执行文件

3. **技能组合**
   - 链式执行多个技能
   - 条件执行
   - 并行执行

4. **技能学习**
   - 从用户行为学习新技能
   - 自动优化技能匹配
   - 技能推荐
