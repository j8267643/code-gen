"""
Git diff command
"""
import subprocess
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax

from code_gen.client import ClaudeClient

console = Console()


async def show_diff(file: Path = None, staged: bool = False):
    """Show git diff with AI explanation"""
    try:
        # Build git diff command
        cmd = ['git', 'diff']
        if staged:
            cmd.append('--cached')
        if file:
            cmd.append(str(file))
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )
        
        if result.returncode != 0:
            console.print("[red]Git error or not a repository[/red]")
            return
        
        diff = result.stdout
        if not diff:
            console.print("[yellow]No changes to show[/yellow]")
            return
        
        # Show diff
        console.print(Syntax(diff, 'diff', line_numbers=False))
        
        # Get AI explanation
        client = Client()
        
        prompt = f"""Explain these code changes in a clear and concise way:

```diff
{diff[:4000]}
```

Summarize:
1. What changed
2. Why these changes might have been made
3. Any potential issues or improvements"""
        
        with console.status("[bold blue]Analyzing changes...", spinner="dots"):
            explanation = await client.send_message(
                messages=[{"role": "user", "content": prompt}],
            )
        
        console.print(f"\n[bold blue]AI Analysis:[/bold blue]")
        console.print(explanation)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# Fix import
from code_gen.client import ClaudeClient as Client
