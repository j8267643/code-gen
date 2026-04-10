"""
Code Gen CLI
"""
import sys
import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from code_gen.config import ModelProvider, settings
from code_gen.session import SessionManager
from code_gen.ui.app import CodeGenApp

app = typer.Typer(pretty_exceptions_enable=False)
console = Console()


@app.command()
def chat(
    path: Optional[Path] = typer.Argument(
        None,
        help="Project directory to work with",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    model: str = typer.Option(
        None,
        "--model",
        "-m",
        help="Model to use (overrides default)",
    ),
):
    """Start an interactive coding session with AI"""
    import os
    
    # Check for PyYAML dependency
    try:
        import yaml
    except ImportError:
        console.print("[red]Error: PyYAML is required. Install with: pip install PyYAML[/red]")
        raise typer.Exit(1)
    
    work_dir = path or Path.cwd()
    
    # 配置文件放在项目根目录的 .code_gen 文件夹中
    config_path = work_dir / ".code_gen" / "config.yaml"
    
    # 如果配置文件不存在，创建默认配置文件
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        default_config = '''# =============================================================================
# Code Gen Configuration File
# =============================================================================
# This is the main configuration file for Code Gen.
# All settings can be overridden via environment variables.
#
# Location: {config_path}
# Documentation: https://github.com/your-repo/code-gen/blob/main/docs/config.md
# =============================================================================

# -----------------------------------------------------------------------------
# Core Settings
# -----------------------------------------------------------------------------

# Model provider to use
# Options: anthropic, ollama, lmstudio, openai_compatible
model_provider: anthropic

# -----------------------------------------------------------------------------
# Anthropic Claude (Cloud API)
# -----------------------------------------------------------------------------
anthropic:
  api_key: ""                          # Set via ANTHROPIC_API_KEY env var
  model: claude-3-5-sonnet-20241022    # Model identifier

# -----------------------------------------------------------------------------
# Ollama (Local Models)
# -----------------------------------------------------------------------------
ollama:
  base_url: http://localhost:11434     # Ollama server URL
  model: codellama                     # Default local model

# -----------------------------------------------------------------------------
# LM Studio (Local Server)
# -----------------------------------------------------------------------------
lmstudio:
  base_url: http://localhost:1234/v1   # LM Studio server URL
  model: local-model                   # Model name

# -----------------------------------------------------------------------------
# OpenAI Compatible (Generic)
# -----------------------------------------------------------------------------
openai_compatible:
  base_url: ""                         # API base URL
  api_key: ""                          # API key (if required)
  model: local-model                   # Model identifier

# -----------------------------------------------------------------------------
# Generation Parameters
# -----------------------------------------------------------------------------
generation:
  max_tokens: 4096                     # Maximum tokens per response
  temperature: 0.7                     # Creativity (0.0 = deterministic, 1.0 = creative)

# -----------------------------------------------------------------------------
# Feature Flags
# -----------------------------------------------------------------------------
features:
  auto_commit: false                   # Auto-commit changes
  verbose: false                       # Verbose output
  show_token_count: true               # Display token usage

# -----------------------------------------------------------------------------
# Plugin & Skill Settings
# -----------------------------------------------------------------------------
plugins:
  enabled: true
  directory: .code_gen/plugins

skills:
  enabled: true
  directory: skills

# -----------------------------------------------------------------------------
# Git Settings
# -----------------------------------------------------------------------------
git:
  user_name: ""                        # Git commit author name
  user_email: ""                       # Git commit author email
'''.format(config_path=config_path)
        config_path.write_text(default_config, encoding='utf-8')
        console.print(f"[green]✓ Created default config file: {config_path}[/green]")
    
    # 从配置文件加载设置
    config_data = {}
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load config file: {e}[/yellow]")
    
    # 获取模型提供商（优先级：环境变量 > 配置文件 > 默认设置）
    provider_str = os.getenv('MODEL_PROVIDER', config_data.get('model_provider', settings.model_provider.value))
    try:
        provider = ModelProvider(provider_str)
    except ValueError:
        provider = ModelProvider.ANTHROPIC
    
    # 获取模型名称（优先级：命令行参数 > 环境变量 > 配置文件 > 默认设置）
    if model:
        model_name = model
    elif provider == ModelProvider.OLLAMA:
        model_name = os.getenv('OLLAMA_MODEL', 
            config_data.get('ollama', {}).get('model', settings.ollama_model))
    elif provider == ModelProvider.LMSTUDIO:
        model_name = os.getenv('LMSTUDIO_MODEL',
            config_data.get('lmstudio', {}).get('model', settings.lmstudio_model))
    elif provider == ModelProvider.OPENAI_COMPATIBLE:
        model_name = os.getenv('OPENAI_COMPATIBLE_MODEL',
            config_data.get('openai_compatible', {}).get('model', settings.openai_compatible_model))
    else:
        model_name = config_data.get('anthropic', {}).get('model', settings.anthropic_model)
    
    # 检查是否需要 API key（Ollama 和 LM Studio 不需要）
    api_key = os.getenv('ANTHROPIC_API_KEY') or config_data.get('anthropic', {}).get('api_key', '')
    
    if provider == ModelProvider.ANTHROPIC and not api_key:
        console.print("[red]Error: API key required for Anthropic provider[/red]")
        console.print(f"[dim]Current default model: {model_name}[/dim]")
        console.print(f"[dim]Provider: {provider.value}[/dim]")
        console.print("\n[yellow]To configure:[/yellow]")
        console.print("  1. Run [cyan]code-gen login[/cyan] to set API key")
        console.print("  2. Or set [cyan]ANTHROPIC_API_KEY[/cyan] environment variable")
        console.print("  3. Or modify config file directly:")
        console.print(f"     [dim]{config_path}[/dim]")
        sys.exit(1)
    
    # Start interactive session
    session = SessionManager(work_dir, model_name)
    
    try:
        app_instance = CodeGenApp(session)
        app_instance.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
        sys.exit(0)


@app.command()
def review(
    file: Optional[Path] = typer.Argument(
        None,
        help="File to review",
    ),
):
    """Review code files with AI"""
    from code_gen.commands.review import review_code
    
    # Check auth if needed
    if settings.requires_api_key() and not settings.anthropic_api_key:
        console.print("[red]Error: API key required[/red]")
        sys.exit(1)
    
    asyncio.run(review_code(file))


@app.command()
def commit(
    message: Optional[str] = typer.Argument(
        None,
        help="Commit message (optional, will generate if not provided)",
    ),
    staged: bool = typer.Option(
        False,
        "--staged",
        "-s",
        help="Commit staged changes only",
    ),
):
    """Generate commit message and commit changes"""
    from code_gen.commands.commit import handle_commit
    
    # Check auth if needed
    if settings.requires_api_key() and not settings.anthropic_api_key:
        console.print("[red]Error: API key required[/red]")
        sys.exit(1)
    
    asyncio.run(handle_commit(message, staged))


@app.command()
def diff(
    file: Optional[Path] = typer.Argument(
        None,
        help="File to show diff for",
    ),
    staged: bool = typer.Option(
        False,
        "--staged",
        "-s",
        help="Show staged changes",
    ),
):
    """Show git diff with AI explanation"""
    from code_gen.commands.diff import show_diff
    
    # Check auth if needed
    if settings.requires_api_key() and not settings.anthropic_api_key:
        console.print("[red]Error: API key required[/red]")
        sys.exit(1)
    
    asyncio.run(show_diff(file, staged))


@app.command()
def tasks(
    action: str = typer.Argument(
        "list",
        help="Action: list, add, complete, clear",
    ),
    description: Optional[str] = typer.Argument(
        None,
        help="Task description (for add action)",
    ),
):
    """Manage development tasks"""
    from code_gen.commands.tasks import manage_tasks
    
    manage_tasks(action, description)


@app.command()
def config(
    key: Optional[str] = typer.Argument(
        None,
        help="Configuration key",
    ),
    value: Optional[str] = typer.Argument(
        None,
        help="Configuration value (set if provided)",
    ),
    list_all: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List all configuration",
    ),
):
    """Manage Claude Code configuration"""
    from code_gen.commands.config import manage_config
    
    manage_config(key, value, list_all)


