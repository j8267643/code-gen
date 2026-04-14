"""
Git Integration - Git 集成
Inspired by Claude Code's git automation

功能：
1. 自动提交（可配置开关，默认关闭）
2. 对话式 Git 操作
3. 自动生成提交信息
4. 每轮对话自动存档
5. 分支管理
6. 变更追踪

适用于：自动化版本控制、代码审计、协作开发
"""
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import subprocess
import re
import os


class GitAutoCommitMode(str, Enum):
    """自动提交模式"""
    DISABLED = "disabled"      # 禁用（默认）
    MANUAL = "manual"          # 手动触发
    ON_SUCCESS = "on_success"  # 成功时自动提交
    EVERY_TURN = "every_turn"  # 每轮都提交


class GitOperationStatus(str, Enum):
    """Git 操作状态"""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    NO_CHANGES = "no_changes"


@dataclass
class GitConfig:
    """Git 集成配置"""
    # 自动提交设置（默认禁用）
    auto_commit: GitAutoCommitMode = GitAutoCommitMode.DISABLED
    
    # 提交信息设置
    auto_generate_message: bool = True
    commit_message_template: str = "[{timestamp}] {summary}"
    include_diff_in_message: bool = False
    
    # 分支设置
    auto_create_branch: bool = False
    branch_prefix: str = "agent/"
    
    # 存档设置
    archive_every_turn: bool = False
    archive_branch: str = "agent-archive"
    
    # 安全设置
    require_clean_working_tree: bool = False
    allowed_operations: List[str] = field(default_factory=lambda: [
        "status", "add", "commit", "log", "diff", "branch"
    ])
    
    # 仓库设置
    repo_path: Optional[Path] = None
    git_executable: str = "git"
    
    def __post_init__(self):
        if isinstance(self.auto_commit, str):
            self.auto_commit = GitAutoCommitMode(self.auto_commit)


@dataclass
class GitOperationResult:
    """Git 操作结果"""
    status: GitOperationStatus
    operation: str
    message: str
    stdout: str = ""
    stderr: str = ""
    commit_hash: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def success(self) -> bool:
        return self.status == GitOperationStatus.SUCCESS


@dataclass
class ChangeInfo:
    """变更信息"""
    file_path: str
    change_type: str  # added, modified, deleted, renamed
    additions: int = 0
    deletions: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "type": self.change_type,
            "additions": self.additions,
            "deletions": self.deletions
        }


