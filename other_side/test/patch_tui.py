from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

def show_change_blocks(additions: int, deletions: int, max_blocks: int = 10, filename: str = ""):
    """
    Shows a row of small colored blocks: green ▮ for additions, red ▮ for deletions
    Caps at max_blocks total (scales down if more changes)
    """
    total_changes = additions + deletions
    if total_changes == 0:
        console.print("[dim]No changes[/dim]")
        return

    # Scale to max_blocks if needed
    scale = max_blocks / total_changes if total_changes > max_blocks else 1
    green_count = round(additions * scale)
    red_count = round(deletions * scale)

    # Fill up to max_blocks if rounding left space
    while green_count + red_count < max_blocks and (green_count < additions or red_count < deletions):
        if green_count < additions:
            green_count += 1
        elif red_count < deletions:
            red_count += 1

    blocks = (
        Text("▮" * green_count, style="bold green") +
        Text("▮" * red_count, style="bold red")
    )

    label = f"[white]{filename}[/white]" if filename else ""
    changes_text = f" +{additions} / -{deletions}"

    console.print(
        Panel(
            blocks + Text(changes_text, style="dim"),
            title=label or "Changes",
            border_style="bright_black",
            padding=(0, 2),
            expand=False
        )
    )


# ────────────────────────────────────────────────
# Examples
# ────────────────────────────────────────────────

show_change_blocks(7, 2, filename="Button.tsx")
show_change_blocks(0, 15, filename="old_config.json")
show_change_blocks(25, 40, max_blocks=20, filename="big_file.py")
show_change_blocks(3, 3)