@app.command()
def provider(
    name: Optional[str] = typer.Argument(
        None,
        help="Provider name: anthropic, ollama, lmstudio, openai_compatible",
    ),
    list_all: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List available providers",
    ),
):
    """Switch between AI providers"""
    if list_all or not name:
        table = Table(title="Available Providers")
        table.add_column("Provider", style="cyan")
        table.add_column("Description")
        table.add_column("Requires Auth", style="yellow")
        table.add_column("Status", style="green")
        
        providers = [
            ("anthropic", "Anthropic Claude API", "Yes", "✓" if settings.anthropic_api_key else "✗"),
            ("ollama", "Ollama local models", "No", "Local"),
            ("lmstudio", "LM Studio local server", "No", "Local"),
            ("openai_compatible", "Generic OpenAI API", "Optional", "Config"),
        ]
        
        current = settings.model_provider.value
        for p, desc, auth, status in providers:
            marker = "→ " if p == current else "  "
            table.add_row(f"{marker}{p}", desc, auth, status)
        
        console.print(table)
        console.print(f"\n[dim]Current provider: {current}[/dim]")
        console.print("\nTo switch: [yellow]code-gen provider <name>[/yellow]")
        return
    
    # Switch provider
    try:
        new_provider = ModelProvider(name.lower())
        
        # Update settings
        settings.model_provider = new_provider
        
        # Save to config file
        settings.save_user_config()
        
        console.print(f"[green]✓ Switched to provider: {new_provider.value}[/green]")
        
        # Show provider-specific info
        if new_provider == ModelProvider.OLLAMA:
            console.print(f"[dim]Make sure Ollama is running at {settings.ollama_base_url}[/dim]")
            console.print(f"[dim]Default model: {settings.ollama_model}[/dim]")
        elif new_provider == ModelProvider.LMSTUDIO:
            console.print(f"[dim]Make sure LM Studio server is running at {settings.lmstudio_base_url}[/dim]")
        elif new_provider == ModelProvider.ANTHROPIC:
            if not settings.anthropic_api_key:
                console.print("[yellow]Warning: No API key set. Run 'code-gen login'[/yellow]")
        
    except ValueError:
        console.print(f"[red]Invalid provider: {name}[/red]")


