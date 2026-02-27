"""
Function Call Router
Routes AI function calls to appropriate handlers with live CLI display
"""

import os
from google.genai import types

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# ============================================================================
# TEAM TOOLS — shared tool set passed to every team member
# ============================================================================

def _build_team_tools() -> types.Tool:
    from func.get_files_info import schema_get_files_info
    from func.get_file_content import schema_get_file_content
    from func.write_file import schema_write_file
    from func.run_python_file import schema_run_python_file
    from func.run_shell import schema_run_shell
    from func.patch_file import schema_patch_file
    from func.build import schema_build_project, schema_install_dependencies
    from func.task_executor import schema_execute_task
    from func.plan_project import schema_plan_project

    return types.Tool(function_declarations=[
        schema_get_files_info,
        schema_get_file_content,
        schema_run_python_file,
        schema_write_file,
        schema_run_shell,
        schema_build_project,
        schema_install_dependencies,
        schema_patch_file,
        schema_plan_project,
        schema_execute_task,
    ])


def _get_teams_instance():
    """Lazy singleton — one TeamsCLI instance reused across all calls"""
    if not hasattr(_get_teams_instance, "_instance"):
        from team_agent.teams_cli import TeamsCLI
        _get_teams_instance._instance = TeamsCLI(
            env_path=".env",
            tools=_build_team_tools()
        )
    return _get_teams_instance._instance


# ============================================================================
# MAIN ROUTER
# ============================================================================

