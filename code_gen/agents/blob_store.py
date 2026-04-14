"""
Blob Store - 内容寻址存储

基于 GSD-2 的 BlobStore 设计，提供：
1. 使用 SHA-256 哈希作为文件名，自动去重
2. 内容寻址使写入幂等
3. 支持垃圾回收清理未引用的 blob
4. 原子写入避免部分写入

使用场景:
- 存储 Agent 生成的图片、文件等大对象
- 缓存计算结果
- 会话持久化的附件存储

使用示例:
    >>> from blob_store import BlobStore
    >>> 
    >>> store = BlobStore("./blobs")
    >>> 
    >>> # 存储数据
    >>> data = b"Hello, World!"
    >>> result = store.put(data)
    >>> print(result.hash)  # sha256 hash
    >>> print(result.ref)   # blob:sha256:... 格式的引用
    >>> 
    >>> # 读取数据
    >>> blob = store.get(result.hash)
    >>> 
    >>> # 垃圾回收
    >>> removed = store.gc({result.hash})  # 保留引用的 hash
"""
import hashlib
import os
import re
from pathlib import Path
from typing import Optional, Set, Union, BinaryIO
from dataclasses import dataclass
from datetime import datetime


# Blob 引用前缀
BLOB_PREFIX = "blob:sha256:"
SHA256_HEX_RE = re.compile(r'^[a-f0-9]{64}$')


@dataclass
class BlobPutResult:
    """Blob 存储结果"""
    hash: str
    path: Path
    size: int
    
    @property
    def ref(self) -> str:
        """获取 blob 引用格式"""
        return f"{BLOB_PREFIX}{self.hash}"
    
    def __repr__(self) -> str:
        return f"BlobPutResult(hash='{self.hash[:16]}...', size={self.size})"


