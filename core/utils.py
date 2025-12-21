from rich.console import Console
from rich.panel import Panel

console = Console(force_terminal=True)

def print_header(text):
    console.print(f"[bold magenta]{text}[/bold magenta]")

def print_info(text):
    console.print(f"[cyan]{text}[/cyan]")

def print_success(text):
    console.print(f"[green]{text}[/green]")

def print_warning(text):
    console.print(f"[yellow]{text}[/yellow]")

def print_error(text):
    console.print(f"[bold red]{text}[/bold red]")

def print_event(event_type, text):
    colors = {
        "战斗": "red",
        "探索": "blue", 
        "休息": "green",
        "NPC": "magenta"
    }
    color = colors.get(event_type, "yellow")
    console.print(f"\n[bold {color}][{event_type}][/bold {color}] {text}")

def print_character(name, text):
    console.print(Panel(text, title=f"[cyan]{name}[/cyan]", border_style="cyan"))

def format_loot(loot):
    """美化战利品显示"""
    if isinstance(loot, dict):
        items = [f"{name} x{count}" for name, count in loot.items()]
        return ", ".join(items)
    elif isinstance(loot, list):
        return ", ".join(str(item) for item in loot)
    return str(loot)
