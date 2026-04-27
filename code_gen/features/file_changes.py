"""
文件变更预览系统
提供文件变更的 diff 预览、原子性操作和回滚功能
"""
import os
import shutil
import hashlib
import json
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
import difflib


class ChangeStatus(Enum):
    """变更状态"""
    PENDING = "pending"      # 待确认
    APPLIED = "applied"      # 已应用
    ROLLED_BACK = "rolled_back"  # 已回滚
    FAILED = "failed"        # 失败


class ChangeType(Enum):
    """变更类型"""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"


@dataclass
class FileChange:
    """文件变更记录"""
    change_id: str = field(default_factory=lambda: hashlib.md5(str(datetime.now()).encode()).hexdigest()[:12])
    change_type: ChangeType = ChangeType.MODIFY
    file_path: Path = field(default_factory=Path)
    original_content: Optional[str] = None
    new_content: Optional[str] = None
    original_hash: Optional[str] = None
    new_hash: Optional[str] = None
    status: ChangeStatus = ChangeStatus.PENDING
    timestamp: datetime = field(default_factory=datetime.now)
    description: str = ""
    
    def __post_init__(self):
        if self.original_content is not None:
            self.original_hash = hashlib.md5(self.original_content.encode()).hexdigest()[:16]
        if self.new_content is not None:
            self.new_hash = hashlib.md5(self.new_content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type.value,
            "file_path": str(self.file_path),
            "original_hash": self.original_hash,
            "new_hash": self.new_hash,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description
        }


@dataclass
class ChangeBatch:
    """变更批次（原子性操作单元）"""
    batch_id: str = field(default_factory=lambda: hashlib.md5(str(datetime.now()).encode()).hexdigest()[:12])
    changes: List[FileChange] = field(default_factory=list)
    description: str = ""
    status: ChangeStatus = ChangeStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    applied_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None
    
    def add_change(self, change: FileChange):
        """添加变更到批次"""
        self.changes.append(change)
    
    def get_summary(self) -> str:
        """获取批次摘要"""
        counts = {}
        for change in self.changes:
            counts[change.change_type.value] = counts.get(change.change_type.value, 0) + 1
        
        parts = []
        for change_type, count in counts.items():
            parts.append(f"{count} {change_type}")
        return f"{self.description}: {', '.join(parts)}"


