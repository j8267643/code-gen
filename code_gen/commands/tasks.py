"""
Task management command
"""
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from code_gen.config import settings

console = Console()


def load_tasks() -> list[dict]:
    """Load tasks from file"""
    tasks_file = settings.config_dir / "tasks.json"
    if tasks_file.exists():
        with open(tasks_file, 'r') as f:
            return json.load(f)
    return []


def save_tasks(tasks: list[dict]):
    """Save tasks to file"""
    tasks_file = settings.config_dir / "tasks.json"
    with open(tasks_file, 'w') as f:
        json.dump(tasks, f, indent=2)


def manage_tasks(action: str, description: str = None):
    """Manage development tasks"""
    tasks = load_tasks()
    
    if action == "list":
        if not tasks:
            console.print("[dim]No tasks[/dim]")
            return
        
        table = Table(title="Development Tasks")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Status", style="green")
        table.add_column("Task")
        table.add_column("Created", style="dim")
        
        for i, task in enumerate(tasks, 1):
            status = "✓" if task.get("completed") else "○"
            style = "dim" if task.get("completed") else ""
            table.add_row(
                str(i),
                status,
                task["description"],
                task.get("created", "")[:10],
                style=style
            )
        
        console.print(table)
        
    elif action == "add":
        if not description:
            console.print("[red]Task description required[/red]")
            return
        
        tasks.append({
            "description": description,
            "completed": False,
            "created": datetime.now().isoformat(),
        })
        save_tasks(tasks)
        console.print(f"[green]✓ Added task: {description}[/green]")
        
    elif action == "complete":
        if not description:
            console.print("[red]Task number required[/red]")
            return
        
        try:
            idx = int(description) - 1
            if 0 <= idx < len(tasks):
                tasks[idx]["completed"] = True
                save_tasks(tasks)
                console.print(f"[green]✓ Completed: {tasks[idx]['description']}[/green]")
            else:
                console.print("[red]Invalid task number[/red]")
        except ValueError:
            console.print("[red]Invalid task number[/red]")
            
    elif action == "clear":
        save_tasks([])
        console.print("[green]✓ All tasks cleared[/green]")
        
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
