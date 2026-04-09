# Code Gen - AI 编程助手 CLI

一个基于 AI 的命令行编程助手，帮助开发者提高编码效率。

## 🌟 功能特性

### 核心功能

- **交互式聊天** - 与 AI 进行自然语言对话，获取代码建议和解决方案
- **代码审查** - 使用 AI 自动审查代码质量和潜在问题
- **自动生成提交信息** - 分析代码变更并生成提交信息
- **差异分析** - 获取 Git 差异的 AI 解释
- **任务管理** - 管理开发任务和进度

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
pip install typer rich
```

### 配置提供商

```bash
# 使用 Ollama (本地模型)
code_gen provider ollama

# 使用 LMStudio
code_gen provider lmstudio

# 使用 Anthropic API
code_gen provider anthropic
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

## 🏗️ 项目结构

```
code_gen/
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

## 🧪 测试

```bash
# 运行所有测试
python -m tests.test_all

# 运行特定测试
python -m tests.test_memory
python -m tests.test_security
```

## 📝 许可证

MIT License

## 👥 作者

Code Gen Team

## 🙏 致谢

本项目基于 Claude Code 架构构建，提供了强大的 AI 编程辅助功能。
