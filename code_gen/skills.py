"""
Skill system for Claude Code
Based on loadSkillsDir.ts from TypeScript project
"""
from typing import Optional, List, Callable, Dict
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import json
import hashlib
import time
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SkillType(str, Enum):
    """Skill types"""
    CODE_REVIEW = "code_review"
    GIT_COMMIT = "git_commit"
    CODE_SEARCH = "code_search"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"


@dataclass
class Skill:
    """A skill"""
    name: str
    description: str
    path: str
    patterns: list = None
    commands: list = None
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "local"
    metadata: dict = None
    
    def __post_init__(self):
        if self.patterns is None:
            self.patterns = []
        if self.commands is None:
            self.commands = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "patterns": self.patterns,
            "commands": self.commands,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Skill':
        """Create from dictionary"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            path=data.get("path", ""),
            patterns=data.get("patterns", []),
            commands=data.get("commands", []),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            source=data.get("source", "local"),
            metadata=data.get("metadata", {})
        )
    
    def get_hash(self) -> str:
        """Get skill content hash for change detection"""
        content = f"{self.name}:{self.description}:{self.patterns}:{self.commands}"
        return hashlib.md5(content.encode()).hexdigest()


class SkillChange:
    """Skill change event"""
    
    def __init__(self, skill: Skill, change_type: str):
        self.skill = skill
        self.change_type = change_type
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "skill": self.skill.to_dict(),
            "change_type": self.change_type,
            "timestamp": self.timestamp
        }


class SkillChangeDetector:
    """Detect skill changes"""
    
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self._file_hashes: Dict[str, str] = {}
        self._change_handlers: List[Callable] = []
    
    def _get_file_hash(self, path: Path) -> Optional[str]:
        """Get file hash"""
        try:
            with open(path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to get hash for {path}: {e}")
            return None
    
    def _get_all_skill_files(self) -> List[Path]:
        """Get all skill files"""
        if not self.skills_dir.exists():
            return []
        
        return list(self.skills_dir.glob("*.md"))
    
    def detect_changes(self) -> List[SkillChange]:
        """Detect skill changes"""
        changes = []
        current_files = self._get_all_skill_files()
        current_hashes = {}
        
        # Check for new or modified skills
        for file_path in current_files:
            file_hash = self._get_file_hash(file_path)
            if file_hash:
                current_hashes[str(file_path)] = file_hash
                
                if str(file_path) not in self._file_hashes:
                    changes.append(SkillChange(
                        skill=Skill(
                            name=file_path.stem,
                            description="",
                            path=str(file_path),
                            source="local"
                        ),
                        change_type="added"
                    ))
                elif self._file_hashes[str(file_path)] != file_hash:
                    changes.append(SkillChange(
                        skill=Skill(
                            name=file_path.stem,
                            description="",
                            path=str(file_path),
                            source="local"
                        ),
                        change_type="modified"
                    ))
        
        # Check for deleted skills
        for file_path in self._file_hashes:
            if file_path not in current_hashes:
                changes.append(SkillChange(
                    skill=Skill(
                        name=Path(file_path).stem,
                        description="",
                        path=file_path,
                        source="local"
                    ),
                    change_type="deleted"
                ))
        
        self._file_hashes = current_hashes
        return changes
    
    def on_change(self, handler: Callable):
        """Register change handler"""
        self._change_handlers.append(handler)
    
    async def notify_changes(self, changes: List[SkillChange]):
        """Notify change handlers"""
        for handler in self._change_handlers:
            try:
                await handler(changes)
            except Exception as e:
                logger.error(f"Error in change handler: {e}")


class SkillSystem:
    """Skill system for Claude Code"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.skills_dir = work_dir / ".code_gen" / "skills"
        self.skills: dict[str, Skill] = {}
        self._change_detector: Optional[SkillChangeDetector] = None
        self._ensure_skills_dir()
        self._init_change_detector()
    
    def _ensure_skills_dir(self):
        """Ensure skills directory exists"""
        self.skills_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_change_detector(self):
        """Initialize change detector"""
        self._change_detector = SkillChangeDetector(self.skills_dir)
    
    def _create_default_skills(self):
        """Create default skills"""
        # Code review skill
        review_skill = Skill(
            name="code_review",
            description="Review code and suggest improvements",
            path=str(self.skills_dir / "code_review.md"),
            patterns=["review", "review code", "analyze code"],
            commands=["review"],
            source="bundled"
        )
        
        # Git commit skill
        commit_skill = Skill(
            name="git_commit",
            description="Generate commit messages and commit changes",
            path=str(self.skills_dir / "git_commit.md"),
            patterns=["commit", "git commit", "commit changes"],
            commands=["commit"],
            source="bundled"
        )
        
        # Code search skill
        search_skill = Skill(
            name="code_search",
            description="Search for code patterns",
            path=str(self.skills_dir / "code_search.md"),
            patterns=["search", "find code", "look for"],
            commands=["search"],
            source="bundled"
        )
        
        self.skills[review_skill.name] = review_skill
        self.skills[commit_skill.name] = commit_skill
        self.skills[search_skill.name] = search_skill
    
    def load_skills(self):
        """Load skills from directory"""
        if not self.skills_dir.exists():
            return
        
        for item in self.skills_dir.iterdir():
            if item.is_file() and item.suffix == '.md':
                self._load_skill_file(item)
        
        # Initialize file hashes for change detection
        if self._change_detector:
            self._change_detector._file_hashes = {
                str(p): self._change_detector._get_file_hash(p)
                for p in self._change_detector._get_all_skill_files()
            }
    
    def load_bundled_skills(self):
        """Load bundled skills"""
        self._create_default_skills()
    
    def load_project_skills(self):
        """Load project-specific skills"""
        project_skills_dir = self.work_dir / ".code_gen" / "skills"
        if project_skills_dir.exists():
            for item in project_skills_dir.iterdir():
                if item.is_file() and item.suffix == '.md':
                    self._load_skill_file(item)
    
    def _load_skill_file(self, path: Path):
        """Load a skill from file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse skill from markdown
            skill = Skill(
                name=path.stem,
                description=self._extract_description(content),
                path=str(path),
                patterns=self._extract_patterns(content),
                commands=self._extract_commands(content),
                source="local"
            )
            
            self.skills[skill.name] = skill
            
        except Exception as e:
            logger.error(f"Failed to load skill from {path}: {e}")
    
    def _extract_description(self, content: str) -> str:
        """Extract description from skill content"""
        lines = content.split('\n')
        if lines:
            return lines[0].strip('#').strip()
        return content[:100]
    
    def _extract_patterns(self, content: str) -> list:
        """Extract patterns from skill content"""
        patterns = []
        in_patterns = False
        
        for line in content.split('\n'):
            line = line.strip()
            if line == '## Patterns':
                in_patterns = True
            elif line == '## Commands':
                in_patterns = False
            elif in_patterns and line.startswith('- '):
                patterns.append(line[2:].strip())
        
        return patterns
    
    def _extract_commands(self, content: str) -> list:
        """Extract commands from skill content"""
        commands = []
        in_commands = False
        
        for line in content.split('\n'):
            line = line.strip()
            if line == '## Commands':
                in_commands = True
            elif in_commands and line.startswith('- '):
                commands.append(line[2:].strip())
        
        return commands
    
    def get_matching_skills(self, input: str) -> list[Skill]:
        """Get skills matching input"""
        matching = []
        input_lower = input.lower()
        
        for skill in self.skills.values():
            if skill.enabled:
                # Check patterns
                for pattern in skill.patterns:
                    if pattern.lower() in input_lower:
                        matching.append(skill)
                        break
        
        return matching
    
    def enable_skill(self, name: str) -> bool:
        """Enable a skill"""
        if name in self.skills:
            self.skills[name].enabled = True
            self.skills[name].updated_at = datetime.now().isoformat()
            return True
        return False
    
    def disable_skill(self, name: str) -> bool:
        """Disable a skill"""
        if name in self.skills:
            self.skills[name].enabled = False
            self.skills[name].updated_at = datetime.now().isoformat()
            return True
        return False
    
    def get_enabled_skills(self) -> list[Skill]:
        """Get enabled skills"""
        return [s for s in self.skills.values() if s.enabled]
    
    def create_skill(self, name: str, description: str, 
                     patterns: list = None, commands: list = None) -> Skill:
        """Create a new skill"""
        if patterns is None:
            patterns = []
        if commands is None:
            commands = []
        
        skill = Skill(
            name=name,
            description=description,
            path=str(self.skills_dir / f"{name}.md"),
            patterns=patterns,
            commands=commands,
            source="local"
        )
        
        # Save skill
        self._save_skill(skill)
        
        # Add to skills
        self.skills[name] = skill
        
        return skill
    
    def update_skill(self, name: str, **kwargs) -> bool:
        """Update a skill"""
        if name not in self.skills:
            return False
        
        skill = self.skills[name]
        for key, value in kwargs.items():
            if hasattr(skill, key):
                setattr(skill, key, value)
        
        skill.updated_at = datetime.now().isoformat()
        self._save_skill(skill)
        return True
    
    def delete_skill(self, name: str) -> bool:
        """Delete a skill"""
        if name not in self.skills:
            return False
        
        skill = self.skills[name]
        try:
            Path(skill.path).unlink()
            del self.skills[name]
            return True
        except Exception as e:
            logger.error(f"Failed to delete skill {name}: {e}")
            return False
    
    def _save_skill(self, skill: Skill):
        """Save skill to file"""
        content = f"""# {skill.name}

{skill.description}

## Patterns
{chr(10).join(f'- {p}' for p in skill.patterns)}

## Commands
{chr(10).join(f'- {c}' for c in skill.commands)}
"""
        
        with open(skill.path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def detect_changes(self) -> list:
        """Detect skill changes"""
        if not self._change_detector:
            return []
        
        return self._change_detector.detect_changes()
    
    async def check_for_changes(self) -> list:
        """Check for skill changes and notify handlers"""
        if not self._change_detector:
            return []
        
        changes = self._change_detector.detect_changes()
        if changes:
            await self._change_detector.notify_changes(changes)
            self.load_skills()
        
        return changes


# Global skill system instance
skill_system = None
