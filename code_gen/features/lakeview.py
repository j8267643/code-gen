"""
Lakeview - 智能步骤摘要系统

功能：自动总结 Agent 每个步骤的任务，让用户快速了解 AI 在做什么
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import json

# Rich imports for beautiful output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class StepTag(str, Enum):
    """步骤标签 - 定义 Agent 可能执行的任务类型"""
    WRITE_TEST = "WRITE_TEST"           # 编写测试
    VERIFY_TEST = "VERIFY_TEST"         # 验证测试
    EXAMINE_CODE = "EXAMINE_CODE"       # 检查代码
    WRITE_FIX = "WRITE_FIX"             # 编写修复
    VERIFY_FIX = "VERIFY_FIX"           # 验证修复
    ANALYZE = "ANALYZE"                 # 分析问题
    PLAN = "PLAN"                       # 制定计划
    EXECUTE = "EXECUTE"                 # 执行命令
    SEARCH = "SEARCH"                   # 搜索代码
    REFLECT = "REFLECT"                 # 反思
    REPORT = "REPORT"                   # 报告结果
    THINK = "THINK"                     # 思考
    OUTLIER = "OUTLIER"                 # 其他


# 标签对应的 emoji
TAG_EMOJI = {
    StepTag.WRITE_TEST: "☑️",
    StepTag.VERIFY_TEST: "✅",
    StepTag.EXAMINE_CODE: "👁️",
    StepTag.WRITE_FIX: "📝",
    StepTag.VERIFY_FIX: "🔥",
    StepTag.ANALYZE: "🔍",
    StepTag.PLAN: "📋",
    StepTag.EXECUTE: "⚡",
    StepTag.SEARCH: "🔎",
    StepTag.REFLECT: "💭",
    StepTag.REPORT: "📣",
    StepTag.THINK: "🧠",
    StepTag.OUTLIER: "⁉️",
}


@dataclass
class StepSummary:
    """步骤摘要"""
    step_number: int
    task: str                          # 简洁的任务描述（最多10个词）
    details: str                       # 详细描述（最多30个词）
    tags: List[StepTag] = field(default_factory=list)
    emoji: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "task": self.task,
            "details": self.details,
            "tags": [t.value for t in self.tags],
            "emoji": self.emoji,
            "timestamp": self.timestamp
        }


@dataclass
class AgentStep:
    """Agent 执行步骤"""
    step_number: int
    action: str                        # 执行的动作
    result: Optional[str] = None       # 执行结果
    tool_name: Optional[str] = None    # 使用的工具
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class LakeviewSummarizer:
    """Lakeview 摘要生成器 - 基于规则的轻量级实现"""
    
    # 工具名称到标签的映射
    TOOL_TAG_MAP = {
        "read_file": [StepTag.EXAMINE_CODE],
        "write_file": [StepTag.WRITE_FIX],
        "edit_file": [StepTag.WRITE_FIX],
        "search_codebase": [StepTag.SEARCH],
        "grep": [StepTag.SEARCH],
        "glob": [StepTag.SEARCH],
        "bash": [StepTag.EXECUTE],
        "run_command": [StepTag.EXECUTE],
        "TodoWrite": [StepTag.PLAN],
        "AskUserQuestion": [StepTag.REPORT],
        "sequential_thinking": [StepTag.THINK],
        "analyze_project": [StepTag.ANALYZE],
        "smart_run": [StepTag.EXECUTE],
    }
    
    # 动作关键词到标签的映射
    ACTION_KEYWORDS = {
        "测试": [StepTag.WRITE_TEST, StepTag.VERIFY_TEST],
        "test": [StepTag.WRITE_TEST, StepTag.VERIFY_TEST],
        "修复": [StepTag.WRITE_FIX, StepTag.VERIFY_FIX],
        "fix": [StepTag.WRITE_FIX, StepTag.VERIFY_FIX],
        "分析": [StepTag.ANALYZE],
        "analyze": [StepTag.ANALYZE],
        "检查": [StepTag.EXAMINE_CODE],
        "查看": [StepTag.EXAMINE_CODE],
        "examine": [StepTag.EXAMINE_CODE],
        "搜索": [StepTag.SEARCH],
        "search": [StepTag.SEARCH],
        "运行": [StepTag.EXECUTE],
        "run": [StepTag.EXECUTE],
        "执行": [StepTag.EXECUTE],
        "计划": [StepTag.PLAN],
        "plan": [StepTag.PLAN],
        "思考": [StepTag.THINK],
        "think": [StepTag.THINK],
        "反思": [StepTag.REFLECT],
        "reflect": [StepTag.REFLECT],
        "完成": [StepTag.REPORT],
        "总结": [StepTag.REPORT],
        "报告": [StepTag.REPORT],
    }
    
    def __init__(self):
        self.summaries: List[StepSummary] = []
        self.current_step: int = 0
    
    def summarize_step(self, step: AgentStep) -> StepSummary:
        """生成步骤摘要"""
        self.current_step += 1
        
        # 基于工具名称确定标签
        tags = self._detect_tags(step)
        
        # 生成任务描述
        task = self._generate_task_description(step, tags)
        
        # 生成详细描述
        details = self._generate_details(step, tags)
        
        # 生成 emoji
        emoji = self._generate_emoji(tags)
        
        summary = StepSummary(
            step_number=self.current_step,
            task=task,
            details=details,
            tags=tags,
            emoji=emoji,
            timestamp=step.timestamp
        )
        
        self.summaries.append(summary)
        return summary
    
    def _detect_tags(self, step: AgentStep) -> List[StepTag]:
        """检测步骤标签"""
        tags = set()
        
        # 基于工具名称
        if step.tool_name and step.tool_name in self.TOOL_TAG_MAP:
            tags.update(self.TOOL_TAG_MAP[step.tool_name])
        
        # 基于动作内容关键词
        action_lower = step.action.lower()
        for keyword, keyword_tags in self.ACTION_KEYWORDS.items():
            if keyword.lower() in action_lower:
                tags.update(keyword_tags)
        
        # 基于结果内容
        if step.result:
            result_lower = step.result.lower()
            if "error" in result_lower or "失败" in result_lower:
                tags.add(StepTag.OUTLIER)
            if "success" in result_lower or "成功" in result_lower:
                tags.add(StepTag.VERIFY_FIX)
        
        return list(tags) if tags else [StepTag.OUTLIER]
    
    def _generate_task_description(self, step: AgentStep, tags: List[StepTag]) -> str:
        """生成简洁的任务描述"""
        # 基于标签生成描述
        if StepTag.WRITE_TEST in tags:
            return "编写测试代码"
        elif StepTag.VERIFY_TEST in tags:
            return "验证测试结果"
        elif StepTag.EXAMINE_CODE in tags:
            return "检查代码文件"
        elif StepTag.WRITE_FIX in tags:
            return "修改代码文件"
        elif StepTag.VERIFY_FIX in tags:
            return "验证修复结果"
        elif StepTag.ANALYZE in tags:
            return "分析问题原因"
        elif StepTag.PLAN in tags:
            return "制定执行计划"
        elif StepTag.EXECUTE in tags:
            return "执行命令操作"
        elif StepTag.SEARCH in tags:
            return "搜索代码内容"
        elif StepTag.THINK in tags:
            return "进行深度思考"
        elif StepTag.REFLECT in tags:
            return "反思执行过程"
        elif StepTag.REPORT in tags:
            return "报告执行结果"
        else:
            # 从动作中提取
            action = step.action[:30] if len(step.action) > 30 else step.action
            return action
    
    def _generate_details(self, step: AgentStep, tags: List[StepTag]) -> str:
        """生成详细描述"""
        details_parts = []
        
        # 添加工具信息
        if step.tool_name:
            details_parts.append(f"使用工具: {step.tool_name}")
        
        # 添加动作摘要
        action_summary = step.action[:50] if len(step.action) > 50 else step.action
        details_parts.append(f"操作: {action_summary}")
        
        # 添加结果摘要
        if step.result:
            result_summary = step.result[:50] if len(step.result) > 50 else step.result
            details_parts.append(f"结果: {result_summary}")
        
        return " | ".join(details_parts)
    
    def _generate_emoji(self, tags: List[StepTag]) -> str:
        """生成 emoji 表示"""
        if not tags:
            return TAG_EMOJI[StepTag.OUTLIER]
        
        # 优先使用第一个标签的 emoji
        return TAG_EMOJI.get(tags[0], TAG_EMOJI[StepTag.OUTLIER])
    
    def get_summary_text(self, summary: StepSummary, verbose: bool = False) -> str:
        """获取格式化的摘要文本 (纯文本版本)"""
        if verbose:
            tag_str = ", ".join([f"{TAG_EMOJI.get(t, '')}{t.value}" for t in summary.tags])
            return f"{summary.emoji} Step {summary.step_number}: {summary.task}\n   {summary.details}\n   标签: {tag_str}"
        else:
            return f"{summary.emoji} Step {summary.step_number}: {summary.task}"
    
    def get_all_summaries_text(self, verbose: bool = False) -> str:
        """获取所有摘要的文本 (纯文本版本)"""
        lines = ["📊 执行步骤摘要:", ""]
        for summary in self.summaries:
            lines.append(self.get_summary_text(summary, verbose))
        return "\n".join(lines)
    
    def get_step_table(self, summary: StepSummary) -> Optional[Any]:
        """获取步骤的 Rich Table 格式"""
        if not RICH_AVAILABLE:
            return None
        
        # Create a table for this step
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="cyan", width=12)
        table.add_column("Content", style="white")
        
        # Add step number and task
        table.add_row(
            "Step",
            f"[bold green]{summary.emoji} Step {summary.step_number}[/bold green]: [bold]{summary.task}[/bold]"
        )
        
        # Add details
        if summary.details:
            table.add_row("Details", summary.details[:80])
        
        # Add tags (without the ugly ⁉️ symbol)
        if summary.tags:
            tag_texts = []
            for tag in summary.tags:
                emoji = TAG_EMOJI.get(tag, "")
                # Skip the ugly OUTLIER tag emoji
                if tag == StepTag.OUTLIER:
                    continue
                tag_texts.append(f"{emoji} {tag.value}")
            if tag_texts:
                table.add_row("Tags", ", ".join(tag_texts))
        
        return table
    
    def get_all_summaries_rich(self) -> Optional[Any]:
        """获取所有摘要的 Rich 格式"""
        if not RICH_AVAILABLE:
            return None
        
        if not self.summaries:
            return Panel("[dim]暂无执行步骤[/dim]", title="📊 执行摘要", border_style="blue")
        
        # Create a panel for each step
        panels = []
        for summary in self.summaries:
            table = self.get_step_table(summary)
            if table:
                panels.append(table)
        
        return Columns(panels, equal=False, expand=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "summaries": [s.to_dict() for s in self.summaries],
            "current_step": self.current_step,
            "total_steps": len(self.summaries)
        }
    
    def save(self, filepath: str):
        """保存到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