class BlobStore:
    """
    内容寻址 Blob 存储
    
    文件存储在 `<dir>/<sha256-hex>`，无扩展名。
    SHA-256 哈希基于原始二进制数据计算（非 base64）。
    内容寻址使写入幂等并提供自动去重。
    
    Attributes:
        dir: 存储目录路径
    """
    
    def __init__(self, dir_path: Union[str, Path]):
        """
        初始化 Blob 存储
        
        Args:
            dir_path: 存储目录路径
        """
        self.dir = Path(dir_path)
        self.dir.mkdir(parents=True, exist_ok=True)
    
    def put(self, data: Union[bytes, BinaryIO], expected_hash: Optional[str] = None) -> BlobPutResult:
        """
        写入二进制数据到 blob 存储
        
        幂等操作 - 相同内容产生相同哈希
        
        Args:
            data: 二进制数据或文件对象
            expected_hash: 预期的哈希值（用于验证）
        
        Returns:
            BlobPutResult 包含哈希、路径和大小
        
        Raises:
            ValueError: 如果 expected_hash 与实际哈希不匹配
        """
        # 读取数据
        if hasattr(data, 'read'):
            content = data.read()
            if isinstance(content, str):
                content = content.encode('utf-8')
        else:
            content = data if isinstance(data, bytes) else data.encode('utf-8')
        
        # 计算 SHA-256 哈希
        hash_value = hashlib.sha256(content).hexdigest()
        
        # 验证预期哈希
        if expected_hash and expected_hash != hash_value:
            raise ValueError(
                f"Hash mismatch: expected {expected_hash[:16]}..., "
                f"got {hash_value[:16]}..."
            )
        
        blob_path = self.dir / hash_value
        
        # 原子写入: 使用 'wx' 模式，如果文件已存在则失败
        try:
            with open(blob_path, 'wb') as f:
                f.write(content)
        except FileExistsError:
            # 文件已存在 - 对于内容寻址存储是预期的
            pass
        except Exception as e:
            raise IOError(f"Failed to write blob {hash_value[:16]}...: {e}")
        
        return BlobPutResult(
            hash=hash_value,
            path=blob_path,
            size=len(content)
        )
    
    def put_file(self, file_path: Union[str, Path], move: bool = False) -> BlobPutResult:
        """
        将文件存入 blob 存储
        
        Args:
            file_path: 源文件路径
            move: 是否移动文件而不是复制
        
        Returns:
            BlobPutResult
        """
        file_path = Path(file_path)
        
        # 计算哈希
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        
        hash_value = hasher.hexdigest()
        blob_path = self.dir / hash_value
        
        # 如果文件已存在，直接返回
        if blob_path.exists():
            if move:
                file_path.unlink()  # 删除源文件
            return BlobPutResult(
                hash=hash_value,
                path=blob_path,
                size=blob_path.stat().st_size
            )
        
        # 移动或复制文件
        if move:
            import shutil
            shutil.move(str(file_path), str(blob_path))
        else:
            import shutil
            shutil.copy2(str(file_path), str(blob_path))
        
        return BlobPutResult(
            hash=hash_value,
            path=blob_path,
            size=blob_path.stat().st_size
        )
    
    def get(self, hash_or_ref: str) -> Optional[bytes]:
        """
        通过哈希或引用读取 blob
        
        Args:
            hash_or_ref: SHA-256 哈希或 blob:sha256:... 格式的引用
        
        Returns:
            二进制数据，如果不存在则返回 None
        """
        hash_value = self._extract_hash(hash_or_ref)
        if not hash_value:
            return None
        
        blob_path = self.dir / hash_value
        
        try:
            with open(blob_path, 'rb') as f:
                return f.read()
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"⚠️ 读取 blob 失败 {hash_value[:16]}...: {e}")
            return None
    
    def get_path(self, hash_or_ref: str) -> Optional[Path]:
        """
        获取 blob 文件路径
        
        Args:
            hash_or_ref: SHA-256 哈希或引用
        
        Returns:
            文件路径，如果不存在则返回 None
        """
        hash_value = self._extract_hash(hash_or_ref)
        if not hash_value:
            return None
        
        blob_path = self.dir / hash_value
        return blob_path if blob_path.exists() else None
    
    def has(self, hash_or_ref: str) -> bool:
        """
        检查 blob 是否存在
        
        Args:
            hash_or_ref: SHA-256 哈希或引用
        
        Returns:
            是否存在
        """
        hash_value = self._extract_hash(hash_or_ref)
        if not hash_value:
            return False
        
        return (self.dir / hash_value).exists()
    
    def delete(self, hash_or_ref: str) -> bool:
        """
        删除 blob
        
        Args:
            hash_or_ref: SHA-256 哈希或引用
        
        Returns:
            是否成功删除
        """
        hash_value = self._extract_hash(hash_or_ref)
        if not hash_value:
            return False
        
        blob_path = self.dir / hash_value
        
        try:
            blob_path.unlink()
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"⚠️ 删除 blob 失败 {hash_value[:16]}...: {e}")
            return False
    
    def gc(self, referenced_hashes: Set[str]) -> int:
        """
        垃圾回收 - 删除未被引用的 blob
        
        Args:
            referenced_hashes: 仍被引用的 SHA-256 哈希集合
        
        Returns:
            删除的 blob 数量
        """
        removed = 0
        
        try:
            for entry in self.dir.iterdir():
                if not entry.is_file():
                    continue
                
                # 验证文件名是有效的 SHA-256 哈希
                if not SHA256_HEX_RE.match(entry.name):
                    continue
                
                # 如果未被引用，删除
                if entry.name not in referenced_hashes:
                    try:
                        entry.unlink()
                        removed += 1
                    except Exception:
                        # 尽力删除
                        pass
        except Exception as e:
            print(f"⚠️ 垃圾回收失败: {e}")
        
        return removed
    
    def total_size(self) -> int:
        """
        获取所有 blob 的总大小（字节）
        
        Returns:
            总大小
        """
        total = 0
        
        try:
            for entry in self.dir.iterdir():
                if entry.is_file() and SHA256_HEX_RE.match(entry.name):
                    total += entry.stat().st_size
        except Exception:
            pass
        
        return total
    
    def count(self) -> int:
        """
        获取 blob 数量
        
        Returns:
            blob 数量
        """
        count = 0
        
        try:
            for entry in self.dir.iterdir():
                if entry.is_file() and SHA256_HEX_RE.match(entry.name):
                    count += 1
        except Exception:
            pass
        
        return count
    
    def list_all(self) -> Set[str]:
        """
        列出所有 blob 的哈希
        
        Returns:
            哈希集合
        """
        hashes = set()
        
        try:
            for entry in self.dir.iterdir():
                if entry.is_file() and SHA256_HEX_RE.match(entry.name):
                    hashes.add(entry.name)
        except Exception:
            pass
        
        return hashes
    
    def get_stats(self) -> dict:
        """
        获取存储统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "count": self.count(),
            "total_size": self.total_size(),
            "total_size_mb": round(self.total_size() / (1024 * 1024), 2),
            "dir": str(self.dir)
        }
    
    def _extract_hash(self, hash_or_ref: str) -> Optional[str]:
        """
        从哈希或引用中提取纯哈希值
        
        Args:
            hash_or_ref: SHA-256 哈希或 blob:sha256:... 格式的引用
        
        Returns:
            纯哈希值，如果无效则返回 None
        """
        if hash_or_ref.startswith(BLOB_PREFIX):
            hash_value = hash_or_ref[len(BLOB_PREFIX):]
        else:
            hash_value = hash_or_ref
        
        # 验证哈希格式
        if not SHA256_HEX_RE.match(hash_value):
            return None
        
        return hash_value
    
    @staticmethod
    def compute_hash(data: Union[bytes, str]) -> str:
        """
        计算数据的 SHA-256 哈希
        
        Args:
            data: 二进制数据或字符串
        
        Returns:
            SHA-256 哈希（十六进制）
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def make_ref(hash_value: str) -> str:
        """
        从哈希值创建引用
        
        Args:
            hash_value: SHA-256 哈希
        
        Returns:
            blob:sha256:... 格式的引用
        """
        return f"{BLOB_PREFIX}{hash_value}"


