"""
Permission system for Claude Code
Based on useCanUseTool.tsx from TypeScript project
"""
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, List
from enum import Enum
from pathlib import Path
from datetime import datetime


class PermissionDecisionType(str, Enum):
    """Permission decision types"""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class PermissionDecision:
    """Permission decision result"""
    decision: PermissionDecisionType
    reason: str
    updated_input: Optional[str] = None
    feedback: Optional[dict] = None
    
    @classmethod
    def allow(cls, reason: str = "") -> "PermissionDecision":
        return cls(decision=PermissionDecisionType.ALLOW, reason=reason)
    
    @classmethod
    def deny(cls, reason: str = "") -> "PermissionDecision":
        return cls(decision=PermissionDecisionType.DENY, reason=reason)
    
    @classmethod
    def ask(cls, reason: str = "") -> "PermissionDecision":
        return cls(decision=PermissionDecisionType.ASK, reason=reason)


@dataclass
class PermissionRuleConfig:
    """Configuration for a permission rule"""
    name: str
    enabled: bool = True
    mode: str = "block"
    patterns: List[str] = field(default_factory=list)
    description: str = ""


class PermissionRule:
    """Permission rule for tools"""
    
    def __init__(
        self,
        name: str,
        check: Callable[[str, str], PermissionDecision],
        description: str = "",
        config: PermissionRuleConfig = None
    ):
        self.name = name
        self.check = check
        self.description = description
        self.config = config or PermissionRuleConfig(name=name)
    
    def evaluate(self, tool_name: str, input: str) -> PermissionDecision:
        if not self.config.enabled:
            return PermissionDecision.allow(f"Rule '{self.name}' is disabled")
        return self.check(tool_name, input)


