"""
Artifact Manager - 制品管理器

基于 GSD-2 的 ArtifactManager 设计，提供：
1. 会话级别的文件存储
2. 支持恢复时 ID 连续性
3. 制品元数据管理
4. 自动垃圾回收
5. 制品版本控制

使用场景:
- 存储代码生成结果
- 保存 Agent 输出文件
- 管理会话附件

使用示例:
    >>> from code_gen.agents.artifact_manager import ArtifactManager, Artifact
    >>> 
    >>> manager = ArtifactManager("./artifacts")
    >>> 
    >>> # 创建制品
    >>> artifact = manager.create(
    ...     name="generated_code.py",
    ...     content="print('hello')",
    ...     artifact_type="code"
    ... )
    >>> 
    >>> # 读取制品
    >>> content = manager.read(artifact.id)
    >>> 
    >>> # 列出制品
    >>> artifacts = manager.list_artifacts()
"""
import json
import hashlib
import shutil
from typing import Dict, Any, Optional, List, Union, BinaryIO
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
import mimetypes


class ArtifactType(Enum):
    """制品类型"""
    CODE = "code"
    TEXT = "text"
    IMAGE = "image"
    DATA = "data"
    CONFIG = "config"
    LOG = "log"
    OTHER = "other"


@dataclass
class Artifact:
    """制品"""
    id: str
    name: str
    artifact_type: ArtifactType
    created_at: datetime
    updated_at: datetime
    size_bytes: int = 0
    content_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    version: int = 1
    
    @property
    def extension(self) -> str:
        """获取文件扩展名"""
        return Path(self.name).suffix
    
    @property
    def mime_type(self) -> str:
        """获取 MIME 类型"""
        mime, _ = mimetypes.guess_type(self.name)
        return mime or "application/octet-stream"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "artifact_type": self.artifact_type.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "size_bytes": self.size_bytes,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
            "session_id": self.session_id,
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
        """从字典创建"""
        return cls(
            id=data["id"],
            name=data["name"],
            artifact_type=ArtifactType(data["artifact_type"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            size_bytes=data["size_bytes"],
            content_hash=data["content_hash"],
            metadata=data.get("metadata", {}),
            session_id=data.get("session_id"),
            version=data.get("version", 1)
        )


@dataclass
class ArtifactVersion:
    """制品版本"""
    version: int
    created_at: datetime
    content_hash: str
    size_bytes: int
    change_message: str = ""


class ArtifactManager:
    """
    制品管理器
    
    管理会话级别的文件存储
    """
    
    def __init__(
        self,
        artifacts_dir: Union[str, Path],
        session_id: Optional[str] = None
    ):
        """
        初始化制品管理器
        
        Args:
            artifacts_dir: 制品目录
            session_id: 会话 ID
        """
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # 内容目录
        self.content_dir = self.artifacts_dir / "content"
        self.content_dir.mkdir(exist_ok=True)
        
        # 元数据目录
        self.meta_dir = self.artifacts_dir / "meta"
        self.meta_dir.mkdir(exist_ok=True)
        
        # 版本目录
        self.versions_dir = self.artifacts_dir / "versions"
        self.versions_dir.mkdir(exist_ok=True)
        
        self.session_id = session_id
        
        # 内存中的制品索引
        self._artifacts: Dict[str, Artifact] = {}
        
        # 加载现有制品
        self._load_index()
    
    def _get_content_path(self, content_hash: str) -> Path:
        """获取内容文件路径"""
        # 使用哈希前2位作为子目录
        subdir = content_hash[:2]
        return self.content_dir / subdir / content_hash
    
    def _get_meta_path(self, artifact_id: str) -> Path:
        """获取元数据文件路径"""
        return self.meta_dir / f"{artifact_id}.json"
    
    def _compute_hash(self, content: Union[str, bytes]) -> str:
        """计算内容哈希"""
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()
    
    def _load_index(self) -> None:
        """加载制品索引"""
        try:
            for meta_file in self.meta_dir.glob("*.json"):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    artifact = Artifact.from_dict(data)
                    self._artifacts[artifact.id] = artifact
                except (json.JSONDecodeError, KeyError):
                    pass
        except Exception:
            pass
    
    def _save_content(self, content_hash: str, content: Union[str, bytes]) -> Path:
        """
        保存内容（内容寻址）
        
        相同内容只保存一次
        """
        content_path = self._get_content_path(content_hash)
        
        # 如果已存在，直接返回
        if content_path.exists():
            return content_path
        
        # 创建子目录
        content_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入内容
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        with open(content_path, 'wb') as f:
            f.write(content)
        
        return content_path
    
    def _save_metadata(self, artifact: Artifact) -> None:
        """保存元数据"""
        meta_path = self._get_meta_path(artifact.id)
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(artifact.to_dict(), f, indent=2, ensure_ascii=False)
    
    def create(
        self,
        name: str,
        content: Union[str, bytes],
        artifact_type: ArtifactType = ArtifactType.OTHER,
        metadata: Optional[Dict[str, Any]] = None,
        artifact_id: Optional[str] = None
    ) -> Artifact:
        """
        创建制品
        
        Args:
            name: 制品名称
            content: 内容
            artifact_type: 类型
            metadata: 元数据
            artifact_id: 指定 ID（用于恢复时保持连续性）
        
        Returns:
            制品对象
        """
        # 计算内容哈希
        content_hash = self._compute_hash(content)
        
        # 保存内容
        self._save_content(content_hash, content)
        
        # 确定大小
        if isinstance(content, str):
            size_bytes = len(content.encode('utf-8'))
        else:
            size_bytes = len(content)
        
        now = datetime.now()
        
        # 创建制品对象
        artifact = Artifact(
            id=artifact_id or self._generate_id(),
            name=name,
            artifact_type=artifact_type,
            created_at=now,
            updated_at=now,
            size_bytes=size_bytes,
            content_hash=content_hash,
            metadata=metadata or {},
            session_id=self.session_id
        )
        
        # 保存
        self._artifacts[artifact.id] = artifact
        self._save_metadata(artifact)
        
        return artifact
    
    def _generate_id(self) -> str:
        """生成唯一 ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def read(self, artifact_id: str) -> Optional[Union[str, bytes]]:
        """
        读取制品内容
        
        Args:
            artifact_id: 制品 ID
        
        Returns:
            内容或 None
        """
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return None
        
        content_path = self._get_content_path(artifact.content_hash)
        
        try:
            with open(content_path, 'rb') as f:
                content = f.read()
            
            # 尝试解码为文本
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                return content
                
        except FileNotFoundError:
            return None
    
    def read_text(self, artifact_id: str) -> Optional[str]:
        """
        读取制品文本内容
        
        Args:
            artifact_id: 制品 ID
        
        Returns:
            文本内容或 None
        """
        content = self.read(artifact_id)
        if content is None:
            return None
        
        if isinstance(content, bytes):
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                return None
        
        return content
    
    def update(
        self,
        artifact_id: str,
        content: Union[str, bytes],
        change_message: str = ""
    ) -> Optional[Artifact]:
        """
        更新制品
        
        Args:
            artifact_id: 制品 ID
            content: 新内容
            change_message: 变更说明
        
        Returns:
            更新后的制品或 None
        """
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return None
        
        # 保存旧版本
        self._save_version(artifact, change_message)
        
        # 计算新哈希
        content_hash = self._compute_hash(content)
        
        # 保存新内容
        self._save_content(content_hash, content)
        
        # 更新制品
        artifact.content_hash = content_hash
        artifact.updated_at = datetime.now()
        artifact.version += 1
        
        if isinstance(content, str):
            artifact.size_bytes = len(content.encode('utf-8'))
        else:
            artifact.size_bytes = len(content)
        
        # 保存
        self._save_metadata(artifact)
        
        return artifact
    
    def _save_version(self, artifact: Artifact, message: str) -> None:
        """保存版本"""
        version_data = {
            "version": artifact.version,
            "created_at": artifact.updated_at.isoformat(),
            "content_hash": artifact.content_hash,
            "size_bytes": artifact.size_bytes,
            "change_message": message
        }
        
        version_path = (
            self.versions_dir / 
            f"{artifact.id}_v{artifact.version}.json"
        )
        
        with open(version_path, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2)
    
    def delete(self, artifact_id: str) -> bool:
        """
        删除制品
        
        Args:
            artifact_id: 制品 ID
        
        Returns:
            是否成功
        """
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return False
        
        # 从内存删除
        del self._artifacts[artifact_id]
        
        # 删除元数据
        meta_path = self._get_meta_path(artifact_id)
        try:
            meta_path.unlink(missing_ok=True)
        except:
            pass
        
        # 注意：内容文件不删除（可能被其他制品引用）
        
        return True
    
    def get(self, artifact_id: str) -> Optional[Artifact]:
        """
        获取制品信息
        
        Args:
            artifact_id: 制品 ID
        
        Returns:
            制品信息或 None
        """
        return self._artifacts.get(artifact_id)
    
    def list_artifacts(
        self,
        artifact_type: Optional[ArtifactType] = None,
        session_id: Optional[str] = None
    ) -> List[Artifact]:
        """
        列出品
        
        Args:
            artifact_type: 过滤类型
            session_id: 过滤会话
        
        Returns:
            制品列表
        """
        artifacts = list(self._artifacts.values())
        
        if artifact_type:
            artifacts = [a for a in artifacts if a.artifact_type == artifact_type]
        
        if session_id:
            artifacts = [a for a in artifacts if a.session_id == session_id]
        
        # 按更新时间排序
        artifacts.sort(key=lambda a: a.updated_at, reverse=True)
        
        return artifacts
    
    def exists(self, artifact_id: str) -> bool:
        """
        检查制品是否存在
        
        Args:
            artifact_id: 制品 ID
        
        Returns:
            是否存在
        """
        return artifact_id in self._artifacts
    
    def get_path(self, artifact_id: str) -> Optional[Path]:
        """
        获取制品文件路径
        
        Args:
            artifact_id: 制品 ID
        
        Returns:
            文件路径或 None
        """
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return None
        
        return self._get_content_path(artifact.content_hash)
    
    def export(self, artifact_id: str, destination: Union[str, Path]) -> bool:
        """
        导出制品到文件
        
        Args:
            artifact_id: 制品 ID
            destination: 目标路径
        
        Returns:
            是否成功
        """
        source_path = self.get_path(artifact_id)
        if not source_path:
            return False
        
        try:
            shutil.copy2(source_path, destination)
            return True
        except:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息
        """
        total_size = sum(a.size_bytes for a in self._artifacts.values())
        
        by_type = {}
        for a in self._artifacts.values():
            type_name = a.artifact_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        return {
            "total_artifacts": len(self._artifacts),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_type": by_type,
            "artifacts_dir": str(self.artifacts_dir)
        }
    
    def gc(self) -> int:
        """
        垃圾回收 - 删除未被引用的内容文件
        
        Returns:
            删除的文件数
        """
        # 获取所有被引用的哈希
        referenced_hashes = {a.content_hash for a in self._artifacts.values()}
        
        removed = 0
        
        try:
            for content_file in self.content_dir.rglob("*"):
                if content_file.is_file():
                    if content_file.name not in referenced_hashes:
                        try:
                            content_file.unlink()
                            removed += 1
                        except:
                            pass
            
            # 清理空目录
            for subdir in self.content_dir.iterdir():
                if subdir.is_dir() and not any(subdir.iterdir()):
                    try:
                        subdir.rmdir()
                    except:
                        pass
                        
        except Exception:
            pass
        
        return removed


# 便捷函数
def create_artifact(
    name: str,
    content: Union[str, bytes],
    artifact_type: str = "other",
    **kwargs
) -> Artifact:
    """便捷函数：创建制品"""
    manager = ArtifactManager(".artifacts")
    return manager.create(
        name=name,
        content=content,
        artifact_type=ArtifactType(artifact_type),
        **kwargs
    )
