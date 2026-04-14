"""
Discovery Cache - 发现缓存

基于 GSD-2 的 DiscoveryCache 设计，提供：
1. 带 TTL 的磁盘缓存
2. 原子写入避免数据损坏
3. 自动过期检测
4. 按类别隔离缓存

使用场景:
- 缓存模型发现结果
- 缓存工具列表
- 缓存配置信息

使用示例:
    >>> from discovery_cache import DiscoveryCache
    >>> 
    >>> cache = DiscoveryCache("./cache")
    >>> 
    >>> # 存储数据
    >>> cache.set("models", ["gpt-4", "gpt-3.5"], ttl_hours=24)
    >>> 
    >>> # 获取数据
    >>> if not cache.is_stale("models"):
    ...     models = cache.get("models")
    >>> 
    >>> # 清除过期数据
    >>> cache.clear_stale()
"""
import json
import os
import tempfile
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import shutil


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    data: Any
    created_at: datetime
    expires_at: Optional[datetime]
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "key": self.key,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "version": self.version,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """从字典创建"""
        return cls(
            key=data["key"],
            data=data["data"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            version=data.get("version", 1),
            metadata=data.get("metadata", {})
        )


class DiscoveryCache:
    """
    发现缓存
    
    磁盘缓存，支持 TTL 和原子写入
    """
    
    CACHE_VERSION = 1
    
    def __init__(
        self,
        cache_dir: Union[str, Path],
        default_ttl_hours: float = 24.0
    ):
        """
        初始化缓存
        
        Args:
            cache_dir: 缓存目录
            default_ttl_hours: 默认 TTL（小时）
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl_hours = default_ttl_hours
        
        # 内存中的缓存
        self._memory_cache: Dict[str, CacheEntry] = {}
        
        # 加载所有缓存
        self._load_all()
    
    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用安全的文件名
        safe_key = self._sanitize_key(key)
        return self.cache_dir / f"{safe_key}.json"
    
    def _sanitize_key(self, key: str) -> str:
        """清理键名，使其适合作为文件名"""
        # 替换不安全字符
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
        return safe[:100]  # 限制长度
    
    def _load_all(self) -> None:
        """加载所有缓存文件"""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 验证版本
                    if data.get("version") != self.CACHE_VERSION:
                        continue
                    
                    entry = CacheEntry.from_dict(data)
                    self._memory_cache[entry.key] = entry
                    
                except (json.JSONDecodeError, KeyError, ValueError):
                    # 损坏的缓存文件，删除
                    try:
                        cache_file.unlink()
                    except:
                        pass
        except Exception:
            pass
    
    def _save_atomic(self, key: str, entry: CacheEntry) -> None:
        """
        原子保存缓存条目
        
        写入临时文件然后重命名，避免部分写入
        """
        cache_path = self._get_cache_path(key)
        temp_path = cache_path.with_suffix('.tmp')
        
        try:
            # 写入临时文件
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(entry.to_dict(), f, indent=2, ensure_ascii=False)
            
            # 原子重命名
            temp_path.replace(cache_path)
            
        except Exception as e:
            # 清理临时文件
            try:
                temp_path.unlink(missing_ok=True)
            except:
                pass
            raise IOError(f"Failed to save cache for {key}: {e}")
    
    def set(
        self,
        key: str,
        data: Any,
        ttl_hours: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        设置缓存
        
        Args:
            key: 缓存键
            data: 缓存数据
            ttl_hours: TTL（小时），None 表示永不过期
            metadata: 元数据
        """
        now = datetime.now()
        
        if ttl_hours is not None:
            expires_at = now + timedelta(hours=ttl_hours)
        else:
            expires_at = None
        
        entry = CacheEntry(
            key=key,
            data=data,
            created_at=now,
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        # 保存到内存
        self._memory_cache[key] = entry
        
        # 保存到磁盘
        self._save_atomic(key, entry)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存
        
        Args:
            key: 缓存键
            default: 默认值
        
        Returns:
            缓存数据或默认值
        """
        entry = self._memory_cache.get(key)
        
        if entry is None:
            return default
        
        if entry.is_expired():
            # 过期，删除
            self.delete(key)
            return default
        
        return entry.data
    
    def get_entry(self, key: str) -> Optional[CacheEntry]:
        """
        获取完整的缓存条目
        
        Args:
            key: 缓存键
        
        Returns:
            缓存条目或 None
        """
        entry = self._memory_cache.get(key)
        
        if entry and entry.is_expired():
            self.delete(key)
            return None
        
        return entry
    
    def is_stale(self, key: str) -> bool:
        """
        检查缓存是否过期
        
        Args:
            key: 缓存键
        
        Returns:
            是否过期（不存在也视为过期）
        """
        entry = self._memory_cache.get(key)
        
        if entry is None:
            return True
        
        return entry.is_expired()
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
        
        Returns:
            是否成功删除
        """
        # 从内存删除
        if key in self._memory_cache:
            del self._memory_cache[key]
        
        # 从磁盘删除
        cache_path = self._get_cache_path(key)
        try:
            cache_path.unlink(missing_ok=True)
            return True
        except:
            return False
    
    def clear(self) -> None:
        """清除所有缓存"""
        # 清除内存
        self._memory_cache.clear()
        
        # 清除磁盘
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                except:
                    pass
        except:
            pass
    
    def clear_stale(self) -> int:
        """
        清除过期缓存
        
        Returns:
            清除的条目数
        """
        removed = 0
        
        # 检查内存中的条目
        expired_keys = [
            key for key, entry in self._memory_cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            self.delete(key)
            removed += 1
        
        # 检查磁盘上的文件
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    entry = CacheEntry.from_dict(data)
                    if entry.is_expired():
                        cache_file.unlink()
                        removed += 1
                        
                except:
                    # 损坏的文件，删除
                    try:
                        cache_file.unlink()
                        removed += 1
                    except:
                        pass
        except:
            pass
        
        return removed
    
    def keys(self) -> List[str]:
        """
        获取所有缓存键
        
        Returns:
            键列表
        """
        # 过滤掉过期的
        valid_keys = []
        for key, entry in list(self._memory_cache.items()):
            if entry.is_expired():
                self.delete(key)
            else:
                valid_keys.append(key)
        
        return valid_keys
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计
        
        Returns:
            统计信息
        """
        total = len(self._memory_cache)
        expired = sum(1 for e in self._memory_cache.values() if e.is_expired())
        
        # 计算总大小
        total_size = 0
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                total_size += cache_file.stat().st_size
        except:
            pass
        
        return {
            "total_entries": total,
            "expired_entries": expired,
            "valid_entries": total - expired,
            "cache_dir": str(self.cache_dir),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
    
    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存元数据
        
        Args:
            key: 缓存键
        
        Returns:
            元数据或 None
        """
        entry = self.get_entry(key)
        return entry.metadata if entry else None
    
    def update_metadata(
        self,
        key: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        更新缓存元数据
        
        Args:
            key: 缓存键
            metadata: 新元数据
        
        Returns:
            是否成功
        """
        entry = self.get_entry(key)
        if entry is None:
            return False
        
        entry.metadata.update(metadata)
        self._save_atomic(key, entry)
        return True
    
    def touch(self, key: str, ttl_hours: Optional[float] = None) -> bool:
        """
        更新缓存时间戳
        
        Args:
            key: 缓存键
            ttl_hours: 新的 TTL
        
        Returns:
            是否成功
        """
        entry = self.get_entry(key)
        if entry is None:
            return False
        
        entry.created_at = datetime.now()
        
        if ttl_hours is not None:
            entry.expires_at = entry.created_at + timedelta(hours=ttl_hours)
        
        self._save_atomic(key, entry)
        return True


# 便捷函数
def get_default_cache() -> DiscoveryCache:
    """获取默认缓存实例"""
    return DiscoveryCache(".cache/discovery")
