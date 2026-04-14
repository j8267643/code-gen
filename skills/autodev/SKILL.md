---
name: autodev
description: "使用 AutoDev 自主开发系统执行开发任务。触发词: '用 autodev 执行', '开始自主开发', '自动执行 prd', 'autodev run'。"
user-invocable: true
---

# AutoDev 技能

使用 Code-Gen 框架的 AutoDev 集成来执行自主开发任务。

## 功能

1. **创建 PRD** - 生成产品需求文档模板
2. **转换 PRD** - 将 Markdown PRD 转换为可执行格式
3. **执行循环** - 自动执行所有用户故事
4. **进度跟踪** - 记录执行进度和学习点

## 使用方式

### 1. 创建 PRD

```
用 autodev 创建一个 prd，功能是：[功能描述]
```

### 2. 转换 PRD

```
转换这个 prd 到 autodev 格式: [prd 文件路径]
```

### 3. 执行

```
用 autodev 执行这个 prd
```

或

```
开始 autodev 执行循环
```

### 4. 查看状态

```
查看 autodev 执行状态
```

## 工作流程

1. **初始化**: `code-gen autodev init`
2. **创建 PRD**: `code-gen autodev prd "功能描述"`
3. **编辑 PRD**: 手动编辑生成的 Markdown 文件
4. **转换**: `code-gen autodev convert tasks/prd-xxx.md`
5. **执行**: `code-gen autodev run`
6. **查看进度**: `code-gen autodev status`

## PRD 格式

PRD 应该包含:
- 项目概述
- 明确的目标
- 用户故事（带验收标准）
- 技术方案
- 非功能需求

## 用户故事格式

```markdown
### US-001: [标题]
**描述**: 作为 [角色], 我想要 [功能], 以便 [价值]

**验收标准**:
- [ ] 标准 1
- [ ] 标准 2
- [ ] 类型检查通过
- [ ] 测试通过

**优先级**: 1
```

## 集成特性

- ✅ 与 UnifiedAgent 集成
- ✅ 自动 Git 提交
- ✅ 进度跟踪 (progress.txt)
- ✅ 代码库模式学习
- ✅ 任务路由和分类
- ✅ 复杂度评估
- ✅ 失败恢复
