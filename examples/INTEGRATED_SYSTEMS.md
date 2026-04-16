# 集成系统文档

本文档介绍项目中集成的四大核心系统：SOP、经验池、AFLOW 和 Action Node。

## 系统概览

```
┌─────────────────────────────────────────────────────────────┐
│                    集成系统架构                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   SOP 系统   │  │   经验池     │  │  AFLOW       │      │
│  │  标准作业程序 │  │  经验积累    │  │  工作流生成   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │              │
│         └─────────────────┼─────────────────┘              │
│                           │                                │
│                    ┌──────┴───────┐                       │
│                    │  Action Node │                       │
│                    │  动作标准化  │                       │
│                    └──────┬───────┘                       │
│                           │                                │
│                    ┌──────┴───────┐                       │
│                    │   统一执行   │                       │
│                    └──────────────┘                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 1. SOP 系统 (code_gen.sop)

### 核心概念

SOP (Standard Operating Procedure) 系统用于定义和管理标准作业程序，灵感来源于 MetaGPT 的 `Code = SOP(Team)` 理念。

### 主要组件

- **SOP**: 标准作业程序定义
- **SOPStep**: 步骤定义
- **SOPContext**: 执行上下文
- **SOPRegistry**: 注册表
- **SOPExecutor**: 执行器

### 使用示例

```python
from code_gen.sop import SOP, SOPStep, SOPExecutor, SOPRegistry

# 获取内置 SOP
registry = SOPRegistry()
sop = registry.get("code_generation")

# 创建执行上下文
context = sop.create_context(inputs={
    "requirement": "创建一个用户认证类"
})

# 执行 SOP
executor = SOPExecutor()
executor.register_action("write_code", my_code_handler)
result = await executor.execute(sop, context)
```

### 内置 SOP 模板

- `code_generation`: 代码生成流程
- `bug_fix`: Bug 修复流程

## 2. 经验池系统 (code_gen.exp_pool)

### 核心概念

经验池系统用于积累和复用 AI Agent 的执行经验，实现持续学习和优化。

### 主要组件

- **Experience**: 经验条目
- **ExperiencePool**: 经验池
- **ExperienceManager**: 经验管理器
- **ExperienceRetriever**: 经验检索器
- **ExperienceScorer**: 经验评分器

### 使用示例

```python
from code_gen.exp_pool import ExperienceManager, ExperienceType

# 创建管理器
manager = ExperienceManager()

# 收集经验
exp = manager.collect_from_execution(
    task_description="修复登录 Bug",
    task_type=ExperienceType.BUG_FIX,
    input_context={"bug": "密码验证失败"},
    output_result={"fix": "修复哈希比较"},
    steps=[{"action": "analyze"}, {"action": "fix"}],
    success=True,
    lessons=["使用恒定时间比较"],
)

# 检索经验
results = manager.retrieve_experiences(
    query="密码验证",
    exp_type=ExperienceType.BUG_FIX,
    limit=3,
)

# 增强提示
augmented_prompt = manager.augment_prompt(
    base_prompt="修复以下 Bug...",
    task_description="密码验证问题",
    task_type=ExperienceType.BUG_FIX,
)
```

## 3. AFLOW 系统 (code_gen.aflow)

### 核心概念

AFLOW (Automated Workflow Generation) 用于自动生成和优化工作流，灵感来源于 MetaGPT 的 AFLOW (ICLR 2025 Oral)。

### 主要组件

- **WorkflowGraph**: 工作流图
- **WorkflowNode**: 工作流节点
- **WorkflowEdge**: 工作流边
- **WorkflowOptimizer**: 工作流优化器
- **WorkflowSearcher**: 工作流搜索器

### 使用示例

```python
from code_gen.aflow import (
    WorkflowTemplates,
    WorkflowOptimizer,
    SimpleEvaluator,
)

# 使用模板创建工作流
workflow = WorkflowTemplates.sequential([
    "analyze_requirements",
    "write_code",
    "review_code",
])

# 评估工作流
evaluator = SimpleEvaluator()
result = evaluator.quick_evaluate(workflow)
print(f"评分: {result.score}")

# 优化工作流
optimizer = WorkflowOptimizer()
optimized = await optimizer.optimize(workflow, goal="balanced")

# 分析瓶颈
bottlenecks = optimizer.analyze_bottlenecks(workflow)
suggestions = optimizer.suggest_improvements(workflow)
```

### 优化目标

- `speed`: 优化执行速度
- `quality`: 优化输出质量
- `cost`: 优化成本
- `balanced`: 平衡优化

## 4. Action Node 系统 (code_gen.action_node)

### 核心概念

Action Node 系统用于标准化 AI Agent 的动作定义，包含输入输出模式、提示模板等。

### 主要组件

- **ActionNode**: 动作节点
- **FieldDefinition**: 字段定义
- **ActionExecutor**: 动作执行器
- **ActionChain**: 动作链
- **ActionPipeline**: 动作管道

### 使用示例

```python
from code_gen.action_node import (
    ActionNode,
    FieldDefinition,
    ActionExecutor,
    ActionChain,
    ActionTemplates,
)

# 使用模板
action = ActionTemplates.code_generation()

# 创建自定义动作
action = ActionNode(
    name="my_action",
    description="My custom action",
    instruction="Do something...",
    input_fields=[
        FieldDefinition(name="input", field_type=str, required=True),
    ],
    output_fields=[
        FieldDefinition(name="output", field_type=str, required=True),
    ],
)

# 执行动作
executor = ActionExecutor(llm_client=my_client)
result = await executor.execute(action, {"input": "test"})

# 动作链
chain = ActionChain(executor)
chain.add_action(action1)
chain.add_action(action2)
result = await chain.execute({"input": "test"})
```

## 系统集成

### 组合使用示例

```python
# 1. 使用经验池增强 SOP
manager = ExperienceManager()
experiences = manager.get_relevant_experiences_for_task(
    task_description="设计类",
    task_type=ExperienceType.CODE_GENERATION,
)

# 2. 使用 Action Node 定义 SOP 步骤
analyze_action = ActionNode(...)
code_action = ActionNode(...)

# 3. 使用 AFLOW 优化工作流
workflow = WorkflowTemplates.sequential([...])
optimizer = WorkflowOptimizer()
optimized = await optimizer.optimize(workflow)

# 4. 使用 Action Node 执行工作流
executor = ActionExecutor()
for step in optimized.steps:
    result = await executor.execute(step.action, context)
```

## 运行演示

```bash
# 运行集成演示
python examples/integrated_system_demo.py
```

## 目录结构

```
code_gen/
├── sop/                    # SOP 系统
│   ├── __init__.py
│   ├── sop.py             # 核心实现
│   ├── registry.py        # 注册表
│   └── executor.py        # 执行器
├── exp_pool/               # 经验池系统
│   ├── __init__.py
│   ├── experience.py      # 经验模型
│   ├── pool.py            # 经验池
│   ├── manager.py         # 管理器
│   ├── retriever.py       # 检索器
│   └── scorer.py          # 评分器
├── aflow/                  # AFLOW 系统
│   ├── __init__.py
│   ├── workflow.py        # 工作流图
│   ├── optimizer.py       # 优化器
│   ├── search.py          # 搜索器
│   └── evaluator.py       # 评估器
└── action_node/            # Action Node 系统
    ├── __init__.py
    ├── node.py            # 节点定义
    ├── parser.py          # 输出解析
    ├── registry.py        # 注册表
    └── executor.py        # 执行器
```

## 参考

- MetaGPT: https://github.com/geekan/MetaGPT
- AFLOW Paper: https://openreview.net/forum?id=z5uVAKwmjf