class PermissionSystem:
    """Permission decision system"""
    
    def __init__(self):
        self.rules: list[PermissionRule] = []
        self._initialize_default_rules()
        self._permission_cache: Dict[str, PermissionDecision] = {}
    
    def _initialize_default_rules(self):
        """Initialize default permission rules"""
        self.add_rule(
            "safe_file_paths",
            self._check_safe_file_paths,
            "Block dangerous file paths",
            PermissionRuleConfig(
                name="safe_file_paths",
                patterns=[
                    "/etc/passwd",
                    "/etc/shadow",
                    "~/.ssh",
                    "C:\\Windows",
                    "/System/",
                    "/Library/",
                ]
            )
        )
        
        self.add_rule(
            "safe_commands",
            self._check_safe_commands,
            "Block dangerous commands",
            PermissionRuleConfig(
                name="safe_commands",
                patterns=[
                    "rm -rf /",
                    "mkfs",
                    "dd if=",
                    "> /dev/sda",
                    "chmod 777",
                    "chown root:",
                ]
            )
        )
        
        self.add_rule(
            "environment_variables",
            self._check_environment_variables,
            "Check environment variable access",
            PermissionRuleConfig(
                name="environment_variables",
                patterns=[
                    "API_KEY",
                    "SECRET",
                    "PASSWORD",
                    "TOKEN",
                ]
            )
        )
        
        self.add_rule(
            "network_access",
            self._check_network_access,
            "Check network access",
            PermissionRuleConfig(
                name="network_access",
                mode="ask",
            )
        )
        
        self.add_rule(
            "system_modification",
            self._check_system_modification,
            "Check system modification attempts",
            PermissionRuleConfig(
                name="system_modification",
                mode="deny",
            )
        )
    
    def add_rule(self, name: str, check: Callable, description: str = "", config: PermissionRuleConfig = None):
        """Add a permission rule"""
        rule = PermissionRule(name, check, description, config)
        self.rules.append(rule)
    
    def _check_safe_file_paths(self, tool_name: str, input: str) -> PermissionDecision:
        """Check if file path is safe"""
        patterns = self._get_rule_patterns("safe_file_paths")
        
        for pattern in patterns:
            if pattern in input:
                return PermissionDecision.deny(
                    f"Blocked dangerous file path: {pattern}"
                )
        
        return PermissionDecision.allow()
    
    def _check_safe_commands(self, tool_name: str, input: str) -> PermissionDecision:
        """Check if command is safe"""
        patterns = self._get_rule_patterns("safe_commands")
        
        for cmd in patterns:
            if cmd in input:
                return PermissionDecision.deny(
                    f"Blocked dangerous command: {cmd}"
                )
        
        return PermissionDecision.allow()
    
    def _check_environment_variables(self, tool_name: str, input: str) -> PermissionDecision:
        """Check for environment variable access"""
        patterns = self._get_rule_patterns("environment_variables")
        
        for pattern in patterns:
            if pattern.lower() in input.lower():
                return PermissionDecision.ask(
                    f"Access to environment variable containing '{pattern}' detected"
                )
        
        return PermissionDecision.allow()
    
    def _check_network_access(self, tool_name: str, input: str) -> PermissionDecision:
        """Check for network access attempts"""
        if tool_name in ["http_get", "http_post", "fetch", "curl"]:
            return PermissionDecision.ask(
                "Network access detected. Allow this operation?"
            )
        
        return PermissionDecision.allow()
    
    def _check_system_modification(self, tool_name: str, input: str) -> PermissionDecision:
        """Check for system modification attempts"""
        dangerous_tools = [
            "delete_system_files",
            "modify_system_config",
            "install_system_packages",
            "disable_security",
        ]
        
        if tool_name in dangerous_tools:
            return PermissionDecision.deny(
                f"System modification tool '{tool_name}' is not allowed"
            )
        
        return PermissionDecision.allow()
    
    def _get_rule_patterns(self, rule_name: str) -> List[str]:
        """Get patterns for a specific rule"""
        for rule in self.rules:
            if rule.name == rule_name and rule.config:
                return rule.config.patterns
        return []
    
    def can_use_tool(self, tool_name: str, input: str = "") -> PermissionDecision:
        """Check if tool can be used"""
        cache_key = f"{tool_name}:{input}"
        
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]
        
        for rule in self.rules:
            decision = rule.evaluate(tool_name, input)
            if decision.decision != PermissionDecisionType.ALLOW:
                self._permission_cache[cache_key] = decision
                return decision
        
        decision = PermissionDecision.allow()
        self._permission_cache[cache_key] = decision
        return decision
    
    def get_permission_mode(self) -> str:
        """Get current permission mode"""
        return "auto"
    
    def get_permission_prompt(self, tool_name: str, input: str = "") -> Optional[str]:
        """Get permission prompt for a tool"""
        decision = self.can_use_tool(tool_name, input)
        
        if decision.decision == PermissionDecisionType.ASK:
            return f"Tool '{tool_name}' requires permission: {decision.reason}"
        
        return None
    
    def get_detailed_permission_info(self, tool_name: str, input: str = "") -> dict:
        """Get detailed permission information"""
        results = []
        
        for rule in self.rules:
            if rule.config.enabled:
                decision = rule.evaluate(tool_name, input)
                results.append({
                    "rule": rule.name,
                    "description": rule.description,
                    "decision": decision.decision.value,
                    "reason": decision.reason,
                })
        
        return {
            "tool": tool_name,
            "input": input,
            "rules": results,
            "final_decision": self.can_use_tool(tool_name, input).decision.value,
        }
    
    def clear_cache(self):
        """Clear permission cache"""
        self._permission_cache.clear()
    
    def load_permissions_from_file(self, file_path: str):
        """Load permissions from configuration file"""
        path = Path(file_path)
        
        if not path.exists():
            return
        
        try:
            import json
            with open(path, 'r') as f:
                data = json.load(f)
            
            permissions = data.get("permissions", {})
            
            for rule_name, rule_config in permissions.items():
                for rule in self.rules:
                    if rule.name == rule_name:
                        if "enabled" in rule_config:
                            rule.config.enabled = rule_config["enabled"]
                        if "mode" in rule_config:
                            rule.config.mode = rule_config["mode"]
                        if "patterns" in rule_config:
                            rule.config.patterns = rule_config["patterns"]
        except Exception:
            pass
    
    def save_permissions_to_file(self, file_path: str):
        """Save permissions to configuration file"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        data = {
            "permissions": {},
            "updated_at": datetime.now().isoformat()
        }
        
        for rule in self.rules:
            data["permissions"][rule.name] = {
                "enabled": rule.config.enabled,
                "mode": rule.config.mode,
                "patterns": rule.config.patterns,
                "description": rule.description,
            }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)


permission_system = PermissionSystem()
