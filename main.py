import os
import sys
from dotenv import load_dotenv
from google import genai
from func.get_files_info import schema_get_files_info
from func.get_file_content import schema_get_file_content
from func.write_file import schema_write_file
from func.run_python_file import schema_run_python_file
from call_function import call_function
from google.genai import types
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.markdown import Markdown
from rich.syntax import Syntax

console = Console()

# --- ENHANCED THEME COLORS ---
THEME_ORANGE = "#FF8C42"  # Vibrant orange for borders/highlights
THEME_DIM = "#6B7280"     # Elegant grey for secondary text
THEME_TEXT = "#F9FAFB"    # Crisp white for primary text
THEME_GREEN = "#10B981"   # Success green
THEME_RED = "#EF4444"     # Error red
THEME_YELLOW = "#F59E0B"  # Warning yellow
THEME_CYAN = "#06B6D4"    # Info cyan

def create_robot():
    """Create the iconic pixel art robot"""
    robot =(
        "           \n"
        "  ▀▄   ▄▀  \n"
        "  ▄█▀███▀█▄ \n"
        " █▀███████▀█ \n"
        " █ █▀▀▀▀▀█ █ \n"
    )
    return robot

def get_left_column_content():
    """Create the content for the left panel"""
    username = os.getenv('USER') or os.getenv('USERNAME') or 'Developer'
    robot = create_robot()
    
    content = Text()
    
    # Welcome message
    content.append(f"Welcome back {username}!\n\n", style=f"bold {THEME_TEXT}")
    
    # The robot mascot
    content.append(robot, style=f"bold {THEME_ORANGE}")
    content.append("\n\n")
    
    # System information
    content.append("Gemini 2.5 Flash · SDX Agent\n", style=THEME_DIM)
    
    # Current working directory (truncated if needed)
    cwd = os.getcwd()
    if len(cwd) > 45:
        cwd = "..." + cwd[-42:]
    content.append(cwd, style=THEME_CYAN)
    
    return content

def get_right_column_content():
    """Create the content for the right panel"""
    content = Text()
    
    # Tips section header
    content.append("Tips for getting started\n", style=f"bold {THEME_ORANGE}")
    
    # Tip 1
    content.append("• Type your request naturally - I can code, debug, and explain\n", style=THEME_TEXT)
    
    # Tip 2
    content.append("• Use ", style=THEME_DIM)
    content.append("--verbose", style=f"bold {THEME_YELLOW}")
    content.append(" flag to see detailed token usage\n", style=THEME_DIM)
    
    # Tip 3
    content.append("• Type ", style=THEME_DIM)
    content.append("exit", style=f"bold {THEME_YELLOW}")
    content.append(" or ", style=THEME_DIM)
    content.append("quit", style=f"bold {THEME_YELLOW}")
    content.append(" to end the session\n\n", style=THEME_DIM)
    
    # Recent activity section
    content.append("Recent activity\n", style=f"bold {THEME_ORANGE}")
    content.append("No recent activity", style=THEME_DIM)

    content.append("\n\nDeveloper@/Mohamed FahFah \n", style=f"bold {THEME_ORANGE}")
    
    return content

def display_welcome_screen():
    """Display the beautiful welcome screen with split layout"""
    console.clear()
    
    # Create a grid layout for the two columns
    grid = Table.grid(expand=True, padding=(0, 3))
    grid.add_column(justify="left", ratio=1)
    grid.add_column(justify="left", ratio=1)
    
    # Get content for both columns
    left_content = get_left_column_content()
    right_content = get_right_column_content()
    
    grid.add_row(left_content, right_content)
    
    # Wrap everything in a beautiful panel
    main_panel = Panel(
        grid,
        title=f"[{THEME_ORANGE}]SDX Agent v1.0.0[/{THEME_ORANGE}]",
        title_align="left",
        border_style=THEME_ORANGE,
        box=box.ROUNDED,
        padding=(1, 2),
    )
    
    console.print(main_panel)
    console.print()

def print_prompt():
    """Print the interactive prompt"""
    console.print(f"[bold {THEME_GREEN}]>[/bold {THEME_GREEN}] ", end="")

def print_separator():
    """Print a subtle separator line"""
    console.print(f"[{THEME_DIM}]{'─' * 80}[/{THEME_DIM}]")