class FileChangeManager:
    """文件变更管理器"""
    
    def __init__(self, work_dir: Path, backup_dir: Optional[Path] = None):
        self.work_dir = work_dir
        self.backup_dir = backup_dir or (work_dir / ".code_gen" / "backups")
        self.batches: List[ChangeBatch] = []
        self.current_batch: Optional[ChangeBatch] = None
        self._ensure_backup_dir()
    
    def _ensure_backup_dir(self):
        """确保备份目录存在"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def start_batch(self, description: str = "") -> ChangeBatch:
        """开始一个新的变更批次"""
        self.current_batch = ChangeBatch(description=description)
        return self.current_batch
    
    def add_file_change(
        self,
        file_path: Path,
        new_content: str,
        change_type: ChangeType = ChangeType.MODIFY,
        description: str = ""
    ) -> FileChange:
        """添加文件变更"""
        if self.current_batch is None:
            self.start_batch("Auto batch")
        
        full_path = self.work_dir / file_path
        
        # 读取原始内容
        original_content = None
        if full_path.exists() and change_type != ChangeType.CREATE:
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
            except:
                pass
        
        change = FileChange(
            change_type=change_type,
            file_path=file_path,
            original_content=original_content,
            new_content=new_content,
            description=description
        )
        
        self.current_batch.add_change(change)
        return change
    
    def preview_changes(self, batch: Optional[ChangeBatch] = None) -> str:
        """生成变更预览（diff 格式）"""
        batch = batch or self.current_batch
        if not batch or not batch.changes:
            return "No changes to preview"
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"Change Preview: {batch.description}")
        lines.append("=" * 60)
        lines.append("")
        
        for change in batch.changes:
            lines.append(f"File: {change.file_path}")
            lines.append(f"Type: {change.change_type.value}")
            lines.append(f"Description: {change.description}")
            lines.append("-" * 40)
            
            if change.change_type == ChangeType.CREATE:
                lines.append("+++ New file")
                lines.extend(self._format_new_file(change.new_content))
            elif change.change_type == ChangeType.DELETE:
                lines.append("--- Deleted file")
                if change.original_content:
                    lines.extend(self._format_deleted_file(change.original_content))
            elif change.change_type == ChangeType.MODIFY:
                diff = self._generate_diff(
                    change.original_content or "",
                    change.new_content or "",
                    str(change.file_path)
                )
                lines.extend(diff)
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_new_file(self, content: str) -> List[str]:
        """格式化新文件内容"""
        lines = []
        for i, line in enumerate(content.split('\n'), 1):
            lines.append(f"+ {line}")
        return lines
    
    def _format_deleted_file(self, content: str) -> List[str]:
        """格式化删除的文件内容"""
        lines = []
        for i, line in enumerate(content.split('\n'), 1):
            lines.append(f"- {line}")
        return lines
    
    def _generate_diff(self, original: str, new: str, filename: str) -> List[str]:
        """生成 unified diff"""
        original_lines = original.split('\n')
        new_lines = new.split('\n')
        
        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        )
        
        return list(diff)
    
    def apply_batch(self, batch: Optional[ChangeBatch] = None) -> bool:
        """应用变更批次（原子性操作）"""
        batch = batch or self.current_batch
        if not batch:
            return False
        
        # 先创建备份
        if not self._create_backup(batch):
            return False
        
        # 尝试应用所有变更
        applied_changes = []
        try:
            for change in batch.changes:
                if self._apply_single_change(change):
                    applied_changes.append(change)
                    change.status = ChangeStatus.APPLIED
                else:
                    raise Exception(f"Failed to apply change: {change.file_path}")
            
            batch.status = ChangeStatus.APPLIED
            batch.applied_at = datetime.now()
            self.batches.append(batch)
            self.current_batch = None
            return True
            
        except Exception as e:
            # 回滚已应用的变更
            for change in reversed(applied_changes):
                self._rollback_single_change(change)
            
            batch.status = ChangeStatus.FAILED
            return False
    
    def _create_backup(self, batch: ChangeBatch) -> bool:
        """为批次创建备份"""
        try:
            backup_path = self.backup_dir / batch.batch_id
            backup_path.mkdir(parents=True, exist_ok=True)
            
            backup_data = {
                "batch": asdict(batch),
                "files": {}
            }
            
            for change in batch.changes:
                if change.original_content is not None:
                    backup_data["files"][str(change.file_path)] = change.original_content
                    # 也保存到文件
                    file_backup_path = backup_path / f"{change.change_id}.txt"
                    with open(file_backup_path, 'w', encoding='utf-8') as f:
                        f.write(change.original_content)
            
            # 保存元数据
            meta_path = backup_path / "meta.json"
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
            
            return True
        except Exception as e:
            return False
    
    def _apply_single_change(self, change: FileChange) -> bool:
        """应用单个变更"""
        try:
            full_path = self.work_dir / change.file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            if change.change_type == ChangeType.DELETE:
                if full_path.exists():
                    full_path.unlink()
            else:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(change.new_content or "")
            
            return True
        except Exception as e:
            return False
    
    def rollback_batch(self, batch_id: str) -> bool:
        """回滚批次"""
        batch = None
        for b in self.batches:
            if b.batch_id == batch_id:
                batch = b
                break
        
        if not batch or batch.status != ChangeStatus.APPLIED:
            return False
        
        # 从备份恢复
        backup_path = self.backup_dir / batch_id
        meta_path = backup_path / "meta.json"
        
        if not meta_path.exists():
            return False
        
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            for change in reversed(batch.changes):
                self._rollback_single_change(change)
            
            batch.status = ChangeStatus.ROLLED_BACK
            batch.rolled_back_at = datetime.now()
            return True
        except Exception as e:
            return False
    
    def _rollback_single_change(self, change: FileChange) -> bool:
        """回滚单个变更"""
        try:
            full_path = self.work_dir / change.file_path
            
            if change.change_type == ChangeType.CREATE:
                if full_path.exists():
                    full_path.unlink()
            elif change.change_type == ChangeType.DELETE:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(change.original_content or "")
            else:  # MODIFY
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(change.original_content or "")
            
            change.status = ChangeStatus.ROLLED_BACK
            return True
        except Exception as e:
            return False
    
    def get_batch_history(self) -> List[Dict]:
        """获取批次历史"""
        return [{
            "batch_id": b.batch_id,
            "description": b.description,
            "status": b.status.value,
            "changes_count": len(b.changes),
            "created_at": b.created_at.isoformat(),
            "applied_at": b.applied_at.isoformat() if b.applied_at else None
        } for b in self.batches]
    
    def discard_current_batch(self):
        """丢弃当前批次"""
        self.current_batch = None
