import os
import sys
from datetime import datetime
from typing import List, Tuple, Dict
from google.genai import types
from rich.console import Console
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.box import ROUNDED
from difflib import SequenceMatcher

# Add backend to sys.path to import merge utilities
BACKEND_PATH = r"/home/user/agent/other_side/backend"
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)

try:
    from merge.file_merger import apply_single_task_changes
    from merge.types import TaskSnapshot, SemanticChange, ChangeType
except ImportError:
    # Fallback if backend is not available
    class ChangeType:
        MODIFY_FUNCTION = "modify_function"
    
    class SemanticChange:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class TaskSnapshot:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def apply_single_task_changes(baseline, snapshot, file_path):
        content = baseline
        for change in snapshot.semantic_changes:
            if change.content_before and change.content_after:
                content = content.replace(change.content_before, change.content_after)
        return content

console = Console()

class DiffTUI:
    """TUI for displaying file diffs in a style similar to modern web diff viewers."""
    
    def calculate_diff_stats(self, old_lines: List[str], new_lines: List[str]) -> Tuple[int, int]:
        matcher = SequenceMatcher(None, old_lines, new_lines)
        additions = 0
        deletions = 0
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'delete':
                deletions += (i2 - i1)
            elif tag == 'insert':
                additions += (j2 - j1)
            elif tag == 'replace':
                deletions += (i2 - i1)
                additions += (j2 - j1)
        return additions, deletions

    def render_summary(self, files_data: List[Dict]):
        total_additions = sum(f['additions'] for f in files_data)
        total_deletions = sum(f['deletions'] for f in files_data)
        files_count = len(files_data)
        
        header_table = Table.grid(expand=True)
        header_table.add_column(justify="left")
        header_table.add_column(justify="right")
        
        left_side = Text()
        left_side.append("📁 ", style="blue")
        left_side.append(f"{files_count} ", style="bold white")
        left_side.append("file" if files_count == 1 else "files", style="dim white")
        left_side.append(" changed", style="dim white")
        
        right_side = Text()
        right_side.append(f"+{total_additions} ", style="bold green")
        right_side.append(f"-{total_deletions} ", style="bold red")
        
        console.print(Panel(header_table, box=ROUNDED, border_style="bright_black", padding=(0, 1)))

    def render_diff(self, file_path: str, old_content: str, new_content: str):
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        matcher = SequenceMatcher(None, old_lines, new_lines)
        
        additions, deletions = self.calculate_diff_stats(old_lines, new_lines)

        # File header (Card-like)
        path_parts = file_path.split('/')
        filename = path_parts[-1]
        directory = "/".join(path_parts[:-1]) + "/" if len(path_parts) > 1 else ""
        
        title = Text()
        title.append("  ", style="on bright_black")
        title.append(" 📝 ", style="bright_yellow on bright_black")
        if directory:
            title.append(directory, style="dim white on bright_black")
        title.append(filename, style="bold white on bright_black")
        title.append("  ", style="on bright_black")
        
        if additions + deletions > 100:
            title.append("  ")
            title.append(" LARGE CHANGES ", style="black on yellow bold")
        
        stats = Text()
        stats.append(f" +{additions} ", style="green")
        stats.append(f" -{deletions} ", style="red")

        # Diff Table
        grid = Table.grid(padding=(0, 0), expand=True)
        grid.add_column(width=5, justify="right") # Old line
        grid.add_column(width=5, justify="right") # New line
        grid.add_column(width=3, justify="center") # Sign
        grid.add_column(overflow="fold") # Content
        
        context_size = 3
        opcodes = matcher.get_opcodes()
        
        for idx, (tag, i1, i2, j1, j2) in enumerate(opcodes):
            if tag == 'equal':
                if i2 - i1 <= context_size * 2:
                    for i in range(i1, i2):
                        grid.add_row(
                            Text(str(i + 1), style="dim"), 
                            Text(str(j1 + (i - i1) + 1), style="dim"), 
                            " ", 
                            Text(old_lines[i], style="dim")
                        )
                else:
                    if idx > 0:
                        for i in range(i1, i1 + context_size):
                            grid.add_row(
                                Text(str(i + 1), style="dim"), 
                                Text(str(j1 + (i - i1) + 1), style="dim"), 
                                " ", 
                                Text(old_lines[i], style="dim")
                            )
                    
                    grid.add_row(
                        Text("...", style="dim"), 
                        Text("...", style="dim"), 
                        " ", 
                        Text("...", style="dim")
                    )
                    
                    if idx < len(opcodes) - 1:
                        for i in range(i2 - context_size, i2):
                            grid.add_row(
                                Text(str(i + 1), style="dim"), 
                                Text(str(j1 + (i - i1) + 1), style="dim"), 
                                " ", 
                                Text(old_lines[i], style="dim")
                            )
            
            elif tag == 'delete':
                for i in range(i1, i2):
                    grid.add_row(
                        Text(str(i + 1), style="red on rgb(60,20,20)"), 
                        Text("", style="on rgb(60,20,20)"), 
                        Text("-", style="bold red on rgb(60,20,20)"), 
                        Text(old_lines[i], style="red on rgb(60,20,20)")
                    )
            
            elif tag == 'insert':
                for j in range(j1, j2):
                    grid.add_row(
                        Text("", style="on rgb(20,60,20)"), 
                        Text(str(j + 1), style="green on rgb(20,60,20)"), 
                        Text("+", style="bold green on rgb(20,60,20)"), 
                        Text(new_lines[j], style="green on rgb(20,60,20)")
                    )
            
            elif tag == 'replace':
                for i in range(i1, i2):
                    grid.add_row(
                        Text(str(i + 1), style="red on rgb(60,20,20)"), 
                        Text("", style="on rgb(60,20,20)"), 
                        Text("-", style="bold red on rgb(60,20,20)"), 
                        Text(old_lines[i], style="red on rgb(60,20,20)")
                    )
                for j in range(j1, j2):
                    grid.add_row(
                        Text("", style="on rgb(20,60,20)"), 
                        Text(str(j + 1), style="green on rgb(20,60,20)"), 
                        Text("+", style="bold green on rgb(20,60,20)"), 
                        Text(new_lines[j], style="green on rgb(20,60,20)")
                    )

        panel = Panel(
            grid,
            title=title,
            title_align="left",
            subtitle=stats,
            subtitle_align="right",
            box=ROUNDED,
            border_style="bright_black",
            padding=(0, 0)
        )
        console.print(panel)

