"""
Authentication commands
"""
import keyring
from rich.console import Console
from rich.prompt import Prompt

from code_gen.config import settings

console = Console()
SERVICE_NAME = "claude-code"
USERNAME = "api-key"


def login_user(api_key: str = None):
    """Login with API key"""
    if not api_key:
        api_key = Prompt.ask(
            "Enter your Anthropic API key",
            password=True,
        )
    
    if not api_key.startswith("sk-"):
        console.print("[red]Invalid API key format. Should start with 'sk-'[/red]")
        return
    
    # Store in keyring
    keyring.set_password(SERVICE_NAME, USERNAME, api_key)
    
    console.print("[green]✓ API key saved successfully![/green]")
    console.print("[dim]You can now use Claude Code[/dim]")


def logout_user():
    """Logout and remove stored credentials"""
    try:
        keyring.delete_password(SERVICE_NAME, USERNAME)
        console.print("[green]✓ Logged out successfully[/green]")
    except keyring.errors.PasswordDeleteError:
        console.print("[yellow]No stored credentials found[/yellow]")


def get_api_key() -> str:
    """Get stored API key"""
    # First check environment
    if settings.anthropic_api_key:
        return settings.anthropic_api_key
    
    # Then check keyring
    api_key = keyring.get_password(SERVICE_NAME, USERNAME)
    if api_key:
        return api_key
    
    raise ValueError(
        "API key not found. Run 'claude-code login' or set ANTHROPIC_API_KEY"
    )
