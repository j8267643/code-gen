"""
Cost tracker for Claude Code
Based on cost-tracker.ts from TypeScript project
"""
from typing import Optional, List
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import json


@dataclass
class TokenUsage:
    """Token usage for a model"""
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    
    def add_usage(self, input_tokens: int, output_tokens: int):
        """Add usage"""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens = self.input_tokens + self.output_tokens


@dataclass
class CostEntry:
    """Cost entry for a session"""
    session_id: str
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: str
    cost: float = 0.0


class CostTracker:
    """Cost tracker for Claude Code"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.config_path = work_dir / ".claude" / "cost_config.json"
        self.usage_history: List[CostEntry] = []
        self.model_usage: dict[str, TokenUsage] = {}
        self.model_costs: dict = {
            "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},  # per 1M tokens
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        }
        self._load_config()
    
    def _load_config(self):
        """Load cost configuration"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.model_costs.update(config.get("model_costs", {}))
            except Exception as e:
                print(f"Failed to load cost config: {e}")
    
    def record_usage(self, session_id: str, model: str, 
                     input_tokens: int, output_tokens: int):
        """Record token usage"""
        # Update model usage
        if model not in self.model_usage:
            self.model_usage[model] = TokenUsage(model=model)
        
        self.model_usage[model].add_usage(input_tokens, output_tokens)
        
        # Calculate cost
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        
        # Create cost entry
        entry = CostEntry(
            session_id=session_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            timestamp=datetime.now().isoformat(),
            cost=cost
        )
        
        self.usage_history.append(entry)
        
        # Save history
        self._save_history()
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on model and tokens"""
        if model not in self.model_costs:
            return 0.0
        
        costs = self.model_costs[model]
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]
        
        return input_cost + output_cost
    
    def _save_history(self):
        """Save usage history"""
        history_path = self.work_dir / ".claude" / "cost_history.json"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(history_path, 'w') as f:
                json.dump({
                    "entries": [
                        {
                            "session_id": e.session_id,
                            "model": e.model,
                            "input_tokens": e.input_tokens,
                            "output_tokens": e.output_tokens,
                            "timestamp": e.timestamp,
                            "cost": e.cost
                        }
                        for e in self.usage_history
                    ]
                }, f, indent=2)
        except Exception as e:
            print(f"Failed to save history: {e}")
    
    def get_total_cost(self) -> float:
        """Get total cost"""
        return sum(e.cost for e in self.usage_history)
    
    def get_model_usage(self, model: str) -> TokenUsage:
        """Get usage for a model"""
        return self.model_usage.get(model, TokenUsage(model=model))
    
    def get_recent_sessions(self, count: int = 10) -> list[CostEntry]:
        """Get recent sessions"""
        return sorted(
            self.usage_history,
            key=lambda e: e.timestamp,
            reverse=True
        )[:count]
    
    def get_cost_summary(self) -> dict:
        """Get cost summary"""
        summary = {
            "total_cost": self.get_total_cost(),
            "total_input_tokens": sum(e.input_tokens for e in self.usage_history),
            "total_output_tokens": sum(e.output_tokens for e in self.usage_history),
            "total_sessions": len(self.usage_history),
            "model_breakdown": {}
        }
        
        for entry in self.usage_history:
            if entry.model not in summary["model_breakdown"]:
                summary["model_breakdown"][entry.model] = {
                    "cost": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "sessions": 0
                }
            
            summary["model_breakdown"][entry.model]["cost"] += entry.cost
            summary["model_breakdown"][entry.model]["input_tokens"] += entry.input_tokens
            summary["model_breakdown"][entry.model]["output_tokens"] += entry.output_tokens
            summary["model_breakdown"][entry.model]["sessions"] += 1
        
        return summary


# Global cost tracker instance
cost_tracker = None