class BlobReference:
    """
    Blob 引用管理器
    
    用于跟踪哪些 blob 被引用，便于垃圾回收
    """
    
    def __init__(self):
        self._refs: Set[str] = set()
    
    def add(self, hash_or_ref: str) -> None:
        """添加引用"""
        hash_value = hash_or_ref
        if hash_or_ref.startswith(BLOB_PREFIX):
            hash_value = hash_or_ref[len(BLOB_PREFIX):]
        if SHA256_HEX_RE.match(hash_value):
            self._refs.add(hash_value)
    
    def remove(self, hash_or_ref: str) -> None:
        """移除引用"""
        hash_value = hash_or_ref
        if hash_or_ref.startswith(BLOB_PREFIX):
            hash_value = hash_or_ref[len(BLOB_PREFIX):]
        self._refs.discard(hash_value)
    
    def has(self, hash_or_ref: str) -> bool:
        """检查是否有引用"""
        hash_value = hash_or_ref
        if hash_or_ref.startswith(BLOB_PREFIX):
            hash_value = hash_or_ref[len(BLOB_PREFIX):]
        return hash_value in self._refs
    
    def get_all(self) -> Set[str]:
        """获取所有引用"""
        return self._refs.copy()
    
    def clear(self) -> None:
        """清除所有引用"""
        self._refs.clear()
    
    def update(self, hashes: Set[str]) -> None:
        """批量更新引用"""
        for h in hashes:
            if SHA256_HEX_RE.match(h):
                self._refs.add(h)