@app.command()
def login():
    """Authenticate with Anthropic API"""
    from code_gen.commands.auth import login_user
    
    login_user()


@app.command()
def logout():
    """Remove stored API credentials"""
    from code_gen.commands.auth import logout_user
    
    logout_user()


@app.command()
def version():
    """Show version information"""
    from code_gen import __version__
    
    console.print(f"[bold blue]Claude Code[/bold blue] version [green]{__version__}[/green]")
    console.print(f"[dim]Provider: {settings.model_provider.value}[/dim]")


@app.command()
def dream(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force dream even if not scheduled",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    path: Optional[Path] = typer.Argument(
        None,
        help="Project directory to work with",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
):
    """Run the nightly dreaming process to extract insights from memories"""
    from code_gen.commands.dream import dream
    
    work_dir = path or Path.cwd()
    
    # Check auth if needed
    if settings.requires_api_key() and not settings.anthropic_api_key:
        console.print("[red]Error: API key required[/red]")
        sys.exit(1)
    
    asyncio.run(dream(work_dir, force, verbose))


@app.command()
def security(
    command: str = typer.Argument(
        "status",
        help="Command: status, report, clear, inject, scan, watch"
    ),
    work_dir: Path = typer.Option(Path.cwd(), "--work-dir", "-w", help="Working directory"),
    input: str = typer.Option("", "--input", "-i", help="Input for injection check"),
    path: str = typer.Option(".", "--path", "-p", help="Path for scan"),
    task_id: str = typer.Option("default", "--task-id", "-t", help="Task ID for watch"),
    force: bool = typer.Option(False, "--force", "-f", help="Force clear"),
    output: str = typer.Option(None, "--output", "-o", help="Output file for report"),
):
    """Security Monitor - Protect against prompt injection, scope creep, and accidental damage"""
    from code_gen.commands.security import security_app
    
    # Create a temporary typer context to call security app
    import sys
    from typer.main import get_command
    
    # Build command arguments
    cmd_args = [command]
    
    if command == "inject" and input:
        cmd_args.extend(["--input", input])
    elif command == "scan" and path:
        cmd_args.extend(["--path", path])
    elif command == "watch":
        cmd_args.extend(["--task-id", task_id])
    elif command == "clear":
        cmd_args.append("--force")
    elif command == "report" and output:
        cmd_args.extend(["--output", output])
    
    # Add work directory
    cmd_args.extend(["--work-dir", str(work_dir)])
    
    # Call security app
    security_app(cmd_args)


def main():
    """Main entry point"""
    app()


if __name__ == "__main__":
    main()
