"""
Configuration management command
"""
from rich.console import Console
from rich.table import Table

from code_gen.config import settings

console = Console()


def manage_config(key: str = None, value: str = None, list_all: bool = False):
    """Manage configuration"""
    if list_all or (not key and not value):
        # Show all config
        table = Table(title="Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value")
        
        config_dict = settings.model_dump()
        for k, v in sorted(config_dict.items()):
            # Mask sensitive values
            if 'key' in k.lower() or 'secret' in k.lower() or 'password' in k.lower():
                v = "***" if v else "Not set"
            table.add_row(k, str(v))
        
        console.print(table)
        return
    
    if key and not value:
        # Show specific config
        config_dict = settings.model_dump()
        if key in config_dict:
            v = config_dict[key]
            if 'key' in key.lower() or 'secret' in key.lower():
                v = "***" if v else "Not set"
            console.print(f"{key}: {v}")
        else:
            console.print(f"[red]Unknown config key: {key}[/red]")
        return
    
    if key and value:
        # Set config
        if hasattr(settings, key):
            try:
                # Handle different types
                current_value = getattr(settings, key)
                
                if isinstance(current_value, bool):
                    new_value = value.lower() in ('true', '1', 'yes')
                elif isinstance(current_value, int):
                    new_value = int(value)
                elif isinstance(current_value, float):
                    new_value = float(value)
                else:
                    new_value = value
                
                setattr(settings, key, new_value)
                settings.save_user_config()
                console.print(f"[green]✓ Set {key} = {new_value}[/green]")
            except (ValueError, TypeError) as e:
                console.print(f"[red]Error setting {key}: {e}[/red]")
        else:
            console.print(f"[red]Unknown config key: {key}[/red]")