class GitIntegration:
    """
    Git 集成管理器
    
    提供对话式 Git 操作和自动提交功能
    """
    
    def __init__(self, config: Optional[GitConfig] = None):
        self.config = config or GitConfig()
        self.operation_history: List[GitOperationResult] = []
        self._repo_path: Optional[Path] = None
        
        # 初始化仓库路径
        if self.config.repo_path:
            self._repo_path = self.config.repo_path
        else:
            self._repo_path = self._find_git_root()
    
    def _find_git_root(self) -> Optional[Path]:
        """查找 Git 仓库根目录"""
        current = Path.cwd()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        return None
    
    def _run_git(
        self,
        args: List[str],
        check: bool = False
    ) -> GitOperationResult:
        """
        执行 Git 命令
        
        Args:
            args: Git 命令参数
            check: 是否检查返回值
            
        Returns:
            GitOperationResult
        """
        if not self._repo_path:
            return GitOperationResult(
                status=GitOperationStatus.FAILED,
                operation=" ".join(args),
                message="未找到 Git 仓库"
            )
        
        cmd = [self.config.git_executable] + args
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                return GitOperationResult(
                    status=GitOperationStatus.SUCCESS,
                    operation=" ".join(args),
                    message="操作成功",
                    stdout=result.stdout,
                    stderr=result.stderr
                )
            else:
                return GitOperationResult(
                    status=GitOperationStatus.FAILED,
                    operation=" ".join(args),
                    message=f"Git 错误 (code {result.returncode})",
                    stdout=result.stdout,
                    stderr=result.stderr
                )
        except Exception as e:
            return GitOperationResult(
                status=GitOperationStatus.FAILED,
                operation=" ".join(args),
                message=f"执行错误: {str(e)}"
            )
    
    # ========== 基本 Git 操作 ==========
    
    def status(self) -> GitOperationResult:
        """获取仓库状态"""
        return self._run_git(["status", "-s"])
    
    def get_status_parsed(self) -> Dict[str, List[str]]:
        """获取解析后的状态"""
        result = self._run_git(["status", "-s", "--porcelain"])
        
        if not result.success:
            return {"error": result.message}
        
        staged = []
        unstaged = []
        untracked = []
        
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            status_code = line[:2]
            file_path = line[3:].strip()
            
            if status_code[0] in 'MADRC':
                staged.append(file_path)
            if status_code[1] in 'MD':
                unstaged.append(file_path)
            if status_code == '??':
                untracked.append(file_path)
        
        return {
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "has_changes": bool(staged or unstaged or untracked)
        }
    
    def add(self, files: Union[str, List[str]] = ".") -> GitOperationResult:
        """添加文件到暂存区"""
        if isinstance(files, str):
            files = [files]
        return self._run_git(["add"] + files)
    
    def commit(
        self,
        message: str,
        allow_empty: bool = False
    ) -> GitOperationResult:
        """
        提交更改
        
        Args:
            message: 提交信息
            allow_empty: 允许空提交
        """
        cmd = ["commit", "-m", message]
        if allow_empty:
            cmd.append("--allow-empty")
        
        result = self._run_git(cmd)
        
        if result.success:
            # 获取提交 hash
            hash_result = self._run_git(["rev-parse", "HEAD"])
            if hash_result.success:
                result.commit_hash = hash_result.stdout.strip()
        
        self.operation_history.append(result)
        return result
    
    def diff(self, cached: bool = False) -> GitOperationResult:
        """查看差异"""
        cmd = ["diff"]
        if cached:
            cmd.append("--cached")
        return self._run_git(cmd)
    
    def log(
        self,
        n: int = 10,
        oneline: bool = True
    ) -> GitOperationResult:
        """查看日志"""
        cmd = ["log", f"-{n}"]
        if oneline:
            cmd.append("--oneline")
        return self._run_git(cmd)
    
    def branch(self) -> GitOperationResult:
        """查看分支"""
        return self._run_git(["branch", "-a"])
    
    def checkout(self, branch: str, create: bool = False) -> GitOperationResult:
        """切换/创建分支"""
        cmd = ["checkout"]
        if create:
            cmd.append("-b")
        cmd.append(branch)
        return self._run_git(cmd)
    
    # ========== 智能提交功能 ==========
    
    def generate_commit_message(
        self,
        context: Optional[str] = None
    ) -> str:
        """
        自动生成提交信息
        
        基于变更内容生成有意义的提交信息
        """
        status = self.get_status_parsed()
        
        if "error" in status:
            return "Auto commit"
        
        changes = []
        
        # 分析变更类型
        if status["staged"]:
            changes.extend(status["staged"])
        if status["unstaged"]:
            changes.extend(status["unstaged"])
        
        if not changes:
            return "No changes"
        
        # 生成摘要
        file_count = len(changes)
        
        # 检测变更类型
        has_code = any(f.endswith(('.py', '.js', '.ts', '.java')) for f in changes)
        has_config = any(f.endswith(('.json', '.yaml', '.yml', '.toml')) for f in changes)
        has_docs = any(f.endswith(('.md', '.rst', '.txt')) for f in changes)
        
        # 构建提交信息
        parts = []
        
        if file_count == 1:
            parts.append(f"Update {changes[0]}")
        else:
            type_desc = []
            if has_code:
                type_desc.append("code")
            if has_config:
                type_desc.append("config")
            if has_docs:
                type_desc.append("docs")
            
            if type_desc:
                parts.append(f"Update {', '.join(type_desc)} ({file_count} files)")
            else:
                parts.append(f"Update {file_count} files")
        
        # 添加上下文
        if context:
            parts.append(f"- {context}")
        
        # 应用模板
        message = self.config.commit_message_template.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            summary=" | ".join(parts)
        )
        
        return message
    
    def smart_commit(
        self,
        message: Optional[str] = None,
        context: Optional[str] = None,
        auto_add: bool = True
    ) -> GitOperationResult:
        """
        智能提交
        
        自动处理添加、生成提交信息、提交
        """
        # 检查是否有变更
        status = self.get_status_parsed()
        if "error" in status:
            return GitOperationResult(
                status=GitOperationStatus.FAILED,
                operation="smart_commit",
                message=status["error"]
            )
        
        if not status["has_changes"]:
            return GitOperationResult(
                status=GitOperationStatus.NO_CHANGES,
                operation="smart_commit",
                message="没有可提交的变更"
            )
        
        # 自动添加
        if auto_add and (status["unstaged"] or status["untracked"]):
            add_result = self.add()
            if not add_result.success:
                return add_result
        
        # 生成提交信息
        if not message:
            message = self.generate_commit_message(context)
        
        # 执行提交
        return self.commit(message)
    
    # ========== 自动提交功能 ==========
    
    def should_auto_commit(
        self,
        operation_success: bool = True,
        turn_number: int = 0
    ) -> bool:
        """
        检查是否应该自动提交
        
        Args:
            operation_success: 操作是否成功
            turn_number: 当前轮次
            
        Returns:
            是否应该自动提交
        """
        mode = self.config.auto_commit
        
        if mode == GitAutoCommitMode.DISABLED:
            return False
        
        if mode == GitAutoCommitMode.MANUAL:
            return False  # 手动模式不自动提交
        
        if mode == GitAutoCommitMode.ON_SUCCESS:
            return operation_success
        
        if mode == GitAutoCommitMode.EVERY_TURN:
            return True
        
        return False
    
    def auto_commit_after_operation(
        self,
        operation_result: bool = True,
        context: Optional[str] = None
    ) -> Optional[GitOperationResult]:
        """
        操作后自动提交
        
        根据配置决定是否自动提交
        """
        if not self.should_auto_commit(operation_result):
            return None
        
        return self.smart_commit(context=context)
    
    # ========== 存档功能 ==========
    
    def archive_turn(
        self,
        turn_number: int,
        summary: Optional[str] = None
    ) -> GitOperationResult:
        """
        存档当前轮次
        
        将当前状态保存到存档分支
        """
        if not self.config.archive_every_turn:
            return GitOperationResult(
                status=GitOperationStatus.SKIPPED,
                operation="archive_turn",
                message="存档功能未启用"
            )
        
        # 获取当前分支
        current = self._run_git(["branch", "--show-current"])
        if not current.success:
            return current
        
        original_branch = current.stdout.strip()
        
        # 创建/切换到存档分支
        archive_branch = self.config.archive_branch
        branch_result = self.checkout(archive_branch, create=True)
        if not branch_result.success:
            return branch_result
        
        # 合并当前变更
        message = f"[Turn {turn_number}] {summary or 'Auto archive'}"
        result = self.smart_commit(message=message)
        
        # 切回原分支
        self.checkout(original_branch)
        
        return result
    
    # ========== 对话式 Git 操作 ==========
    
    def execute_git_command(
        self,
        command_description: str
    ) -> GitOperationResult:
        """
        执行自然语言描述的 Git 命令
        
        Args:
            command_description: 如 "提交所有更改"、"查看状态" 等
            
        Returns:
            GitOperationResult
        """
        # 解析命令
        command = command_description.lower()
        
        # 状态查询
        if any(kw in command for kw in ["状态", "status", "改了什么"]):
            return self.status()
        
        # 提交
        if any(kw in command for kw in ["提交", "commit", "保存"]):
            # 提取提交信息
            message = None
            if "-m" in command or "消息" in command:
                # 尝试提取提交信息
                match = re.search(r'["\'](.+?)["\']', command_description)
                if match:
                    message = match.group(1)
            
            return self.smart_commit(message=message)
        
        # 差异
        if any(kw in command for kw in ["差异", "diff", "改了什么", "变化"]):
            return self.diff()
        
        # 日志
        if any(kw in command for kw in ["日志", "log", "历史", "记录"]):
            return self.log()
        
        # 分支
        if any(kw in command for kw in ["分支", "branch", "切换"]):
            # 尝试提取分支名
            match = re.search(r'(\w+[-/\w]*)', command_description)
            if match:
                branch_name = match.group(1)
                create = "创建" in command or "新建" in command
                return self.checkout(branch_name, create=create)
            return self.branch()
        
        # 添加
        if any(kw in command for kw in ["添加", "add", "暂存"]):
            return self.add()
        
        return GitOperationResult(
            status=GitOperationStatus.FAILED,
            operation="parse",
            message=f"无法理解的命令: {command_description}"
        )
    
    # ========== 统计和报告 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取 Git 统计信息"""
        stats = {
            "repo_path": str(self._repo_path) if self._repo_path else None,
            "auto_commit_mode": self.config.auto_commit.value,
            "operation_count": len(self.operation_history),
            "success_count": sum(1 for r in self.operation_history if r.success)
        }
        
        # 获取仓库统计
        if self._repo_path:
            # 提交数
            count_result = self._run_git(["rev-list", "--count", "HEAD"])
            if count_result.success:
                stats["total_commits"] = int(count_result.stdout.strip())
            
            # 当前分支
            branch_result = self._run_git(["branch", "--show-current"])
            if branch_result.success:
                stats["current_branch"] = branch_result.stdout.strip()
            
            # 最近提交
            last_result = self._run_git(["log", "-1", "--format=%h %s"])
            if last_result.success:
                stats["last_commit"] = last_result.stdout.strip()
        
        return stats
    
    def get_change_summary(self) -> str:
        """获取变更摘要"""
        status = self.get_status_parsed()
        
        if "error" in status:
            return f"错误: {status['error']}"
        
        lines = []
        
        if status["staged"]:
            lines.append(f"已暂存: {len(status['staged'])} 个文件")
        
        if status["unstaged"]:
            lines.append(f"未暂存: {len(status['unstaged'])} 个文件")
        
        if status["untracked"]:
            lines.append(f"未跟踪: {len(status['untracked'])} 个文件")
        
        if not lines:
            return "工作区干净，没有变更"
        
        return "\n".join(lines)


# ========== 便捷函数 ==========

def create_git_integration(
    auto_commit: str = "disabled",
    repo_path: Optional[str] = None
) -> GitIntegration:
    """
    便捷创建 Git 集成
    
    Args:
        auto_commit: 自动提交模式 - "disabled", "manual", "on_success", "every_turn"
        repo_path: 仓库路径
    """
    config = GitConfig(
        auto_commit=GitAutoCommitMode(auto_commit),
        repo_path=Path(repo_path) if repo_path else None
    )
    return GitIntegration(config)


def quick_commit(message: str, repo_path: Optional[str] = None) -> GitOperationResult:
    """快速提交"""
    git = create_git_integration(repo_path=repo_path)
    return git.smart_commit(message=message)


def get_repo_status(repo_path: Optional[str] = None) -> Dict[str, Any]:
    """获取仓库状态"""
    git = create_git_integration(repo_path=repo_path)
    return git.get_status_parsed()
