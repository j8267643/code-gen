# Code Gen - AI 编程助手 CLI

一个基于 AI 的命令行编程助手，支持多 Agent 协作，帮助开发者提高编码效率。

## 🌟 功能特性

### 核心功能

- **交互式聊天** - 与 AI 进行自然语言对话，获取代码建议和解决方案
- **代码审查** - 使用 AI 自动审查代码质量和潜在问题
- **自动生成提交信息** - 分析代码变更并生成提交信息
- **差异分析** - 获取 Git 差异的 AI 解释
- **任务管理** - 管理开发任务和进度

### 多 Agent 系统

- **多 Agent 协作** - 多个专业 Agent 协同工作，完成复杂任务
- **角色专业化** - 支持 Researcher、Architect、Builder、Validator、Tester 等角色
- **动态工作流** - Agent 自主规划执行步骤，无需预定义流程
- **YAML 工作流** - 支持通过 YAML 文件定义工作流
- **断点续跑** - 工作流失败后可从断点处恢复执行
- **工具共享** - 所有 Agent 共享工具注册器，支持工具调用

### 高级功能

- **记忆系统** - 保存用户偏好和项目知识，实现上下文感知
- **安全系统** - 检测提示注入、作用域蔓延和意外损坏
- **插件系统** - 通过插件扩展功能
- **MCP 集成** - 与 Model Context Protocol 服务器集成
- **技能系统** - 自动匹配和执行特定技能
- **成本跟踪** - 追踪 API 使用成本

## 🚀 安装和使用

### 系统要求

- Python 3.8+
- Ollama 或其他兼容的 AI 模型服务

### 安装依赖

```bash
pip install typer rich httpx
```

### 配置提供商

```bash
# 使用 Ollama (本地模型)
python -m code_gen provider ollama

# 使用 LMStudio
python -m code_gen provider lmstudio

# 使用 Anthropic API
python -m code_gen provider anthropic
```

### 运行项目

```bash
# 启动交互式聊天
python -m code_gen chat

# 查看帮助
python -m code_gen --help

# 查看版本
python -m code_gen version
```

## 🤖 多 Agent 系统使用

### 初始化工作流

```bash
# 初始化一个新的工作流
python -m code_gen workflow-init my_workflow.yaml
```

### 运行动态工作流

```bash
# 运行动态工作流（Agent 自主规划）
python -m code_gen dynamic my_workflow.yaml

# 使用特定模型
python -m code_gen dynamic my_workflow.yaml --model qwen2.5
```

### 断点续跑

```bash
# 查看可恢复的工作流
python -m code_gen workflow-resume

# 从失败处恢复特定工作流
python -m code_gen workflow-resume "工作流名称"

# 重试失败的步骤
python -m code_gen workflow-resume "工作流名称" --retry

# 重置工作流（从头开始）
python -m code_gen workflow-resume "工作流名称" --reset
```

### 工作流 YAML 示例

```yaml
name: "新功能开发"
description: "实现用户认证系统"
goal: "创建一个完整的用户认证模块，包括注册、登录、JWT token 生成"
input: "需要支持邮箱和密码注册，密码需要加密存储"
framework: "code_gen"
strategy: "adaptive"

agents:
  researcher:
    name: "技术研究员"
    role: "researcher"
    goal: "研究最佳的用户认证实现方案"
    backstory: "专注于安全性和性能的技术专家"
    
  architect:
    name: "系统架构师"
    role: "architect"
    goal: "设计用户认证系统的架构"
    backstory: "经验丰富的系统架构师，擅长设计可扩展的系统"
    
  builder:
    name: "代码构建者"
    role: "builder"
    goal: "实现用户认证系统的代码"
    backstory: "专业的 Python 开发者，注重代码质量和最佳实践"
    
  validator:
    name: "代码验证者"
    role: "validator"
    goal: "检查代码质量和安全性"
    backstory: "严格的代码审查专家，关注安全和性能"

tools:
  - read_file
  - write_file
  - list_directory
  - execute_command
```

