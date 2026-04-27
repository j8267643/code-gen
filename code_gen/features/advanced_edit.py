"""
Advanced Edit Tools - 高级编辑工具

功能：强大的文件编辑能力，包括 view, create, str_replace, insert 等命令
比基础文件操作更精确、更强大
"""
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import hashlib


class EditCommand(str, Enum):
    """编辑命令"""
    VIEW = "view"               # 查看文件/目录
    CREATE = "create"           # 创建文件
    STR_REPLACE = "str_replace" # 字符串替换
    INSERT = "insert"           # 插入内容


class EditError(Exception):
    """编辑错误"""
    pass


@dataclass
class EditResult:
    """编辑结果"""
    success: bool
    message: str
    content: Optional[str] = None
    lines_affected: int = 0


class TextEditor:
    """文本编辑器 - 高级文件编辑功能"""
    
    SNIPPET_LINES = 4  # 显示代码片段时的上下文行数
    MAX_OUTPUT_LENGTH = 2000  # 最大输出长度
    
    def __init__(self, working_dir: str = "."):
        self.working_dir = Path(working_dir).resolve()
        self._file_cache: Dict[str, str] = {}  # 文件缓存
    
    def _resolve_path(self, path: str) -> Path:
        """解析路径"""
        if os.path.isabs(path):
            return Path(path)
        return self.working_dir / path
    
    def _validate_path(self, path: Path) -> bool:
        """验证路径是否在 working_dir 内"""
        try:
            path.resolve().relative_to(self.working_dir)
            return True
        except ValueError:
            return False
    
    def _truncate_output(self, content: str, max_length: int = None) -> str:
        """截断输出"""
        if max_length is None:
            max_length = self.MAX_OUTPUT_LENGTH
        
        if len(content) <= max_length:
            return content
        
        return content[:max_length] + f"\n\n... [内容已截断，共 {len(content)} 字符]"
    
    def view(self, path: str, view_range: Optional[Tuple[int, int]] = None,
             limit: int = 100) -> EditResult:
        """
        查看文件或目录
        
        Args:
            path: 文件或目录路径
            view_range: 查看的行范围 (start, end)，可选
            limit: 目录下最多显示的文件数
        """
        target_path = self._resolve_path(path)
        
        if not target_path.exists():
            return EditResult(False, f"路径不存在: {path}")
        
        if target_path.is_dir():
            return self._view_directory(target_path, limit)
        else:
            return self._view_file(target_path, view_range)
    
    def _view_directory(self, dir_path: Path, limit: int = 100) -> EditResult:
        """查看目录"""
        if not self._validate_path(dir_path):
            return EditResult(False, "访问被拒绝: 路径超出工作目录")
        
        lines = [f"📁 {dir_path.relative_to(self.working_dir)}/", ""]
        
        try:
            entries = list(dir_path.iterdir())
            entries.sort(key=lambda x: (x.is_file(), x.name.lower()))
            
            # 限制显示数量
            if len(entries) > limit:
                shown_entries = entries[:limit]
                truncated = True
            else:
                shown_entries = entries
                truncated = False
            
            for entry in shown_entries:
                if entry.is_dir():
                    lines.append(f"  📁 {entry.name}/")
                else:
                    size = entry.stat().st_size
                    size_str = self._format_size(size)
                    lines.append(f"  📄 {entry.name} ({size_str})")
            
            if truncated:
                lines.append(f"\n... 还有 {len(entries) - limit} 个文件/目录")
            
            lines.append(f"\n共 {len(entries)} 个条目")
            
            content = "\n".join(lines)
            return EditResult(True, "目录查看成功", content)
            
        except Exception as e:
            return EditResult(False, f"无法读取目录: {e}")
    
    def _view_file(self, file_path: Path, 
                   view_range: Optional[Tuple[int, int]] = None) -> EditResult:
        """查看文件"""
        if not self._validate_path(file_path):
            return EditResult(False, "访问被拒绝: 路径超出工作目录")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            return EditResult(False, "无法解码文件内容（可能是二进制文件）")
        except Exception as e:
            return EditResult(False, f"无法读取文件: {e}")
        
        # 添加行号
        total_lines = len(lines)
        
        if view_range:
            start, end = view_range
            start = max(1, start)
            end = min(total_lines, end)
            lines = lines[start-1:end]
            line_offset = start - 1
        else:
            line_offset = 0
        
        # 格式化输出
        max_line_num_width = len(str(total_lines))
        formatted_lines = []
        
        for i, line in enumerate(lines, start=line_offset+1):
            # 去除行尾换行符
            line_content = line.rstrip('\n\r')
            formatted_lines.append(f"{i:>{max_line_num_width}} | {line_content}")
        
        content = "\n".join(formatted_lines)
        
        # 截断长输出
        truncated = False
        if len(content) > self.MAX_OUTPUT_LENGTH:
            content = self._truncate_output(content)
            truncated = True
        
        header = f"📄 {file_path.relative_to(self.working_dir)} ({total_lines} 行)"
        if view_range:
            header += f" [显示 {view_range[0]}-{view_range[1]} 行]"
        if truncated:
            header += " [内容已截断]"
        
        full_content = f"{header}\n{'=' * len(header)}\n{content}"
        
        return EditResult(True, "文件查看成功", full_content, total_lines)
    
    def create(self, path: str, content: str) -> EditResult:
        """
        创建新文件
        
        Args:
            path: 文件路径
            content: 文件内容
        """
        file_path = self._resolve_path(path)
        
        if not self._validate_path(file_path):
            return EditResult(False, "访问被拒绝: 路径超出工作目录")
        
        if file_path.exists():
            return EditResult(False, f"文件已存在: {path}。如需覆盖，请先删除。")
        
        try:
            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            lines_count = len(content.split('\n'))
            return EditResult(
                True, 
                f"文件创建成功: {path}",
                f"创建了 {path} ({lines_count} 行)",
                lines_count
            )
        except Exception as e:
            return EditResult(False, f"创建文件失败: {e}")
    
    def str_replace(self, path: str, old_str: str, new_str: str) -> EditResult:
        """
        字符串替换 - 精确匹配替换
        
        重要说明：
        - old_str 必须精确匹配文件中的一段内容（包括空格和换行）
        - 如果 old_str 在文件中不唯一，替换将失败
        - 请确保 old_str 包含足够的上下文以使其唯一
        
        Args:
            path: 文件路径
            old_str: 要替换的字符串
            new_str: 新字符串
        """
        file_path = self._resolve_path(path)
        
        if not self._validate_path(file_path):
            return EditResult(False, "访问被拒绝: 路径超出工作目录")
        
        if not file_path.exists():
            return EditResult(False, f"文件不存在: {path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            return EditResult(False, f"无法读取文件: {e}")
        
        # 检查 old_str 是否存在
        if old_str not in original_content:
            return EditResult(
                False, 
                f"未找到要替换的内容。请确保 old_str 精确匹配文件中的内容。"
            )
        
        # 检查唯一性
        occurrences = original_content.count(old_str)
        if occurrences > 1:
            # 找到所有出现位置
            positions = []
            start = 0
            while True:
                idx = original_content.find(old_str, start)
                if idx == -1:
                    break
                # 计算行号
                line_num = original_content[:idx].count('\n') + 1
                positions.append(line_num)
                start = idx + 1
            
            return EditResult(
                False,
                f"找到 {occurrences} 处匹配（行号: {positions}）。"
                f"请提供更多上下文使 old_str 唯一。"
            )
        
        # 执行替换
        new_content = original_content.replace(old_str, new_str, 1)
        
        # 写回文件
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        except Exception as e:
            return EditResult(False, f"写入文件失败: {e}")
        
        # 计算变更
        old_lines = old_str.count('\n') + 1
        new_lines = new_str.count('\n') + 1
        line_diff = new_lines - old_lines
        
        # 生成摘要
        snippet = self._get_change_snippet(new_content, new_str)
        
        message = f"替换成功: {path}\n"
        message += f"行数变化: {line_diff:+d} 行\n"
        message += f"\n变更摘要:\n{snippet}"
        
        return EditResult(True, message, snippet, abs(line_diff))
    
    def insert(self, path: str, insert_line: int, new_str: str) -> EditResult:
        """
        在指定行后插入内容
        
        Args:
            path: 文件路径
            insert_line: 插入位置的行号（在该行之后插入）
            new_str: 要插入的内容
        """
        file_path = self._resolve_path(path)
        
        if not self._validate_path(file_path):
            return EditResult(False, "访问被拒绝: 路径超出工作目录")
        
        if not file_path.exists():
            return EditResult(False, f"文件不存在: {path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            return EditResult(False, f"无法读取文件: {e}")
        
        total_lines = len(lines)
        
        if insert_line < 0 or insert_line > total_lines:
            return EditResult(
                False, 
                f"插入位置无效: {insert_line}。文件共 {total_lines} 行。"
            )
        
        # 确保 new_str 以换行符结尾
        if not new_str.endswith('\n'):
            new_str += '\n'
        
        # 插入内容
        new_lines = new_str.count('\n')
        lines.insert(insert_line, new_str)
        
        # 写回文件
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        except Exception as e:
            return EditResult(False, f"写入文件失败: {e}")
        
        message = f"插入成功: {path}\n"
        message += f"在 {insert_line} 行后插入了 {new_lines} 行"
        
        return EditResult(True, message, lines_affected=new_lines)
    
    def _get_change_snippet(self, content: str, changed_part: str, 
                           context: int = 3) -> str:
        """获取变更的代码片段"""
        lines = content.split('\n')
        changed_lines = changed_part.split('\n')
        
        # 找到变更位置
        changed_start = 0
        for i, line in enumerate(lines):
            if changed_lines[0] in line:
                changed_start = i
                break
        
        # 计算显示范围
        start = max(0, changed_start - context)
        end = min(len(lines), changed_start + len(changed_lines) + context)
        
        # 格式化
        snippet_lines = []
        for i in range(start, end):
            prefix = ">>> " if start <= i < changed_start + len(changed_lines) else "    "
            snippet_lines.append(f"{prefix}{i+1:4d} | {lines[i]}")
        
        return "\n".join(snippet_lines)
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class AdvancedEditTool:
    """高级编辑工具 - 供 Agent 使用"""
    
    def __init__(self, working_dir: str = "."):
        self.editor = TextEditor(working_dir)
    
    def view(self, path: str, view_range: Optional[str] = None) -> str:
        """查看文件或目录"""
        range_tuple = None
        if view_range:
            try:
                parts = view_range.split('-')
                range_tuple = (int(parts[0]), int(parts[1]))
            except (ValueError, IndexError):
                return f"错误: 无效的行范围格式 '{view_range}'，请使用 'start-end' 格式"
        
        result = self.editor.view(path, range_tuple)
        return result.content if result.success else f"错误: {result.message}"
    
    def create(self, path: str, file_text: str) -> str:
        """创建文件"""
        result = self.editor.create(path, file_text)
        return result.message
    
    def str_replace(self, path: str, old_str: str, new_str: str) -> str:
        """字符串替换"""
        result = self.editor.str_replace(path, old_str, new_str)
        return result.message
    
    def insert(self, path: str, insert_line: int, new_str: str) -> str:
        """插入内容"""
        result = self.editor.insert(path, insert_line, new_str)
        return result.message


# 便捷函数
def create_advanced_edit_tool(working_dir: str = ".") -> AdvancedEditTool:
    """创建高级编辑工具"""
    return AdvancedEditTool(working_dir)