def call_function(function_call: types.FunctionCall, verbose: bool = False) -> types.Content:
    """
    Route function calls to appropriate handlers with live CLI display.
    """
    function_name = function_call.name
    args = function_call.args
    working_directory = os.getcwd()

    # ── Display hints ────────────────────────────────────────────────────────
    if function_name == "patch_file":
        pass
    elif function_name in ['run_shell', 'run_python_file']:
        console.print()
    elif function_name in ['build_project', 'install_dependencies']:
        console.print()
        action_text = Text()
        action_text.append("Build Operation: ", style="bold magenta")
        action_text.append(function_name, style="yellow bold")
        console.print(Panel(action_text, border_style="magenta", padding=(0, 2)))
    elif function_name == "team_agent":
        console.print()
        action_text = Text()
        action_text.append("⚡ Team Agent: ", style="bold orange1")
        action_text.append(args.get("command", ""), style="cyan bold")
        console.print(Panel(action_text, border_style="orange1", padding=(0, 2)))
    elif verbose or function_name in ['get_files_info', 'write_file']:
        action_text = Text()
        if function_name == "get_files_info":
            path = args.get("path", ".")
            recursive = args.get("recursive", False)
            action = "Listing files recursively" if recursive else "Listing files"
            action_text.append(f"{action} in: ", style="cyan")
            action_text.append(path, style="yellow bold")
        elif function_name == "write_file":
            action_text.append("Writing file: ", style="cyan")
            action_text.append(args.get("file_path"), style="yellow bold")
        else:
            action_text.append(f"Calling: {function_name}", style="cyan")
        console.print(Panel(action_text, border_style="cyan", padding=(0, 2)))

    # ── Function routing ─────────────────────────────────────────────────────
    result = ""
    try:

        # ====================================================================
        # MEMORY FUNCTIONS
        # ====================================================================
        if function_name == "memory_add_pattern":
            from func.mem_integration import memory_add_pattern
            result = memory_add_pattern(
                category=args.get("category"),
                description=args.get("description"),
                example=args.get("example"),
                working_directory=working_directory
            )
            console.print(f"[green]✓ {result}[/green]\n")

        elif function_name == "memory_save_project_structure":
            from func.mem_integration import memory_save_project_structure
            result = memory_save_project_structure(
                structure=args.get("structure"),
                working_directory=working_directory
            )
            console.print(f"[green]✓ {result}[/green]\n")

        elif function_name == "memory_save_project_commands":
            from func.mem_integration import memory_save_project_commands
            result = memory_save_project_commands(
                commands=args.get("commands"),
                working_directory=working_directory
            )
            console.print(f"[green]✓ {result}[/green]\n")

        elif function_name == "memory_save_file_purpose":
            from func.mem_integration import memory_save_file_purpose
            result = memory_save_file_purpose(
                file_path=args.get("file_path"),
                purpose=args.get("purpose"),
                working_directory=working_directory
            )
            console.print(f"[green]✓ {result}[/green]\n")

        elif function_name == "memory_create_checkpoint":
            from func.mem_integration import memory_create_checkpoint
            result = memory_create_checkpoint(
                task_id=args.get("task_id"),
                description=args.get("description"),
                working_directory=working_directory
            )
            console.print(f"[cyan]✓ {result}[/cyan]\n")

        elif function_name == "memory_restore_checkpoint":
            from func.mem_integration import memory_restore_checkpoint
            result = memory_restore_checkpoint(
                checkpoint_id=args.get("checkpoint_id"),
                working_directory=working_directory
            )
            console.print(f"[cyan]{result}[/cyan]\n")

        elif function_name == "memory_list_checkpoints":
            from func.mem_integration import memory_list_checkpoints
            result = memory_list_checkpoints(working_directory=working_directory)
            console.print(f"[cyan]{result}[/cyan]\n")

        elif function_name == "memory_get_context":
            from func.mem_integration import memory_get_context
            result = memory_get_context(
                query=args.get("query"),
                working_directory=working_directory
            )
            console.print(f"[dim]{result}[/dim]\n")

        elif function_name == "memory_enable":
            from func.mem_integration import memory_enable
            result = memory_enable(working_directory=working_directory)
            console.print(f"[green]✓ {result}[/green]\n")

        elif function_name == "memory_disable":
            from func.mem_integration import memory_disable
            result = memory_disable(working_directory=working_directory)
            console.print(f"[yellow]✓ {result}[/yellow]\n")

        elif function_name == "memory_toggle_feature":
            from func.mem_integration import memory_toggle_feature
            result = memory_toggle_feature(
                feature=args.get("feature"),
                enabled=args.get("enabled"),
                working_directory=working_directory
            )
            console.print(f"[cyan]✓ {result}[/cyan]\n")

        elif function_name == "memory_get_stats":
            from func.mem_integration import memory_get_stats
            result = memory_get_stats(working_directory=working_directory)
            console.print(f"[cyan]{result}[/cyan]\n")

        elif function_name == "memory_cleanup":
            from func.mem_integration import memory_cleanup
            result = memory_cleanup(working_directory=working_directory)
            console.print(f"[yellow]✓ {result}[/yellow]\n")

        # ====================================================================
        # BUILD PROJECT FUNCTIONS
        # ====================================================================
        elif function_name == "build_project":
            from func.build import build_project
            result = build_project(
                working_directory=args.get("working_directory", working_directory),
                project_name=args.get("project_name"),
                project_type=args.get("project_type"),
                framework=args.get("framework", "nextjs"),
                options=args.get("options", {}),
                timeout=args.get("timeout", 300),
                show_live=True
            )
            console.print(f"[cyan]{result}[/cyan]\n")

        elif function_name == "patch_file":
            from func.patch_file import patch_file
            result = patch_file(
                working_directory,
                file_path=args.get("file_path"),
                content_before=args.get("content_before"),
                content_after=args.get("content_after")
            )

        elif function_name == "install_dependencies":
            from func.build import install_dependencies
            result = install_dependencies(
                working_directory=args.get("working_directory", working_directory),
                package_manager=args.get("package_manager", "npm"),
                timeout=args.get("timeout", 300),
                show_live=True
            )
            console.print(f"[cyan]{result}[/cyan]\n")

        # ====================================================================
        # TASK EXECUTION FUNCTION
        # ====================================================================
        elif function_name == "execute_task":
            from func.task_executor import execute_task
            result = execute_task(
                working_directory=working_directory,
                task_id=args.get("task_id"),
                subtask_title=args.get("subtask_title"),
                plan_file=args.get("plan_file")
            )
            console.print(f"[green]✓ Subtask marked complete[/green]")

        # ====================================================================
        # TEAM AGENT
        # ====================================================================
        elif function_name == "team_agent":
            teams = _get_teams_instance()
            command = args.get("command", "").strip()

            # Normalize — ensure it's a /team command
            if not command.lower().startswith("/team"):
                command = f"/team {command}"

            response = teams.handle(command)
            result = response or "Team command executed."
            if response:
                console.print(response)

        # ====================================================================
        # PLANNING FUNCTION
        # ====================================================================
        elif function_name == "plan_project":
            from func.plan_project import plan_project

            console.print()
            action_text = Text()
            action_text.append("🧠 AI Planning: ", style="bold blue")
            action_text.append(args.get("task_description", "Project Analysis"), style="cyan bold")
            console.print(Panel(action_text, border_style="blue", padding=(0, 2)))

            result = plan_project(
                working_directory=args.get("working_directory", working_directory),
                task_description=args.get("task_description"),
                file_patterns=args.get("file_patterns"),
                max_files=args.get("max_files", 50),
                max_file_size=args.get("max_file_size", 100000),
                include_dependencies=args.get("include_dependencies", True),
                save_plan=True,
                show_live=True
            )

            try:
                import json
                plan = json.loads(result)
                total_tasks = plan['metadata']['total_tasks']
                total_subtasks = plan['metadata']['total_subtasks']
                console.print(f"[green]✓ Generated {total_tasks} tasks with {total_subtasks} subtasks[/green]")
                console.print(f"[cyan]  Saved to plans/ directory[/cyan]\n")
            except Exception:
                console.print(f"[green]✓ Plan generated and saved[/green]\n")

        # ====================================================================
        # ORIGINAL SDX AGENT FUNCTIONS
        # ====================================================================
        elif function_name == "get_files_info":
            from func.get_files_info import get_files_info
            result = get_files_info(
                working_directory,
                path=args.get("path", "."),
                recursive=args.get("recursive", False)
            )
            console.print(f"[dim]{result}[/dim]\n")

        elif function_name == "get_file_content":
            from func.get_file_content import get_file_content

            file_path = args.get("file_path")
            start_line = args.get("start_line")
            end_line = args.get("end_line")

            result = get_file_content(
                working_directory,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line
            )

            lines = result.split('\n')
            range_info = None
            content_lines = lines

            if lines and lines[0].startswith("RANGE:"):
                range_parts = lines[0].replace("RANGE:", "").split(":")
                if len(range_parts) == 3:
                    start, end, total = range_parts
                    range_info = (int(start), int(end), int(total))
                    content_lines = lines[1:]

            console.print()
            header = Text()
            header.append("● ", style="bold blue")
            header.append("Read file ", style="bold white")
            header.append(f'"{file_path}"', style="bold cyan")
            if range_info:
                start, end, total = range_info
                header.append(f" L{start}-{end}", style="bold yellow")
            else:
                header.append(" (full file)", style="dim")
            console.print(header)

            summary = Text()
            summary.append(" └─ File: ", style="italic white")
            summary.append(file_path, style="italic bold cyan")
            if range_info:
                start, end, total = range_info
                summary.append(f" (lines {start}-{end} of {total})", style="italic dim")
            console.print(summary)
            console.print()

            preview_lines = content_lines[:20] if len(content_lines) > 20 else content_lines
            preview = '\n'.join(preview_lines)
            if len(content_lines) > 20:
                preview += f"\n[dim]... ({len(content_lines)} total lines)[/dim]"
            console.print(f"[dim]{preview}[/dim]\n")

        elif function_name == "write_file":
            from func.write_file import write_file
            result = write_file(
                working_directory,
                file_path=args.get("file_path"),
                content=args.get("content")
            )
            console.print(f"[green]{result}[/green]\n")

        elif function_name == "run_python_file":
            from func.run_python_file import run_python_file
            result = run_python_file(
                working_directory,
                file_path=args.get("file_path"),
                args=args.get("args", [])
            )

        elif function_name == "run_shell":
            from func.run_shell import run_shell
            result = run_shell(
                working_directory,
                command=args.get("command"),
                timeout=args.get("timeout", 30)
            )

        else:
            result = f"Error: Unknown function '{function_name}'"
            console.print(f"[red]{result}[/red]\n")

    except Exception as e:
        result = f"Error executing {function_name}: {str(e)}"
        console.print(f"[red bold]✗ {result}[/red bold]\n")
        if verbose:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")

    # ── Return to AI ─────────────────────────────────────────────────────────
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    name=function_name,
                    response={"result": result}
                )
            )
        ]
    )