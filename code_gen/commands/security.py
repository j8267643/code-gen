"""Security Monitor commands"""
from pathlib import Path
from typing import Optional

import typer

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from code_gen.security import SecurityMonitor, SecurityConfig

console = Console()

security_app = typer.Typer(
    name="security",
    help="Security Monitor - Protect against prompt injection, scope creep, and accidental damage"
)


@security_app.command()
def status(
    work_dir: Path = typer.Option(Path.cwd(), "--work-dir", "-w", help="Working directory")
):
    """Show security status and recent events"""
    security = SecurityMonitor(work_dir)
    
    report = security.get_security_report()
    stats = report["statistics"]
    
    # Create status panel
    panel_content = Text()
    panel_content.append("Security Status\n", style="bold blue")
    panel_content.append(f"Total Events: {stats['total_events']}\n")
    panel_content.append(f"Blocked: {stats['blocked']}\n")
    panel_content.append(f"Alerted: {stats['alerted']}\n")
    
    if stats['total_events'] > 0:
        panel_content.append("\nRecent Events:\n", style="bold")
        for event in report["events"][:5]:
            severity = event['severity'].upper()
            panel_content.append(f"  [{severity}] {event['threat_name']}\n")
    
    console.print(Panel(panel_content, title="Security Monitor", border_style="blue"))
    
    # Print detailed statistics
    console.print("\n[bold]Statistics by Type:[/bold]")
    for threat_type, count in stats['by_type'].items():
        console.print(f"  • {threat_type}: {count}")
    
    console.print("\n[bold]Statistics by Severity:[/bold]")
    for severity, count in stats['by_severity'].items():
        console.print(f"  • {severity}: {count}")