def show_diff(file_path: str, old_content: str, new_content: str):
    """Bridge function to the new DiffTUI renderer."""
    tui = DiffTUI()
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    additions, deletions = tui.calculate_diff_stats(old_lines, new_lines)
    
    tui.render_summary([{'file': file_path, 'additions': additions, 'deletions': deletions}])
    tui.render_diff(file_path, old_content, new_content)

def patch_file(working_directory: str, file_path: str, content_before: str, content_after: str) -> str:
    """
    Apply a targeted change to a file instead of rewriting it.
    
    Args:
        working_directory: The base working directory
        file_path: Relative path to the file to patch
        content_before: The exact block of code to replace
        content_after: The new block of code to insert
    
    Returns:
        Success or error message
    """
    abs_working_dir = os.path.abspath(working_directory)
    abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))
    
    if not abs_file_path.startswith(abs_working_dir):
        return f'Error: Access denied - {file_path} is outside working directory'
    
    if not os.path.exists(abs_file_path):
        return f'Error: File {file_path} does not exist'
    
    try:
        # Read file
        with open(abs_file_path, 'r', encoding='utf-8') as f:
            baseline = f.read()
        
        # Create a mock snapshot for the merger
        change = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target=file_path,
            location="unknown",
            line_start=1,
            line_end=1,
            content_before=content_before,
            content_after=content_after
        )
        
        snapshot = TaskSnapshot(
            task_id="patch_task",
            task_intent=f"Patching {file_path}",
            started_at=datetime.now(),
            semantic_changes=[change]
        )
        
        # Apply the changes
        modified_content = apply_single_task_changes(baseline, snapshot, file_path)
        
        if modified_content == baseline:
            if content_before not in baseline:
                return f"Error: Could not find the 'content_before' block in {file_path}. Please ensure the content matches exactly (including whitespace)."
            return f"Notice: No changes were applied to {file_path}. The provided content might already be present."

        # Show TUI style diff
        show_diff(file_path, baseline, modified_content)
        
        # Write changes
        with open(abs_file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
            
        return f"Successfully updated '{file_path}'."
    
    except Exception as e:
        return f"Error patching file {file_path}: {str(e)}"

# Schema definition for the AI agent
schema_patch_file = types.FunctionDeclaration(
    name="patch_file",
    description="Update a specific part of a file by replacing a block of code with a new one. This is safer and more efficient than rewriting the entire file.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="The relative path to the file to patch.",
            ),
            "content_before": types.Schema(
                type=types.Type.STRING,
                description="The EXACT block of code as it currently exists in the file. MUST match exactly, including whitespace and indentation.",
            ),
            "content_after": types.Schema(
                type=types.Type.STRING,
                description="The new block of code that should replace the 'content_before' block.",
            ),
        },
        required=["file_path", "content_before", "content_after"],
    ),
)
