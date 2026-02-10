#call_function
import os
from google.genai import types

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

def call_function(function_call: types.FunctionCall, verbose: bool = False) -> types.Content:
    """
    Route function calls to appropriate handlers with live CLI display.
    
    Args:
        function_call: The function call object from the AI
        verbose: Whether to display verbose output
    
    Returns:
        Content object with function response
    """
    function_name = function_call.name
    args = function_call.args
    working_directory = os.getcwd()
    
    # Show function call info (always show for commands)
    if function_name == "patch_file":
        pass
    if function_name in ['run_shell', 'run_python_file']:
        # For execution commands, show minimal header
        console.print()
    elif function_name in ['build_project', 'install_dependencies']:
        # For build commands, show special header
        console.print()
        action_text = Text()
        action_text.append("🔨 Build Operation: ", style="bold magenta")
        action_text.append(function_name, style="yellow bold")
        console.print(Panel(
            action_text,
            border_style="magenta",
            padding=(0, 2)
        ))
    elif function_name.startswith('mcp_'):
        # For MCP commands, show special header
        console.print()
        action_text = Text()
        action_text.append("🔌 MCP Operation: ", style="bold blue")
        action_text.append(function_name, style="yellow bold")
        console.print(Panel(
            action_text,
            border_style="blue",
            padding=(0, 2)
        ))
    elif function_name.startswith('create_team') or function_name.startswith('assign_task') or function_name.startswith('execute_team'):
        # For team commands, show special header
        console.print()
        action_text = Text()
        action_text.append("🤖 Team Operation: ", style="bold cyan")
        action_text.append(function_name, style="yellow bold")
        console.print(Panel(
            action_text,
            border_style="cyan",
            padding=(0, 2)
        ))
    elif verbose or function_name in ['get_files_info', 'get_file_content', 'write_file']:
        # For other functions, show what's happening
        action_text = Text()
        if function_name == "get_files_info":
            path = args.get("path", ".")
            recursive = args.get("recursive", False)
            action = "Listing files recursively" if recursive else "Listing files"
            action_text.append(f"{action} in: ", style="cyan")
            action_text.append(path, style="yellow bold")
        elif function_name == "get_file_content":
            action_text.append("Reading file: ", style="cyan")
            action_text.append(args.get("file_path"), style="yellow bold")
        elif function_name == "write_file":
            action_text.append("Writing file: ", style="cyan")
            action_text.append(args.get("file_path"), style="yellow bold")
        else:
            action_text.append(f"Calling: {function_name}", style="cyan")
        
        console.print(Panel(
            action_text,
            border_style="cyan",
            padding=(0, 2)
        ))
    
    # Import functions locally to avoid circular imports
    try:
        # ===================================================================
        # MEMORY FUNCTIONS
        # ===================================================================
        if function_name == "memory_save_file_purpose":
            from func.memory_functions import memory_save_file_purpose
            result = memory_save_file_purpose(
                working_directory=args.get("working_directory", working_directory),
                filepath=args.get("filepath"),
                purpose=args.get("purpose")
            )
            console.print(f"[green]{result}[/green]\n")
        
        elif function_name == "memory_add_pattern":
            from func.memory_functions import memory_add_pattern
            result = memory_add_pattern(
                working_directory=args.get("working_directory", working_directory),
                pattern=args.get("pattern")
            )
            console.print(f"[green]{result}[/green]\n")
        
        elif function_name == "memory_add_gotcha":
            from func.memory_functions import memory_add_gotcha
            result = memory_add_gotcha(
                working_directory=args.get("working_directory", working_directory),
                gotcha=args.get("gotcha")
            )
            console.print(f"[yellow]{result}[/yellow]\n")
        
        elif function_name == "memory_get_context":
            from func.memory_functions import memory_get_context
            result = memory_get_context(
                working_directory=args.get("working_directory", working_directory)
            )
            console.print(f"[cyan]{result}[/cyan]\n")
        
        elif function_name == "memory_get_stats":
            from func.memory_functions import memory_get_stats
            result = memory_get_stats(
                working_directory=args.get("working_directory", working_directory)
            )
            console.print(f"[cyan]{result}[/cyan]\n")
        
        elif function_name == "memory_clear":
            from func.memory_functions import memory_clear
            result = memory_clear(
                working_directory=args.get("working_directory", working_directory)
            )
            console.print(f"[red]{result}[/red]\n")
        
        # ===================================================================
        # MCP CLIENT FUNCTIONS
        # ===================================================================
        elif function_name == "mcp_start_server":
            from func.mcp_client import mcp_start_server
            result = mcp_start_server(
                working_directory=args.get("working_directory", working_directory),
                server_name=args.get("server_name")
            )
            console.print(f"[cyan]{result}[/cyan]\n")
        
        elif function_name == "mcp_stop_server":
            from func.mcp_client import mcp_stop_server
            result = mcp_stop_server(
                working_directory=args.get("working_directory", working_directory),
                server_name=args.get("server_name")
            )
            console.print(f"[yellow]{result}[/yellow]\n")
        
        elif function_name == "mcp_list_tools":
            from func.mcp_client import mcp_list_tools
            result = mcp_list_tools(
                working_directory=args.get("working_directory", working_directory)
            )
            console.print(f"[cyan]{result}[/cyan]\n")
        
        elif function_name == "mcp_call_tool":
            from func.mcp_client import mcp_call_tool
            result = mcp_call_tool(
                working_directory=args.get("working_directory", working_directory),
                tool_name=args.get("tool_name"),
                arguments=args.get("arguments", {})
            )
            console.print(f"[green]{result}[/green]\n")
        
        elif function_name == "mcp_status":
            from func.mcp_client import mcp_status
            result = mcp_status(
                working_directory=args.get("working_directory", working_directory)
            )
            console.print(f"[cyan]{result}[/cyan]\n")
        
        # ===================================================================
        # BUILD PROJECT FUNCTIONS
        # ===================================================================
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
            # Live output is already shown by the function itself
            console.print(f"[cyan]{result}[/cyan]\n")
        
        elif function_name == "patch_file":
            from func.patch_file import patch_file

            result = patch_file(
                working_directory,
                file_path=args.get("file_path"),
                content_before=args.get("content_before"),
                content_after=args.get("content_after")
            )

            # لا تطبع result
            # patch_file تطبع كل شيء بنفسها

        elif function_name == "install_dependencies":
            from func.build import install_dependencies
            result = install_dependencies(
                working_directory=args.get("working_directory", working_directory),
                package_manager=args.get("package_manager", "npm"),
                timeout=args.get("timeout", 300),
                show_live=True
            )
            # Live output is already shown by the function itself
            console.print(f"[cyan]{result}[/cyan]\n")
        
        # ===================================================================
        # TEAM AGENT FUNCTIONS
        # ===================================================================
        elif function_name == "create_team":
            from func.team_functions import create_team
            result = create_team(
                working_directory,
                team_size=args.get("team_size", 4),
                roles=args.get("roles", []),
                delegation_mode=args.get("delegation_mode", True),
                planning_mode=args.get("planning_mode", False)
            )
            console.print(f"[cyan]{result}[/cyan]\n")
        
        elif function_name == "assign_task_to_team":
            from func.team_functions import assign_task_to_team
            result = assign_task_to_team(
                working_directory,
                title=args.get("title"),
                description=args.get("description"),
                priority=args.get("priority", 5),
                required_skills=args.get("required_skills", []),
                dependencies=args.get("dependencies", [])
            )
            console.print(f"[cyan]{result}[/cyan]\n")
        
        elif function_name == "get_team_status":
            from func.team_functions import get_team_status
            result = get_team_status(working_directory)
            console.print(f"[cyan]{result}[/cyan]\n")
        
        elif function_name == "get_team_messages":
            from func.team_functions import get_team_messages
            result = get_team_messages(
                working_directory,
                agent_id=args.get("agent_id", "all"),
                limit=args.get("limit", 10)
            )
            console.print(f"[cyan]{result}[/cyan]\n")
        
        elif function_name == "execute_team_tasks":
            from func.team_functions import execute_team_tasks
            result = execute_team_tasks(
                working_directory,
                max_iterations=args.get("max_iterations", 10),
                verbose=args.get("verbose", False)
            )
            console.print(f"[green]{result}[/green]\n")
        
        elif function_name == "shutdown_team":
            from func.team_functions import shutdown_team
            result = shutdown_team(working_directory)
            console.print(f"[yellow]{result}[/yellow]\n")
        
        # ===================================================================
        # ORIGINAL SDX AGENT FUNCTIONS
        # ===================================================================
        elif function_name == "get_files_info":
            from func.get_files_info import get_files_info
            result = get_files_info(
                working_directory,
                path=args.get("path", "."),
                recursive=args.get("recursive", False)
            )
            # Show result for file listings
            console.print(f"[dim]{result}[/dim]\n")
        
        elif function_name == "get_file_content":
            from func.get_file_content import get_file_content
            result = get_file_content(
                working_directory,
                file_path=args.get("file_path")
            )
            # Show snippet of file content
            lines = result.split('\n')
            if len(lines) > 20:
                preview = '\n'.join(lines[:20]) + f"\n[dim]... ({len(lines)} total lines)[/dim]"
            else:
                preview = result
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
            # Live output is already shown by the function itself
        
        elif function_name == "run_shell":
            from func.run_shell import run_shell
            result = run_shell(
                working_directory,
                command=args.get("command"),
                timeout=args.get("timeout", 30)
            )
            # Live output is already shown by the function itself
        
        else:
            result = f"Error: Unknown function '{function_name}'"
            console.print(f"[red]{result}[/red]\n")
    
    except Exception as e:
        result = f"Error executing {function_name}: {str(e)}"
        console.print(f"[red bold]✗ {result}[/red bold]\n")
        import traceback
        if verbose:
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
    
    # Return as Content object
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