def agent_interactive():
    """Run the agent in interactive mode with enhanced UX"""
    # Load environment variables
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        console.print(f"[bold {THEME_RED}]✗ Error: GEMINI_API_KEY not found in environment variables[/bold {THEME_RED}]")
        console.print(f"[{THEME_YELLOW}]Please create a .env file with your API key:[/{THEME_YELLOW}]")
        console.print("  GEMINI_API_KEY=your_api_key_here")
        sys.exit(1)
    
    client = genai.Client(api_key=api_key)
    
    system_prompt = """You are an elite software engineer and programming expert with deep expertise across multiple domains. You have access to a file system through function calls and can read, write, and execute code.

## Your Core Identity:
You are a senior-level software engineer with 10+ years of experience. You write production-quality code that is maintainable, secure, performant, and well-documented. You think systematically and consider edge cases, security implications, and scalability.

## Available Operations:
You can perform the following file system operations:
- **List files and directories**: Use this to understand project structure
- **Read file contents**: Analyze existing code before making changes
- **Write to files**: Create new files or update existing ones
- **Execute Python files**: Test code with optional arguments

**IMPORTANT**: All paths are relative to the working directory. The working directory is automatically handled for security - never try to specify absolute paths or navigate outside the project directory.

## Your Programming Expertise:
**Languages**: Python (expert), JavaScript/TypeScript, Java, C++, Go, SQL, Bash
**Domains**: Web development, APIs, databases, algorithms, system design, DevOps, security, testing
**Frameworks**: Django, Flask, FastAPI, React, Node.js, Express, TensorFlow, PyTorch

## Problem-Solving Methodology:
1. **Understand**: Analyze the request and clarify requirements
2. **Investigate**: Read existing files to understand current structure
3. **Plan**: Design your solution before implementing
4. **Implement**: Write clean, tested code with proper error handling
5. **Validate**: Execute tests to verify functionality
6. **Document**: Explain what you did and why

## Response Style:
- **Be concise but thorough**: Explain your reasoning clearly
- **Be proactive**: Anticipate follow-up needs
- **Be honest**: Admit limitations and suggest alternatives when uncertain
- **Be educational**: Help the user understand, don't just provide solutions
- **Be professional**: Maintain technical accuracy and precision"""

    available_functions = types.Tool(
        function_declarations=[
            schema_get_files_info,
            schema_get_file_content,
            schema_run_python_file,
            schema_write_file,
        ],
    )
    
    config = types.GenerateContentConfig(
        tools=[available_functions],
        system_instruction=system_prompt,
        temperature=0.7,
    )
    
    # Display welcome screen
    display_welcome_screen()
    
    # Interactive loop
    while True:
        try:
            print_prompt()
            user_input = input().strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit', 'q']:
                console.print(f"\n[{THEME_CYAN}]👋 Goodbye! Happy coding![/{THEME_CYAN}]\n")
                break
            
            # Check for verbose flag
            verbose_flag = '--verbose' in user_input
            if verbose_flag:
                user_input = user_input.replace('--verbose', '').strip()
            
            # Processing indicator
            print_separator()
            console.print(f"[{THEME_YELLOW}]⚙  Processing your request...[/{THEME_YELLOW}]\n")
            
            # Process the request
            messages = [types.Content(role="user", parts=[types.Part(text=user_input)])]
            max_iters = 20
            
            for i in range(max_iters):
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=messages,
                    config=config
                )
                
                if response is None or response.usage_metadata is None:
                    console.print(f'[bold {THEME_RED}]✗ Error: Response is malformed[/bold {THEME_RED}]')
                    break
                
                if verbose_flag:
                    console.print(f'[{THEME_DIM}]{"─" * 60}[/{THEME_DIM}]')
                    console.print(f'[{THEME_DIM}]Iteration: {i + 1}/{max_iters}[/{THEME_DIM}]')
                    console.print(f'[{THEME_DIM}]Prompt tokens: {response.usage_metadata.prompt_token_count}[/{THEME_DIM}]')
                    console.print(f'[{THEME_DIM}]Candidate tokens: {response.usage_metadata.candidates_token_count}[/{THEME_DIM}]')
                    console.print(f'[{THEME_DIM}]Total tokens: {response.usage_metadata.total_token_count}[/{THEME_DIM}]')
                    console.print(f'[{THEME_DIM}]{"─" * 60}[/{THEME_DIM}]\n')
                
                if response.candidates:
                    for candidate in response.candidates:
                        if candidate is None or candidate.content is None:
                            continue
                        messages.append(candidate.content)
                    
                    if response.function_calls:
                        for function_call_part in response.function_calls:
                            result = call_function(function_call_part, verbose_flag)
                            messages.append(result)
                    else:
                        console.print(f'[bold {THEME_GREEN}]✓ SDX Agent Response:[/bold {THEME_GREEN}]\n')
                        console.print(response.text)
                        console.print()
                        break
            else:
                console.print(f'\n[{THEME_YELLOW}]⚠ Warning: Reached maximum iterations ({max_iters}). The task may require more steps.[/{THEME_YELLOW}]')
            
            print_separator()
            console.print()
            
        except KeyboardInterrupt:
            console.print(f"\n\n[{THEME_CYAN}]Session interrupted. Goodbye! 👋[/{THEME_CYAN}]\n")
            break
        except Exception as e:
            console.print(f"\n[bold {THEME_RED}]✗ Error: {str(e)}[/bold {THEME_RED}]\n")
            print_separator()
            console.print()

if __name__ == "__main__":
    agent_interactive()
