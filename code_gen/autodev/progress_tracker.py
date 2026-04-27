"""
Progress Tracker - 进度跟踪器

跟踪 Ralph 执行进度，类似于 Ralph 的 progress.txt
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class ProgressEntry:
    """进度条目"""
    timestamp: str
    story_id: str
    story_title: str
    status: str  # completed, failed, skipped
    output: str
    learnings: List[str] = field(default_factory=list)
    files_changed: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "story_id": self.story_id,
            "story_title": self.story_title,
            "status": self.status,
            "output": self.output,
            "learnings": self.learnings,
            "files_changed": self.files_changed
        }


@dataclass
class CodebasePattern:
    """代码库模式"""
    pattern: str
    description: str
    category: str  # pattern, gotcha, context
    added_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern,
            "description": self.description,
            "category": self.category,
            "added_at": self.added_at
        }


class ProgressTracker:
    """
    进度跟踪器
    
    类似于 Ralph 的 progress.txt，但增加了结构化支持
    """
    
    def __init__(self, progress_file: Path, patterns_file: Optional[Path] = None):
        self.progress_file = progress_file
        self.patterns_file = patterns_file or progress_file.parent / "patterns.json"
        self.entries: List[ProgressEntry] = []
        self.patterns: List[CodebasePattern] = []
        self._load()
    
    def _load(self):
        """加载已有进度"""
        # 加载进度条目
        if self.progress_file.exists():
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self._parse_progress_txt(content)
        
        # 加载模式
        if self.patterns_file.exists():
            with open(self.patterns_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.patterns = [
                    CodebasePattern(**p) for p in data.get("patterns", [])
                ]
    
    def _parse_progress_txt(self, content: str):
        """解析 progress.txt 格式"""
        # 分割条目
        entries = content.split("\n---\n")
        
        for entry_text in entries:
            if not entry_text.strip():
                continue
            
            # 解析条目
            lines = entry_text.strip().split("\n")
            if not lines:
                continue
            
            # 第一行应该是日期和故事ID
            header = lines[0]
            story_id = "unknown"
            timestamp = datetime.now().isoformat()
            
            match = re.search(r'(\d{4}-\d{2}-\d{2}.+?)\s*-\s*(.+)', header)
            if match:
                timestamp = match.group(1)
                story_id = match.group(2)
            
            # 解析其他信息
            story_title = ""
            status = "unknown"
            output = ""
            learnings = []
            
            for line in lines[1:]:
                if line.startswith("- 故事:"):
                    story_title = line.replace("- 故事:", "").strip()
                elif line.startswith("- 状态:"):
                    status_text = line.replace("- 状态:", "").strip()
                    if "完成" in status_text or "✅" in status_text:
                        status = "completed"
                    elif "失败" in status_text or "❌" in status_text:
                        status = "failed"
                elif line.startswith("- 输出:"):
                    output = line.replace("- 输出:", "").strip()
                elif line.startswith("  -"):
                    learnings.append(line.replace("  -", "").strip())
            
            entry = ProgressEntry(
                timestamp=timestamp,
                story_id=story_id,
                story_title=story_title,
                status=status,
                output=output,
                learnings=learnings
            )
            self.entries.append(entry)
    
    def add_entry(
        self,
        story_id: str,
        story_title: str,
        status: str,
        output: str = "",
        learnings: Optional[List[str]] = None,
        files_changed: Optional[List[str]] = None
    ):
        """添加进度条目"""
        entry = ProgressEntry(
            timestamp=datetime.now().isoformat(),
            story_id=story_id,
            story_title=story_title,
            status=status,
            output=output[:500],  # 限制长度
            learnings=learnings or [],
            files_changed=files_changed or []
        )
        self.entries.append(entry)
        self._save_entry(entry)
    
    def _save_entry(self, entry: ProgressEntry):
        """保存单个条目到文件"""
        status_emoji = "✅" if entry.status == "completed" else "❌" if entry.status == "failed" else "⏭️"
        
        text = f"""
## {entry.timestamp} - {entry.story_id}
- 故事: {entry.story_title}
- 状态: {status_emoji} {entry.status}
- 输出: {entry.output}
"""
        
        if entry.learnings:
            text += "- 学习点:\n"
            for learning in entry.learnings:
                text += f"  - {learning}\n"
        
        if entry.files_changed:
            text += "- 修改的文件:\n"
            for file in entry.files_changed:
                text += f"  - {file}\n"
        
        text += "---\n"
        
        with open(self.progress_file, 'a', encoding='utf-8') as f:
            f.write(text)
    
    def add_pattern(
        self,
        pattern: str,
        description: str,
        category: str = "pattern"
    ):
        """添加代码库模式"""
        codebase_pattern = CodebasePattern(
            pattern=pattern,
            description=description,
            category=category
        )
        self.patterns.append(codebase_pattern)
        self._save_patterns()
    
    def _save_patterns(self):
        """保存模式到文件"""
        data = {
            "patterns": [p.to_dict() for p in self.patterns],
            "updated_at": datetime.now().isoformat()
        }
        with open(self.patterns_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_patterns(self, category: Optional[str] = None) -> List[CodebasePattern]:
        """获取代码库模式"""
        if category:
            return [p for p in self.patterns if p.category == category]
        return self.patterns
    
    def get_learnings(self) -> List[str]:
        """获取所有学习点"""
        learnings = []
        for entry in self.entries:
            learnings.extend(entry.learnings)
        return learnings
    
    def generate_summary(self) -> str:
        """生成进度摘要"""
        total = len(self.entries)
        completed = sum(1 for e in self.entries if e.status == "completed")
        failed = sum(1 for e in self.entries if e.status == "failed")
        
        summary = f"""# Ralph 执行进度摘要

## 统计
- 总条目: {total}
- 已完成: {completed}
- 失败: {failed}
- 成功率: {(completed/total*100) if total > 0 else 0:.1f}%

## 代码库模式 ({len(self.patterns)} 个)
"""
        
        for pattern in self.patterns[:10]:  # 只显示前10个
            summary += f"- [{pattern.category}] {pattern.pattern}: {pattern.description}\n"
        
        summary += "\n## 最近的学习点\n"
        recent_learnings = self.get_learnings()[-5:]
        for learning in recent_learnings:
            summary += f"- {learning}\n"
        
        return summary
    
    def get_context_for_agent(self) -> str:
        """为 Agent 生成上下文信息"""
        context = "## 代码库模式\n"
        
        for pattern in self.patterns:
            context += f"- {pattern.pattern}: {pattern.description}\n"
        
        if self.entries:
            context += "\n## 最近的执行\n"
            for entry in self.entries[-3:]:
                context += f"- {entry.story_id}: {entry.status}\n"
        
        return context


import re  # 放在文件末尾避免循环导入
