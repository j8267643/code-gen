"""
Dream command - Nightly dreaming system
"""
import asyncio
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from code_gen.config import settings
from code_gen.memory import MemorySystem, MemoryType
from code_gen.client import ClaudeClient

console = Console()


async def dream(
    work_dir: Path,
    force: bool = False,
    verbose: bool = False
) -> None:
    """
    Run the nightly dreaming process
    
    Args:
        work_dir: Working directory
        force: Force dream even if not scheduled
        verbose: Show detailed output
    """
    console.print("\n[bold]Starting Dream Process...[/bold]\n")
    
    # Initialize memory system
    memory_system = MemorySystem(work_dir)
    
    if not memory_system.memories:
        console.print("[yellow]No memories to dream about.[/yellow]")
        return
    
    console.print(f"[dim]Found {len(memory_system.memories)} memories[/dim]\n")
    
    # Show memory summary
    if verbose:
        console.print("[bold]Memories Summary:[/bold]")
        for mem_type in MemoryType:
            memories = memory_system.get_memories_by_type(mem_type)
            if memories:
                console.print(f"  • {mem_type.value}: {len(memories)} memories")
        console.print()
    
    # Initialize client
    try:
        client = ClaudeClient()
    except Exception as e:
        console.print(f"[red]Failed to initialize client: {e}[/red]")
        return
    
    # Show progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Dreaming...", total=None)
        
        # Run dream process
        try:
            result = await _run_dream_process(client, memory_system, verbose)
            progress.update(task, completed=True)
            
            # Display dream result
            console.print("\n" + "=" * 60)
            console.print(Panel(
                result,
                title="[bold green]Dream Result[/bold green]",
                border_style="green"
            ))
            console.print("=" * 60 + "\n")
            
            # Save dream result
            await _save_dream_result(work_dir, result)
            
            console.print("[green]Dream process completed![/green]")
            
        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[red]Dream process failed: {e}[/red]")
            raise


async def _run_dream_process(
    client: ClaudeClient,
    memory_system: MemorySystem,
    verbose: bool = False
) -> str:
    """
    Run the actual dream process using AI
    
    Args:
        client: AI client
        memory_system: Memory system instance
        verbose: Show detailed output
        
    Returns:
        Dream result string
    """
    # Prepare memory context
    memories_text = ""
    for memory in memory_system.memories:
        memories_text += f"\n--- {memory.type.value} Memory ({memory.id}) ---\n"
        memories_text += memory.content
        if memory.tags:
            memories_text += f"\nTags: {', '.join(memory.tags)}"
        memories_text += "\n"
    
    # Build dream prompt
    dream_prompt = f"""You are Claude's Dream System. Your task is to analyze memories and extract insights.

Memories to analyze:
{memories_text}

Your task:
1. Identify patterns and connections between memories
2. Extract key insights and learnings
3. Generate new ideas based on the memories
4. Summarize the most important points
5. Suggest next steps or actions

Format your response as:
## Key Insights
- Insight 1
- Insight 2

## Connections
- Connection 1
- Connection 2

## Ideas
- Idea 1
- Idea 2

## Summary
Brief summary of the dream

## Next Steps
- Action 1
- Action 2
"""
    
    # Call AI to process memories
    response = await client.send_message(
        messages=[{"role": "user", "content": dream_prompt}],
        system="You are a helpful AI assistant specialized in analyzing memories and extracting insights."
    )
    
    return response


async def _save_dream_result(work_dir: Path, result: str) -> None:
    """
    Save dream result to file
    
    Args:
        work_dir: Working directory
        result: Dream result string
    """
    dream_dir = work_dir / ".code_gen" / "dreams"
    dream_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = Path().home().name  # Use a simple timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    dream_file = dream_dir / f"dream_{timestamp}.md"
    
    content = f"""# Dream Result - {timestamp}

## Summary
{result}

## Metadata
- Date: {timestamp}
- Type: AI Dream Analysis
"""
    
    try:
        with open(dream_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        console.print(f"[dim]Dream result saved to: {dream_file}[/dim]")
        
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to save dream result: {e}[/yellow]")