@security_app.command()
def report(
    work_dir: Path = typer.Option(Path.cwd(), "--work-dir", "-w", help="Working directory"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path")
):
    """Generate detailed security report"""
    security = SecurityMonitor(work_dir)
    report = security.get_security_report()
    
    # Print report
    console.print("\n[bold blue]Security Report[/bold blue]")
    console.print("=" * 60)
    
    # Statistics
    stats = report["statistics"]
    console.print(f"\n[bold]Statistics:[/bold]")
    console.print(f"  Total Events: {stats['total_events']}")
    console.print(f"  Blocked: {stats['blocked']}")
    console.print(f"  Alerted: {stats['alerted']}")
    
    console.print(f"\n[bold]By Type:[/bold]")
    for threat_type, count in stats['by_type'].items():
        console.print(f"  • {threat_type}: {count}")
    
    console.print(f"\n[bold]By Severity:[/bold]")
    for severity, count in stats['by_severity'].items():
        console.print(f"  • {severity}: {count}")
    
    # Events table
    if report["events"]:
        console.print(f"\n[bold]Recent Events:[/bold]")
        
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Time")
        table.add_column("Type")
        table.add_column("Threat")
        table.add_column("Severity")
        table.add_column("Action")
        table.add_column("Description")
        
        for event in report["events"]:
            severity_colors = {
                "critical": "red",
                "high": "bright_red",
                "medium": "yellow",
                "low": "blue"
            }
            
            color = severity_colors.get(event['severity'], "white")
            
            table.add_row(
                event['timestamp'][:16],
                event['threat_type'],
                event['threat_name'],
                f"[{color}]{event['severity'].upper()}[/{color}]",
                event['action_taken'],
                event['description'][:50]
            )
        
        console.print(table)
    
    console.print("\n" + "=" * 60)
    
    # Save to file if specified
    if output:
        try:
            import json
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            console.print(f"\n[green]Report saved to: {output}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to save report: {e}[/red]")


@security_app.command()
def clear(
    work_dir: Path = typer.Option(Path.cwd(), "--work-dir", "-w", help="Working directory"),
    force: bool = typer.Option(False, "--force", "-f", help="Force clear without confirmation")
):
    """Clear all security events"""
    security = SecurityMonitor(work_dir)
    
    if not force and len(security.events) > 0:
        from rich.prompt import Confirm
        if not Confirm.ask(f"Are you sure you want to clear {len(security.events)} security events?"):
            console.print("[yellow]Clear cancelled[/yellow]")
            return
    
    security.events = []
    security._save_events()
    console.print("[green]All security events cleared[/green]")


@security_app.command()
def inject(
    work_dir: Path = typer.Option(Path.cwd(), "--work-dir", "-w", help="Working directory"),
    input: str = typer.Option(..., "--input", "-i", help="Input to check for injection")
):
    """Check user input for prompt injection"""
    security = SecurityMonitor(work_dir)
    
    event = security.detect_prompt_injection(input)
    
    if event:
        console.print(f"\n[red bold]PROMPT INJECTION DETECTED![/red bold]")
        console.print(f"\n[bold]Threat:[/bold] {event.threat_name}")
        console.print(f"[bold]Severity:[/bold] {event.severity}")
        console.print(f"[bold]Description:[/bold] {event.description}")
        console.print(f"\n[bold]Input:[/bold] {event.input}")
        console.print(f"\n[bold]Action:[/bold] {event.action_taken}")
    else:
        console.print(f"\n[green]No prompt injection detected.[/green]")


@security_app.command()
def scan(
    work_dir: Path = typer.Option(Path.cwd(), "--work-dir", "-w", help="Working directory"),
    path: str = typer.Option(".", "--path", "-p", help="Path to scan for damage risk")
):
    """Scan path for accidental damage risk"""
    security = SecurityMonitor(work_dir)
    
    # Check if path exists
    path_obj = Path(path)
    
    if not path_obj.exists():
        console.print(f"[red]Path does not exist: {path}[/red]")
        return
    
    # Check for uncommitted changes
    has_uncommitted = security._has_uncommitted_changes(path)
    
    # Check for important files
    files = []
    if path_obj.is_file():
        files = [path]
    elif path_obj.is_dir():
        files = [f.name for f in path_obj.iterdir() if f.is_file()]
    
    has_important = security._contains_important_files(path, files)
    
    # Print scan results
    console.print(f"\n[bold blue]Scan Results for: {path}[/bold blue]")
    console.print("=" * 60)
    
    table = Table(show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")
    
    # Check 1: Path exists
    table.add_row("Path exists", "[green]✓[/green]", str(path_obj.resolve()))
    
    # Check 2: Uncommitted changes
    uncommitted_status = "[red]⚠️ YES[/red]" if has_uncommitted else "[green]✓ No[/green]"
    uncommitted_detail = "Has uncommitted git changes" if has_uncommitted else "No uncommitted changes"
    table.add_row("Uncommitted changes", uncommitted_status, uncommitted_detail)
    
    # Check 3: Important files
    important_status = "[red]⚠️ YES[/red]" if has_important else "[green]✓ No[/green]"
    important_detail = "Contains important files" if has_important else "No important files"
    table.add_row("Important files", important_status, important_detail)
    
    console.print(table)
    
    # Risk assessment
    console.print("\n[bold]Risk Assessment:[/bold]")
    if has_uncommitted or has_important:
        console.print("[red bold]HIGH RISK: Deleting this path may cause data loss![/red bold]")
        console.print("\n[bold]Recommendation:[/bold]")
        console.print("  1. Commit your changes first")
        console.print("  2. Backup important files")
        console.print("  3. Use --force to override (if you're sure)")
    else:
        console.print("[green]LOW RISK: Safe to delete[/green]")


@security_app.command()
def watch(
    work_dir: Path = typer.Option(Path.cwd(), "--work-dir", "-w", help="Working directory"),
    task_id: str = typer.Option("default", "--task-id", "-t", help="Task ID to monitor")
):
    """Watch task execution for scope creep"""
    security = SecurityMonitor(work_dir)
    
    console.print(f"\n[bold blue]Watching Task: {task_id}[/bold blue]")
    console.print("Enter task steps (one per line, empty line to finish):")
    
    steps = []
    while True:
        try:
            step = input("> ").strip()
            if not step:
                break
            
            steps.append(step)
            current_scope = {"files": [], "directories": [], "complexity": len(steps)}
            
            security.record_task_step(task_id, step, current_scope)
            
            # Check for scope creep
            event = security.detect_scope_creek(task_id, current_scope)
            if event:
                console.print(f"\n[yellow]⚠️ Scope creep detected![/yellow]")
                console.print(f"  {event.description}")
                console.print()
            
        except EOFError:
            break
    
    console.print(f"\n[green]Task monitoring complete. {len(steps)} steps recorded.[/green]")
