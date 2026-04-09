"""
Configuration management
"""
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import json


class ModelProvider(str, Enum):
    """Model provider types"""
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    OPENAI_COMPATIBLE = "openai_compatible"


class Settings(BaseSettings):
    """Claude Code settings"""
    
    # Application
    app_name: str = "Claude Code"
    version: str = "3.0.0"
    
    # Model Provider
    model_provider: ModelProvider = Field(
        default=ModelProvider.ANTHROPIC,
        env="MODEL_PROVIDER"
    )
    
    # Anthropic API
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-5-sonnet-20241022", env="ANTHROPIC_MODEL")
    
    # Ollama (Local)
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="codellama", env="OLLAMA_MODEL")
    
    # LM Studio (Local)
    lmstudio_base_url: str = Field(default="http://localhost:1234/v1", env="LMSTUDIO_BASE_URL")
    lmstudio_model: str = Field(default="local-model", env="LMSTUDIO_MODEL")
    
    # OpenAI Compatible (Generic)
    openai_compatible_base_url: Optional[str] = Field(default=None, env="OPENAI_COMPATIBLE_BASE_URL")
    openai_compatible_api_key: Optional[str] = Field(default=None, env="OPENAI_COMPATIBLE_API_KEY")
    openai_compatible_model: str = Field(default="local-model", env="OPENAI_COMPATIBLE_MODEL")
    
    # Common settings
    max_tokens: int = 4096
    temperature: float = 0.7
    
    # Paths
    config_dir: Path = Path.home() / ".config" / "claude-code"
    sessions_dir: Path = Field(default_factory=lambda: Path.home() / ".config" / "claude-code" / "sessions")
    snapshots_dir: Path = Field(default_factory=lambda: Path.home() / ".config" / "claude-code" / "snapshots")
    cache_dir: Path = Field(default_factory=lambda: Path.home() / ".cache" / "claude-code")
    
    # Features
    auto_commit: bool = False
    verbose: bool = False
    show_token_count: bool = True
    
    # Git
    git_user_name: Optional[str] = None
    git_user_email: Optional[str] = None
    
    # Plugin settings
    plugin_dir: str = Field(default=".claude/plugins", description="Plugin directory relative to project")
    enable_plugins: bool = Field(default=True, description="Enable plugin system")
    
    # Skill settings
    skill_dir: str = Field(default="skills", description="Skill directory relative to project")
    enable_skills: bool = Field(default=True, description="Enable skill system")
    
    # MCP settings
    mcp_servers: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="MCP server configurations")
    enable_mcp: bool = Field(default=True, description="Enable MCP integration")
    
    # Permission settings
    permission_mode: str = Field(default="auto", description="Permission mode: auto, ask, block")
    permission_config_file: str = Field(default="permissions.json", description="Permission configuration file")
    
    # Cost tracking settings
    cost_config_file: str = Field(default="cost_config.json", description="Cost tracking configuration file")
    track_costs: bool = Field(default=True, description="Track API costs")
    
    # History settings
    max_history_messages: int = Field(default=100, description="Maximum history messages to keep")
    history_file: str = Field(default="history.json", description="History file path")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load user config if exists
        self._load_user_config()
    
    def _load_user_config(self):
        """Load user configuration from file"""
        config_file = self.config_dir / "settings.json"
        
        if not config_file.exists():
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            
            # Update settings from user config
            for key, value in user_config.items():
                if hasattr(self, key):
                    # Handle enum types
                    if key == "model_provider" and isinstance(value, str):
                        try:
                            setattr(self, key, ModelProvider(value))
                        except ValueError:
                            pass
                    else:
                        setattr(self, key, value)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"Warning: Failed to load user config: {e}")
    
    def save_user_config(self):
        """Save current settings to user config file"""
        config_file = self.config_dir / "settings.json"
        
        try:
            # Get current values
            config_data = {
                "model_provider": self.model_provider.value if isinstance(self.model_provider, Enum) else self.model_provider,
                "anthropic_model": self.anthropic_model,
                "ollama_base_url": self.ollama_base_url,
                "ollama_model": self.ollama_model,
                "lmstudio_base_url": self.lmstudio_base_url,
                "lmstudio_model": self.lmstudio_model,
                "openai_compatible_base_url": self.openai_compatible_base_url,
                "openai_compatible_model": self.openai_compatible_model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "auto_commit": self.auto_commit,
                "verbose": self.verbose,
                "show_token_count": self.show_token_count,
                "git_user_name": self.git_user_name,
                "git_user_email": self.git_user_email,
                "plugin_dir": self.plugin_dir,
                "enable_plugins": self.enable_plugins,
                "skill_dir": self.skill_dir,
                "enable_skills": self.enable_skills,
                "mcp_servers": self.mcp_servers,
                "enable_mcp": self.enable_mcp,
                "permission_mode": self.permission_mode,
                "permission_config_file": self.permission_config_file,
                "cost_config_file": self.cost_config_file,
                "track_costs": self.track_costs,
                "max_history_messages": self.max_history_messages,
                "history_file": self.history_file,
            }
            
            # Ensure parent directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save user config: {e}")
    
    def get_model_config(self) -> dict:
        """Get current model configuration"""
        if self.model_provider == ModelProvider.ANTHROPIC:
            return {
                "provider": "anthropic",
                "model": self.anthropic_model,
                "api_key": self.anthropic_api_key,
            }
        elif self.model_provider == ModelProvider.OLLAMA:
            return {
                "provider": "ollama",
                "model": self.ollama_model,
                "base_url": self.ollama_base_url,
            }
        elif self.model_provider == ModelProvider.LMSTUDIO:
            return {
                "provider": "lmstudio",
                "model": self.lmstudio_model,
                "base_url": self.lmstudio_base_url,
            }
        elif self.model_provider == ModelProvider.OPENAI_COMPATIBLE:
            return {
                "provider": "openai_compatible",
                "model": self.openai_compatible_model,
                "base_url": self.openai_compatible_base_url,
                "api_key": self.openai_compatible_api_key,
            }
        return {}
    
    def requires_api_key(self) -> bool:
        """Check if current provider requires API key"""
        return self.model_provider == ModelProvider.ANTHROPIC


# Global settings instance
settings = Settings()