class Lakeview:
    """Lakeview 主类 - 集成到 Agent 中"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.summarizer = LakeviewSummarizer()
        self.step_history: List[AgentStep] = []
    
    def record_step(self, action: str, result: Optional[str] = None, 
                   tool_name: Optional[str] = None) -> Optional[StepSummary]:
        """记录一个步骤"""
        if not self.enabled:
            return None
        
        step = AgentStep(
            step_number=len(self.step_history) + 1,
            action=action,
            result=result,
            tool_name=tool_name
        )
        self.step_history.append(step)
        
        summary = self.summarizer.summarize_step(step)
        return summary
    
    def get_current_summary(self) -> Optional[str]:
        """获取当前摘要"""
        if not self.summarizer.summaries:
            return None
        
        latest = self.summarizer.summaries[-1]
        return self.summarizer.get_summary_text(latest, verbose=False)
    
    def reset(self):
        """重置 Lakeview 状态，清除所有步骤记录"""
        self.step_history = []
        self.summarizer.summaries = []
        self.summarizer.current_step = 0
    
    def get_full_summary(self) -> str:
        """获取完整摘要 (纯文本版本)"""
        if not self.enabled or not self.summarizer.summaries:
            return "Lakeview 未启用或暂无步骤记录"
        
        return self.summarizer.get_all_summaries_text(verbose=True)
    
    def get_summary(self) -> str:
        """获取摘要 (纯文本版本，用于兼容)"""
        return self.get_full_summary()
    
    def get_rich_summary(self) -> Optional[Any]:
        """获取 Rich 格式的摘要"""
        if not self.enabled:
            return None
        return self.summarizer.get_all_summaries_rich()
    
    def print_summary(self, use_rich: bool = True):
        """打印摘要到控制台
        
        Args:
            use_rich: 是否使用 Rich 格式输出，默认为 True
        """
        if use_rich and RICH_AVAILABLE:
            rich_summary = self.get_rich_summary()
            if rich_summary:
                console = Console()
                console.print(rich_summary)
            else:
                print(self.get_full_summary())
        else:
            print(self.get_full_summary())
    
    def save_trajectory(self, filepath: str):
        """保存轨迹"""
        self.summarizer.save(filepath)


# 便捷函数
def create_lakeview(enabled: bool = True) -> Lakeview:
    """创建 Lakeview 实例"""
    return Lakeview(enabled=enabled)
