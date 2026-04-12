#!/usr/bin/env python3
"""
Migrate old memory system to new advanced memory system
"""
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from code_gen.memory import MemorySystem, MemoryType
from code_gen.memory_system import AdvancedMemorySystem, MemoryCategory


def migrate_memories(work_dir: Path):
    """Migrate from old to new memory system"""
    print("Starting memory migration...")
    
    # Initialize both systems
    old_system = MemorySystem(work_dir)
    new_system = AdvancedMemorySystem(work_dir)
    
    migrated_count = 0
    
    # Migrate user memories
    print("\nMigrating user memories...")
    for memory in old_system.get_memories_by_type(MemoryType.USER):
        new_system.add_memory(
            content=memory.content,
            category=MemoryCategory.USER_PREF,
            summary=memory.content[:100],
            tags=["migrated", "user"],
            importance=7
        )
        migrated_count += 1
        print(f"  Migrated: {memory.id}")
    
    # Migrate project memories
    print("\nMigrating project memories...")
    for memory in old_system.get_memories_by_type(MemoryType.PROJECT):
        new_system.add_memory(
            content=memory.content,
            category=MemoryCategory.PROJECT,
            summary=memory.content[:100],
            tags=["migrated", "project"],
            importance=6
        )
        migrated_count += 1
        print(f"  Migrated: {memory.id}")
    
    # Migrate reference memories
    print("\nMigrating reference memories...")
    for memory in old_system.get_memories_by_type(MemoryType.REFERENCE):
        new_system.add_memory(
            content=memory.content,
            category=MemoryCategory.KNOWLEDGE,
            summary=memory.content[:100],
            tags=["migrated", "reference"],
            importance=5
        )
        migrated_count += 1
        print(f"  Migrated: {memory.id}")
    
    print(f"\n✓ Migration complete! Migrated {migrated_count} memories")
    
    # Show new system stats
    stats = new_system.get_memory_stats()
    print("\nNew memory system stats:")
    print(f"  Total memories: {stats['total']}")
    print(f"  By category: {stats['by_category']}")
    print(f"  Avg importance: {stats['avg_importance']}")


if __name__ == "__main__":
    work_dir = Path.cwd()
    migrate_memories(work_dir)