## 📖 命令说明

| 命令 | 说明 |
|------|------|
| `chat` | 启动交互式编码会话 |
| `review [file]` | 使用 AI 审查代码文件 |
| `commit [message]` | 生成提交信息并提交更改 |
| `diff` | 显示 Git 差异和 AI 解释 |
| `tasks` | 管理开发任务 |
| `config` | 管理配置 |
| `provider [name]` | 切换 AI 提供商 |
| `login` | 认证 API |
| `logout` | 移除认证凭证 |
| `version` | 显示版本信息 |
| `dream` | 运行梦境过程提取记忆见解 |
| `security` | 安全监控 |
| `workflow-init [file]` | 初始化工作流 YAML 文件 |
| `dynamic [file]` | 运行动态工作流 |
| `workflow-resume [name]` | 恢复工作流执行 |

## 🏗️ 项目结构

```
code_gen/
├── agents/            # 多 Agent 系统
│   ├── agent.py      # Agent 定义和角色
│   ├── task.py       # 任务管理
│   ├── team.py       # Agent 团队协作
│   ├── executor.py   # Agent 执行器
│   ├── real_executor.py      # 真实 AI 执行器
│   ├── enhanced_executor.py  # 增强执行器（支持工具）
│   ├── workflow.py   # 工作流定义
│   ├── dynamic_workflow.py   # 动态工作流
│   ├── resumable_workflow.py # 可恢复工作流
│   ├── workflow_state.py     # 工作流状态管理
│   ├── yaml_loader.py        # YAML 工作流加载
│   ├── dynamic_yaml_loader.py # 动态 YAML 加载
│   └── tool_registry.py      # 工具注册器
├── commands/          # 命令实现
│   ├── auth.py       # 认证命令
│   ├── commit.py     # 提交命令
│   ├── config.py     # 配置命令
│   ├── diff.py       # 差异命令
│   ├── dream.py      # 梦境命令
│   ├── review.py     # 审查命令
│   ├── security.py   # 安全命令
│   └── tasks.py      # 任务命令
├── tools/            # 工具实现
│   ├── base.py       # 基础工具类
│   ├── files.py      # 文件操作工具
│   ├── git.py        # Git 工具
│   ├── search.py     # 搜索工具
│   └── shell.py      # Shell 工具
├── ui/               # 用户界面
│   └── app.py        # 主应用
├── examples/         # 示例代码
│   ├── demo_multi_agent.py   # 多 Agent 演示
│   └── demo_memory_usage.py  # 记忆系统演示
├── __init__.py
├── __main__.py
├── cli.py            # CLI 入口
├── client.py         # AI 客户端
├── config.py         # 配置管理
├── memory.py         # 记忆系统
├── security.py       # 安全系统
└── ...
```

## 🔧 配置

配置文件位于 `~/.claude_code/` 目录，包含：

- `config.json` - 主配置文件
- `providers.json` - 提供商配置
- `memories/` - 记忆存储目录
- `.workflow_states/` - 工作流状态存储（自动创建）

### Ollama 配置示例

```yaml
# ~/.claude_code/config.yaml
ollama:
  model: qwen2.5
  base_url: http://localhost:11434
```

## 🧪 测试

```bash
# 运行所有测试
python -m tests.test_all

# 运行特定测试
python -m tests.test_memory
python -m tests.test_security
python -m tests.test_mcp

# 运行多 Agent 演示
python examples/demo_multi_agent.py
```

## 📝 许可证

MIT License

## 👥 作者

Code Gen Team

## 🙏 致谢

本项目基于 Claude Code 架构构建，提供了强大的 AI 编程辅助功能。特别感谢：
- Ollama 项目提供本地 AI 模型支持
- Model Context Protocol (MCP) 提供工具集成标准
