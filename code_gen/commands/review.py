"""
Code review command
"""
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from code_gen.client import ClaudeClient

console = Console()


async def review_files(files: list[Path], model: str):
    """Review code files"""
    try:
        client = ClaudeClient()
        
        console.print(Panel.fit(
            "[bold blue]Code Review[/bold blue]",
            border_style="blue"
        ))
        
        for file_path in files:
            console.print(f"\n[bold]Reviewing:[/bold] {file_path}")
            
            # Read file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                console.print(f"[red]Error reading file: {e}[/red]")
                continue
            
            # Show file content
            syntax = Syntax(content, file_path.suffix.lstrip('.') or 'text', line_numbers=True)
            console.print(syntax)
            
            # Get review from Claude
            prompt = f"""Please review this code file and provide feedback on:
1. Code quality and best practices
2. Potential bugs or issues
3. Performance considerations
4. Security concerns
5. Suggestions for improvement

File: {file_path}

```
{content}
```

Provide a concise but thorough review."""
            
            with console.status("[bold blue]Analyzing...", spinner="dots"):
                response = await client.send_message(
                    messages=[{"role": "user", "content": prompt}],
                )
            
            console.print(Panel(
                response,
                title="[bold]Review[/bold]",
                border_style="green"
            ))
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
