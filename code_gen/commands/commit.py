"""
Git commit command
"""
import subprocess
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from code_gen.client import ClaudeClient

console = Console()


async def commit_changes(message: str = None, auto: bool = False):
    """Generate commit message and commit changes"""
    try:
        # Check if we're in a git repo
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            cwd=Path.cwd(),
        )
        if result.returncode != 0:
            console.print("[red]Not a git repository[/red]")
            return
        
        # Get git diff
        result = subprocess.run(
            ['git', 'diff', '--cached'],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )
        staged_diff = result.stdout
        
        if not staged_diff and not auto:
            # Check unstaged changes
            result = subprocess.run(
                ['git', 'diff'],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )
            unstaged_diff = result.stdout
            
            if not unstaged_diff:
                console.print("[yellow]No changes to commit[/yellow]")
                return
            
            # Stage all if auto
            if auto:
                subprocess.run(['git', 'add', '-A'], cwd=Path.cwd())
                result = subprocess.run(
                    ['git', 'diff', '--cached'],
                    capture_output=True,
                    text=True,
                    cwd=Path.cwd(),
                )
                staged_diff = result.stdout
            else:
                console.print("[yellow]No staged changes. Use --auto to stage all.[/yellow]")
                return
        
        # Generate commit message if not provided
        if not message:
            client = ClaudeClient()
            
            prompt = f"""Generate a concise git commit message for these changes.
Follow conventional commits format (type: description).
Keep it under 72 characters.

Changes:
```diff
{staged_diff[:4000]}  # Limit diff size
```

Respond with only the commit message, no explanation."""
            
            with console.status("[bold blue]Generating commit message...", spinner="dots"):
                message = await client.send_message(
                    messages=[{"role": "user", "content": prompt}],
                )
            
            message = message.strip().strip('"\'')
            console.print(f"\n[bold]Suggested message:[/bold] {message}")
            
            if not Confirm.ask("Use this message?", default=True):
                message = input("Enter your commit message: ")
        
        # Commit
        result = subprocess.run(
            ['git', 'commit', '-m', message],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )
        
        if result.returncode == 0:
            console.print(f"[green]✓ Committed: {message}[/green]")
        else:
            console.print(f"[red]Error: {result.stderr}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
