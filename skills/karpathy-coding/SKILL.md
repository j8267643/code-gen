---
name: karpathy-coding
description: "Andrej Karpathy 风格的编码最佳实践。在编写、审查或重构代码时使用，避免过度复杂化，进行精确修改，明确假设，并定义可验证的成功标准。触发词: '用 karpathy 风格', 'karpathy 模式', '简化代码', '精确修改'。"
user-invocable: true
---

# Karpathy 风格编码技能

基于 Andrej Karpathy 的编码哲学和最佳实践，帮助你写出简洁、高效、可维护的代码。

## 核心原则

### 1. 明确假设
- **显式声明假设** — 如果不确定，询问而不是猜测
- **呈现多种解释** — 当存在歧义时，不要默默选择
- **适时反驳** — 在合理时提出反对意见
- **遇到不清楚的地方，停下来，指出困惑之处，询问**

### 2. 简洁优先
- **最少代码解决问题**，不做推测性设计
- **精确修改** — 只触碰必须修改的部分，只清理自己造成的混乱
- **编辑现有代码时**:
  - 不要"改进"未要求修改的代码
  - 不要重构相邻代码
  - 不要更改格式
  - 不要引入新抽象
  - 保持原有风格

### 3. 对抗过度工程化
- **不要添加超出需求的功能**
- **不要为单次使用的代码创建抽象**
- **不要添加未被要求的"灵活性"或"可配置性"**
- **不要为不可能发生的场景添加错误处理**
- **如果 200 行可以写成 50 行，重写它**

### 4. 目标导向
- **定义清晰的成功标准**，循环验证直到满足
- **描述目标状态** 而非命令式指令
- **示例**: "添加输入验证并通过 API 响应暴露错误信息"

## 使用方式

### 代码编写
```
用 karpathy 风格编写 [功能描述]
```

### 代码审查
```
用 karpathy 风格审查这段代码
```

### 代码简化
```
用 karpathy 风格简化这段代码
```

### 重构
```
用 karpathy 风格重构 [代码/文件]
```

## 工作流程

1. **理解需求** — 明确目标，询问歧义
2. **最小实现** — 用最少的代码解决问题
3. **精确修改** — 只修改必要的部分
4. **验证成功** — 确保满足成功标准

## 示例

### ❌ 过度工程化
```python
class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.handlers = []
    
    def register_handler(self, handler):
        self.handlers.append(handler)
    
    def process(self, data):
        for handler in self.handlers:
            data = handler(data)
        return data

# 使用
processor = DataProcessor(config)
processor.register_handler(lambda x: x.strip())
processor.register_handler(lambda x: x.lower())
result = processor.process(data)
```

### ✅ Karpathy 风格
```python
def process_data(data: str) -> str:
    return data.strip().lower()

# 使用
result = process_data(data)
```

## 提示词模板

### 编码任务
```
请用 Karpathy 风格编写代码：

目标：[具体目标]

要求：
1. 最少代码解决问题
2. 不添加未要求的功能
3. 不创建不必要的抽象
4. 代码不超过 [X] 行

成功标准：
- [标准1]
- [标准2]
```

### 代码审查
```
请用 Karpathy 风格审查以下代码：

[代码]

检查点：
1. 是否有过度工程化？
2. 是否可以进一步简化？
3. 是否有不必要的抽象？
4. 是否只实现了必要的功能？
```

## 相关资源

- [Andrej Karpathy 的 LLM 编码规则](https://twitter.com/karpathy/status/...)
- [Claude Code 最佳实践](https://github.com/forrestchang/andrej-karpathy-skills)
