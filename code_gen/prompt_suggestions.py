"""
Prompt suggestion system for Claude Code
Based on services/PromptSuggestion/ from TypeScript project
"""
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import json
from enum import Enum


class SuggestionType(str, Enum):
    """Suggestion types"""
    USER_INTENT = "user_intent"
    STATED_INTENT = "stated_intent"


@dataclass
class PromptSuggestion:
    """Prompt suggestion"""
    id: str
    type: SuggestionType
    content: str
    confidence: float
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class PromptSuggestionSystem:
    """Prompt suggestion system"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.suggestions_path = work_dir / ".claude" / "prompt_suggestions.json"
        self.suggestions: list[PromptSuggestion] = []
        self._load_suggestions()
    
    def _load_suggestions(self):
        """Load suggestions from disk"""
        if self.suggestions_path.exists():
            try:
                with open(self.suggestions_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data.get("suggestions", []):
                        suggestion = PromptSuggestion(**item)
                        self.suggestions.append(suggestion)
            except Exception as e:
                print(f"Failed to load suggestions: {e}")
    
    def generate_suggestions(self, conversation_history: list[dict]) -> list[PromptSuggestion]:
        """Generate prompt suggestions based on conversation"""
        suggestions = []
        
        # Placeholder for suggestion generation
        # In real implementation, this would use a forked agent to analyze conversation
        
        if conversation_history:
            # Generate a suggestion based on last message
            last_message = conversation_history[-1]
            if last_message.get("role") == "user":
                content = last_message.get("content", "")
                
                # Generate user intent suggestion
                suggestions.append(PromptSuggestion(
                    id=f"user_intent_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    type=SuggestionType.USER_INTENT,
                    content=f"Based on your message: '{content[:50]}...'",
                    confidence=0.8
                ))
                
                # Generate stated intent suggestion
                suggestions.append(PromptSuggestion(
                    id=f"stated_intent_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    type=SuggestionType.STATED_INTENT,
                    content=f"You said: '{content}'",
                    confidence=0.95
                ))
        
        # Save suggestions
        self.suggestions.extend(suggestions)
        self._save_suggestions()
        
        return suggestions
    
    def _save_suggestions(self):
        """Save suggestions to disk"""
        try:
            with open(self.suggestions_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "suggestions": [
                        {
                            "id": s.id,
                            "type": s.type,
                            "content": s.content,
                            "confidence": s.confidence,
                            "created_at": s.created_at
                        }
                        for s in self.suggestions
                    ]
                }, f, indent=2)
        except Exception as e:
            print(f"Failed to save suggestions: {e}")
    
    def get_recent_suggestions(self, count: int = 10) -> list[PromptSuggestion]:
        """Get recent suggestions"""
        return sorted(
            self.suggestions,
            key=lambda s: s.created_at,
            reverse=True
        )[:count]
    
    def clear_suggestions(self):
        """Clear suggestions"""
        self.suggestions = []
        self._save_suggestions()


# Global prompt suggestion system instance
prompt_suggestion_system = None
