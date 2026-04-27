"""
Context compression for Claude Code
Based on services/compact/ from TypeScript project
"""
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class CompressionType(str, Enum):
    """Compression types"""
    FULL = "full"  # Complete compression with forked agent
    MICRO = "micro"  # Only compress tool results
    AUTO = "auto"  # Automatic based on token usage


@dataclass
class CompressionResult:
    """Compression result"""
    success: bool
    original_tokens: int
    compressed_tokens: int
    compressed_content: str
    compression_type: CompressionType


class ContextCompressor:
    """Context compressor for reducing token usage"""
    
    def __init__(self, max_tokens: int = 4096):
        self.max_tokens = max_tokens
        self.compression_threshold = 0.9  # Compress when 90% of tokens used
        self.diminishing_threshold = 500  # Diminishing returns threshold
    
    def should_compress(self, token_usage: int) -> bool:
        """Check if compression is needed"""
        return token_usage > self.max_tokens * self.compression_threshold
    
    def get_compression_type(self, token_usage: int) -> CompressionType:
        """Get appropriate compression type"""
        if token_usage > self.max_tokens * 0.95:
            return CompressionType.FULL
        elif token_usage > self.max_tokens * 0.8:
            return CompressionType.MICRO
        else:
            return CompressionType.AUTO
    
    async def compress_full(self, context: str) -> CompressionResult:
        """Full compression with forked agent"""
        # Placeholder for full compression
        # In real implementation, this would use a forked agent to generate summary
        original_tokens = len(context.split())
        compressed_tokens = original_tokens // 3  # Rough estimate
        
        # Generate summary (placeholder)
        compressed_content = f"[Compressed context: {original_tokens} tokens -> {compressed_tokens} tokens]\n" + context[:500]
        
        return CompressionResult(
            success=True,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compressed_content=compressed_content,
            compression_type=CompressionType.FULL
        )
    
    async def compress_micro(self, tool_results: list[dict]) -> CompressionResult:
        """Micro compression - only compress tool results"""
        # Placeholder for micro compression
        original_tokens = sum(len(str(r).split()) for r in tool_results)
        compressed_tokens = original_tokens // 2
        
        # Compress tool results (placeholder)
        compressed_results = []
        for result in tool_results:
            content = str(result.get("content", ""))
            compressed_results.append({
                "type": result.get("type", "tool_result"),
                "content": content[:500] + f"... [compressed from {len(content)} chars]"
            })
        
        return CompressionResult(
            success=True,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compressed_content=str(compressed_results),
            compression_type=CompressionType.MICRO
        )
    
    async def compress_auto(self, context: str, token_usage: int) -> CompressionResult:
        """Automatic compression based on token usage"""
        compression_type = self.get_compression_type(token_usage)
        
        if compression_type == CompressionType.FULL:
            return await self.compress_full(context)
        elif compression_type == CompressionType.MICRO:
            # For micro compression, we need tool results
            return await self.compress_micro([])
        else:
            # No compression needed
            return CompressionResult(
                success=True,
                original_tokens=len(context.split()),
                compressed_tokens=len(context.split()),
                compressed_content=context,
                compression_type=CompressionType.AUTO
            )
    
    def should_stop_compression(self, token_usage: int, compressed_tokens: int) -> bool:
        """Check if compression should stop (diminishing returns)"""
        if compressed_tokens < self.diminishing_threshold:
            return True
        return False


# Global compressor instance
compressor = ContextCompressor()
