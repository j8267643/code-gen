"""
Memory system for Claude Code
Based on memdir/ from TypeScript project
"""
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import json
import os
from enum import Enum


class MemoryType(str, Enum):
    """Memory types"""
    USER = "user"  # User explicitly written
    FEEDBACK = "feedback"  # Model feedback
    PROJECT = "project"  # Project related
    REFERENCE = "reference"  # Reference materials


@dataclass
class Memory:
    """A memory entry"""
    id: str
    type: MemoryType
    content: str
    path: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class MemorySystem:
    """Memory system for Claude Code"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.memdir_path = work_dir / ".code_gen" / "memdir"
        self.memories: list[Memory] = []
        self._load_memories()
    
    def _load_memories(self):
        """Load memories from disk"""
        self.memdir_path.mkdir(parents=True, exist_ok=True)
        
        # Load user memories
        user_mem_path = self.memdir_path / "user"
        if user_mem_path.exists():
            for file in user_mem_path.rglob("*.md"):
                self._load_memory_file(file, MemoryType.USER)
        
        # Load project memories
        project_mem_path = self.memdir_path / "project"
        if project_mem_path.exists():
            for file in project_mem_path.rglob("*.md"):
                self._load_memory_file(file, MemoryType.PROJECT)
        
        # Load reference memories
        reference_mem_path = self.memdir_path / "reference"
        if reference_mem_path.exists():
            for file in reference_mem_path.rglob("*.md"):
                self._load_memory_file(file, MemoryType.REFERENCE)
    
    def _load_memory_file(self, path: Path, memory_type: MemoryType):
        """Load a memory file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            memory = Memory(
                id=path.stem,
                type=memory_type,
                content=content,
                path=str(path)
            )
            self.memories.append(memory)
        except Exception as e:
            print(f"Failed to load memory file {path}: {e}")
    
    def add_memory(self, content: str, memory_type: MemoryType, 
                   path: str = "", tags: list = None) -> Memory:
        """Add a new memory"""
        if tags is None:
            tags = []
        
        # Generate ID
        memory_id = f"{memory_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create memory
        memory = Memory(
            id=memory_id,
            type=memory_type,
            content=content,
            path=path or str(self.memdir_path / memory_type / f"{memory_id}.md"),
            tags=tags
        )
        
        # Save to disk
        self._save_memory(memory)
        
        # Add to list
        self.memories.append(memory)
        
        return memory
    
    def _save_memory(self, memory: Memory):
        """Save memory to disk"""
        memory_path = Path(memory.path)
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(memory_path, 'w', encoding='utf-8') as f:
            f.write(memory.content)
    
    def get_memories_by_type(self, memory_type: MemoryType) -> list[Memory]:
        """Get memories by type"""
        return [m for m in self.memories if m.type == memory_type]
    
    def search_memories(self, query: str, limit: int = 10) -> list[Memory]:
        """Search memories by query"""
        results = []
        query_lower = query.lower()
        
        for memory in self.memories:
            if (query_lower in memory.content.lower() or 
                any(query_lower in tag.lower() for tag in memory.tags)):
                results.append(memory)
                
                if len(results) >= limit:
                    break
        
        return results
    
    def get_recent_memories(self, count: int = 10) -> list[Memory]:
        """Get recent memories"""
        return sorted(
            self.memories,
            key=lambda m: m.created_at,
            reverse=True
        )[:count]
    
    def dream(self) -> str:
        """Nightly dream - extract insights from memories"""
        # Placeholder for dream functionality
        # In real implementation, this would use an agent to analyze memories
        # and extract insights
        
        insights = []
        for memory in self.memories:
            if memory.type == MemoryType.FEEDBACK:
                insights.append(f"Feedback: {memory.content[:100]}")
        
        if not insights:
            return "No significant insights from memories."
        
        return "\n".join(insights[:5])
    
    async def dream_async(self) -> str:
        """Async nightly dream - extract insights from memories using AI"""
        from code_gen.dream import DreamMemorySystem
        
        # Run the four-stage dream process
        dream_system = DreamMemorySystem(self.work_dir)
        
        try:
            result = await dream_system.run_dream_process()
            
            # Return formatted result
            if result.get("status") == "skipped":
                return result.get("message", "No memories to analyze.")
            
            # Format the dream result
            output = "# Dream Memory Result\n\n"
            output += f"**Timestamp:** {result.get('timestamp', '')}\n\n"
            
            # Add statistics
            output += "## Statistics\n\n"
            stages = result.get('stages', {})
            output += f"- Fragments Collected: {stages.get('fragment_collection', 0)}\n"
            output += f"- Associations Found: {stages.get('association_analysis', 0)}\n"
            output += f"- Knowledge Items Extracted: {stages.get('knowledge_extraction', 0)}\n"
            output += f"- Memories Indexed: {stages.get('memory_indexing', 0)}\n\n"
            
            # Add summary
            summary = result.get('summary', '')
            if summary:
                output += "## Summary\n\n"
                output += summary
            
            return output
            
        except Exception as e:
            # Fallback to simple dream if AI fails
            return self._simple_dream()
    
    def _simple_dream(self) -> str:
        """Simple dream fallback without AI"""
        insights = []
        for memory in self.memories:
            if memory.type == MemoryType.FEEDBACK:
                insights.append(f"Feedback: {memory.content[:100]}")
        
        if not insights:
            return "No significant insights from memories."
        
        return "\n".join(insights[:5])
    
    def clear_memories(self, memory_type: Optional[MemoryType] = None):
        """Clear memories"""
        if memory_type:
            self.memories = [m for m in self.memories if m.type != memory_type]
        else:
            self.memories = []
        
        # Rewrite memory file
        self._rewrite_memory_file()
    
    def _rewrite_memory_file(self):
        """Rewrite memory file"""
        # Placeholder for rewriting memory file
        pass


# Global memory system instance
memory_system = None
