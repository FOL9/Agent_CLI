import os
import sys
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

from google import genai
from google.genai import types

from func.get_files_info import schema_get_files_info
from func.get_file_content import schema_get_file_content
from func.write_file import schema_write_file
from func.run_python_file import schema_run_python_file
from call_function import call_function

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax
from rich import box
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.logging import RichHandler


# ============================================================================
# THEME & STYLING
# ============================================================================

class Theme:
    """Centralized theme configuration"""
    ORANGE = "#FF8C42"
    DIM = "#6B7280"
    TEXT = "#F9FAFB"
    GREEN = "#10B981"
    RED = "#EF4444"
    YELLOW = "#F59E0B"
    CYAN = "#06B6D4"
    PURPLE = "#A78BFA"
    BLUE = "#3B82F6"


# ============================================================================
# THINKING ANIMATION
# ============================================================================

class ThinkingSpinner:
    """Animated thinking spinner with NPX-style loading effect"""
    
    FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    def __init__(self, prefix: str = "⚙  Processing your request", color: str = Theme.YELLOW):
        self.prefix = prefix
        self.color = color
        self.running = False
        self.thread = None
        self._frame_index = 0
    
    def _animate(self):
        """Animation loop"""
        while self.running:
            frame = self.FRAMES[self._frame_index % len(self.FRAMES)]
            sys.stdout.write(f'\r\033[{self._get_color_code()}m{self.prefix} {frame}\033[0m')
            sys.stdout.flush()
            self._frame_index += 1
            time.sleep(0.08)
    
    def _get_color_code(self):
        """Convert hex color to ANSI color code (approximation)"""
        color_map = {
            Theme.CYAN: '96',
            Theme.GREEN: '92',
            Theme.YELLOW: '93',
            Theme.ORANGE: '91',
            Theme.PURPLE: '95',
            Theme.BLUE: '94',
        }
        return color_map.get(self.color, '93')  # Default to yellow
    
    def start(self):
        """Start the spinner animation"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._animate, daemon=True)
            self.thread.start()
    
    def stop(self, success_msg: Optional[str] = None):
        """Stop the spinner animation"""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=0.2)
            
            if success_msg:
                sys.stdout.write(f'\r\033[92m✔\033[0m {success_msg}\n')
            else:
                sys.stdout.write('\r\033[92m✔\033[0m Done!       \n')
            sys.stdout.flush()
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if exc_type:
            sys.stdout.write('\r\033[91m✗\033[0m Failed!     \n')
            sys.stdout.flush()
        else:
            self.stop()


class Logger:
    """Enhanced logging system with monitoring toggle"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.monitoring_enabled = False  # Start with monitoring OFF
        
        log_file = self.log_dir / f"sdx_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                RichHandler(console=Console(), show_time=True, show_path=True),
                logging.FileHandler(log_file)
            ]
        )
        self.logger = logging.getLogger("SDXAgent")
        
        # Store handlers for toggling
        self.rich_handler = None
        self.file_handler = None
        for handler in self.logger.handlers:
            if isinstance(handler, RichHandler):
                self.rich_handler = handler
            elif isinstance(handler, logging.FileHandler):
                self.file_handler = handler
        
        # Initially disable console logging for external libraries
        self._set_external_logging(False)
    
    def enable_monitoring(self):
        """Enable monitoring - show all logs in console"""
        self.monitoring_enabled = True
        self._set_external_logging(True)
        if self.rich_handler:
            self.rich_handler.setLevel(logging.INFO)
        self.logger.info("🔍 Monitoring enabled - showing all requests and logs")
    
    def disable_monitoring(self):
        """Disable monitoring - hide external library logs"""
        self.monitoring_enabled = False
        self._set_external_logging(False)
        self.logger.info("🔇 Monitoring disabled - hiding verbose logs")
    
    def _set_external_logging(self, enabled: bool):
        """Control logging level for external libraries"""
        level = logging.INFO if enabled else logging.WARNING
        
        # Control Google GenAI and httpx logging
        logging.getLogger("google_genai").setLevel(level)
        logging.getLogger("httpx").setLevel(level)
        logging.getLogger("google.generativeai").setLevel(level)
        logging.getLogger("google.api_core").setLevel(level)
    
    def info(self, msg: str):
        self.logger.info(msg)
    
    def error(self, msg: str):
        self.logger.error(msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)
    
    def debug(self, msg: str):
        self.logger.debug(msg)


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

class SessionManager:
    """Manages chat history and session state"""
    
    def __init__(self, session_dir: str = "sessions"):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = self.session_dir / f"session_{self.session_id}.json"
        self.history: List[Dict[str, Any]] = []
        self.load_history()
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to session history"""
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        self.history.append(message)
        self.save_history()
    
    def save_history(self):
        """Save session history to file"""
        with open(self.session_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def load_history(self):
        """Load session history from file"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    self.history = json.load(f)
            except Exception as e:
                if logger:
                    logger.warning(f"Could not load session history: {e}")
                self.history = []
    
    def get_context(self, limit: int = 5) -> List[Dict]:
        """Get recent message context for the AI"""
        return self.history[-limit:]
    
    def clear_history(self):
        """Clear current session history"""
        self.history = []
        self.save_history()


# ============================================================================
# COMMAND HANDLER
# ============================================================================

class CommandHandler:
    """Handles special commands and shortcuts"""
    
    COMMANDS = {
        'help': 'Show help information',
        'history': 'Show chat history',
        'clear': 'Clear chat history',
        'status': 'Show agent status',
        'monitor_on': 'Enable request monitoring (show API calls)',
        'monitor_off': 'Disable request monitoring (hide API calls)',
        'exit': 'Exit the agent',
        'quit': 'Exit the agent',
        'q': 'Exit the agent (shorthand)',
    }
    
    def __init__(self, session: SessionManager, console: Console, logger: Logger):
        self.session = session
        self.console = console
        self.logger = logger
    
    def is_command(self, text: str) -> bool:
        """Check if input is a command"""
        return text.lower().strip().startswith('/') or text.lower().strip() in self.COMMANDS
    
    def handle(self, text: str) -> Optional[str]:
        """Handle special commands, return response or None"""
        cmd = text.lower().strip().lstrip('/')
        
        if cmd in ['exit', 'quit', 'q']:
            return "EXIT"
        
        if cmd == 'help':
            return self._show_help()
        
        if cmd == 'history':
            return self._show_history()
        
        if cmd == 'clear':
            self.session.clear_history()
            return "Chat history cleared."
        
        if cmd == 'status':
            return self._show_status()
        
        if cmd == 'monitor_on':
            self.logger.enable_monitoring()
            return "✓ Monitoring enabled - API requests will be shown"
        
        if cmd == 'monitor_off':
            self.logger.disable_monitoring()
            return "✓ Monitoring disabled - API requests hidden"
        
        return None
    
    def _show_help(self) -> str:
        help_text = "Available Commands:\n"
        for cmd, desc in self.COMMANDS.items():
            help_text += f"  /{cmd:<15} - {desc}\n"
        return help_text
    
    def _show_history(self) -> str:
        if not self.session.history:
            return "No chat history available."
        
        history_text = "\n[Recent Chat History]\n"
        for i, msg in enumerate(self.session.history[-10:], 1):
            role = msg['role'].upper()
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            history_text += f"{i}. [{role}] {content}\n"
        return history_text
    
    def _show_status(self) -> str:
        cwd = os.getcwd()
        monitor_status = "ON" if self.logger.monitoring_enabled else "OFF"
        return (
            f"Working Directory: {cwd}\n"
            f"Session ID: {self.session.session_id}\n"
            f"Messages: {len(self.session.history)}\n"
            f"Monitoring: {monitor_status}"
        )


# ============================================================================
# UI COMPONENTS
# ============================================================================

class UI:
    """Centralized UI rendering"""
    
    def __init__(self):
        self.console = Console()
    
    def clear(self):
        self.console.clear()
    
    def create_robot(self) -> str:
        """Create pixel art robot"""
        return (
            "            \n"
            "   ▀▄   ▄▀  \n"
            "   ▄█▀███▀█▄ \n"
            "  █▀███████▀█ \n"
            "  █ █▀▀▀▀▀█ █ \n"
        )
    
    def welcome_screen(self):
        """Display enhanced welcome screen"""
        self.clear()
        
        username = os.getenv('USER') or os.getenv('USERNAME') or 'Developer'
        
        grid = Table.grid(expand=True, padding=(0, 3))
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="left", ratio=1)
        
        # Left column
        left = Text()
        left.append(f" Welcome back {username}!\n\n", style=f"bold {Theme.TEXT}")
        left.append(self.create_robot(), style=f"bold {Theme.ORANGE}")
        left.append("\n\n Gemini 2.5 Flash · SDX Agent v2.0\n", style=Theme.DIM)
        cwd = os.getcwd()
        if len(cwd) > 45:
            cwd = "..." + cwd[-42:]
        left.append(f" \n Current working directory {cwd}", style=Theme.CYAN)
        
        # Right column
        right = Text()
        right.append(" Tips for Getting Started\n", style=f"bold {Theme.ORANGE}")
        right.append("• Type naturally - I code, debug, explain\n", style=Theme.TEXT)
        right.append("• Use ", style=Theme.DIM)
        right.append("--verbose", style=f"bold {Theme.YELLOW}")
        right.append(" for detailed token info\n", style=Theme.DIM)
        right.append("• Type ", style=Theme.DIM)
        right.append("/help", style=f"bold {Theme.YELLOW}")
        right.append(" for available commands\n", style=Theme.DIM)
        right.append("• Use ", style=Theme.DIM)
        right.append("/monitor_on", style=f"bold {Theme.YELLOW}")
        right.append(" to see API requests\n\n", style=Theme.DIM)
        
        right.append(" Quick Actions\n", style=f"bold {Theme.ORANGE}")
        right.append("• /status     - Show session info\n", style=Theme.TEXT)
        right.append("• /monitor_on - Enable API monitoring\n", style=Theme.TEXT)
        right.append("• /clear      - Clear chat history\n", style=Theme.TEXT)
        right.append("• /exit       - End session\n\n", style=Theme.TEXT)
        right.append("* Developer@Mohamed FahFah\n", style=f"bold {Theme.ORANGE}")
        
        grid.add_row(left, right)
        
        panel = Panel(
            grid,
            title=f"[{Theme.ORANGE}]SDX Agent v2.0.0[/{Theme.ORANGE}]",
            title_align="left",
            border_style=Theme.ORANGE,
            box=box.ROUNDED,
            padding=(1, 0),
        )
        
        self.console.print(panel)
        self.console.print()
    
    def prompt(self):
        """Print interactive prompt"""
        self.console.print(f"[bold {Theme.GREEN}]→[/bold {Theme.GREEN}] ", end="")
    
    def separator(self):
        """Print separator line"""
        self.console.print(f"[{Theme.DIM}]{'─' * 80}[/{Theme.DIM}]")
    
    def success(self, title: str, content: str):
        """Display success message"""
        panel = Panel(
            content,
            title=f"[{Theme.GREEN}]✓ {title}[/{Theme.GREEN}]",
            border_style=Theme.GREEN,
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def error(self, title: str, content: str):
        """Display error message"""
        panel = Panel(
            content,
            title=f"[{Theme.RED}]✗ {title}[/{Theme.RED}]",
            border_style=Theme.RED,
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def warning(self, title: str, content: str):
        """Display warning message"""
        panel = Panel(
            content,
            title=f"[{Theme.YELLOW}]⚠ {title}[/{Theme.YELLOW}]",
            border_style=Theme.YELLOW,
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def info(self, title: str, content: str):
        """Display info message"""
        panel = Panel(
            content,
            title=f"[{Theme.CYAN}]ℹ {title}[/{Theme.CYAN}]",
            border_style=Theme.CYAN,
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def code(self, code: str, language: str = "python"):
        """Display formatted code"""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self.console.print(syntax)


# ============================================================================
# AI AGENT
# ============================================================================

class SDXAgent:
    """Main AI Agent class with enhanced capabilities"""
    
    SYSTEM_PROMPT = """You are an elite software engineer and programming expert with deep expertise across multiple domains. You have access to a file system through function calls and can read, write, and execute code.

## Your Core Identity:
- Senior-level software engineer with 10+ years of experience
- You write production-quality code: maintainable, secure, performant, well-documented
- You think systematically, consider edge cases, security, and scalability
- You provide clear explanations and educational value

## Available Operations:
- **List files and directories**: Understand project structure
- **Read file contents**: Analyze existing code before changes
- **Write to files**: Create new files or update existing ones
- **Execute Python files**: Test code with optional arguments

## Programming Expertise:
- **Languages**: Python (expert), JavaScript/TypeScript, Java, C++, Go, SQL, Bash
- **Domains**: Web dev, APIs, databases, algorithms, system design, DevOps, security, testing
- **Frameworks**: Django, Flask, FastAPI, React, Node.js, Express, TensorFlow, PyTorch

## Problem-Solving Methodology:
1. **Understand**: Analyze request, clarify requirements
2. **Investigate**: Read existing files to understand structure
3. **Plan**: Design solution before implementing
4. **Implement**: Write clean, tested code with error handling
5. **Validate**: Execute tests to verify functionality
6. **Document**: Explain what and why

## Response Style:
- Be concise but thorough; explain reasoning clearly
- Be proactive; anticipate follow-up needs
- Be honest; admit limitations and suggest alternatives
- Be educational; help understand, not just provide solutions
- Be professional; maintain technical accuracy"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=self.api_key)
        self.ui = UI()
        self.session = SessionManager()
        self.logger = logger
        self.command_handler = CommandHandler(self.session, self.ui.console, self.logger)
        self.max_iterations = 20
    
    def get_tools(self) -> types.Tool:
        """Define available tools for the agent"""
        return types.Tool(
            function_declarations=[
                schema_get_files_info,
                schema_get_file_content,
                schema_run_python_file,
                schema_write_file,
            ],
        )
    
    def get_config(self) -> types.GenerateContentConfig:
        """Get AI model configuration"""
        return types.GenerateContentConfig(
            tools=[self.get_tools()],
            system_instruction=self.SYSTEM_PROMPT,
            temperature=0.7,
        )
    
    def process_request(self, user_input: str, verbose: bool = False):
        """Process user request with AI"""
        try:
            # Start thinking animation
            spinner = ThinkingSpinner()
            spinner.start()
            
            self.session.add_message("user", user_input)
            
            messages = [types.Content(role="user", parts=[types.Part(text=user_input)])]
            config = self.get_config()
            
            for iteration in range(self.max_iterations):
                response = self.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=messages,
                    config=config
                )
                
                if response is None or response.usage_metadata is None:
                    spinner.stop()
                    self.ui.error("Response Error", "Response is malformed or empty")
                    self.logger.error("Malformed response from API")
                    break
                
                if verbose:
                    self._display_verbose_info(iteration, response)
                
                if response.candidates:
                    for candidate in response.candidates:
                        if candidate and candidate.content:
                            messages.append(candidate.content)
                    
                    if response.function_calls:
                        for function_call in response.function_calls:
                            result = call_function(function_call, verbose)
                            messages.append(result)
                    else:
                        # Final response - stop spinner
                        spinner.stop("Request complete")
                        response_text = response.text
                        self.session.add_message("assistant", response_text)
                        self.ui.success("SDX Agent Response", response_text)
                        self.logger.info("Request processed successfully")
                        break
            else:
                spinner.stop()
                self.ui.warning(
                    "Max Iterations Reached",
                    f"Reached maximum iterations ({self.max_iterations}). Task may require more steps."
                )
                self.logger.warning(f"Max iterations reached for request: {user_input[:50]}...")
        
        except Exception as e:
            if 'spinner' in locals():
                spinner.stop()
            self.ui.error("Error Processing Request", str(e))
            self.logger.error(f"Error processing request: {e}")
    
    def _display_verbose_info(self, iteration: int, response):
        """Display verbose token and iteration information"""
        info_text = (
            f"Iteration: {iteration + 1}/{self.max_iterations}\n"
            f"Prompt tokens: {response.usage_metadata.prompt_token_count}\n"
            f"Candidate tokens: {response.usage_metadata.candidates_token_count}\n"
            f"Total tokens: {response.usage_metadata.total_token_count}"
        )
        self.ui.info("Token Usage", info_text)
    
    def run_interactive(self):
        """Run agent in interactive mode"""
        self.ui.welcome_screen()
        self.logger.info("SDX Agent started in interactive mode")
        
        while True:
            try:
                self.ui.prompt()
                user_input = input().strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if self.command_handler.is_command(user_input):
                    result = self.command_handler.handle(user_input)
                    if result == "EXIT":
                        self.ui.info("Goodbye", "👋 Happy coding! Session saved.")
                        self.logger.info("Agent session ended gracefully")
                        break
                    elif result:
                        self.ui.console.print(f"[{Theme.CYAN}]{result}[/{Theme.CYAN}]\n")
                    continue
                
                # Check for verbose flag
                verbose_flag = '--verbose' in user_input
                if verbose_flag:
                    user_input = user_input.replace('--verbose', '').strip()
                
                self.ui.separator()
                self.process_request(user_input, verbose_flag)
                self.ui.separator()
                self.ui.console.print()
            
            except KeyboardInterrupt:
                self.ui.info("Interrupted", "Session interrupted. Goodbye! 👋")
                self.logger.info("Agent session interrupted by user")
                break
            except Exception as e:
                self.ui.error("Unexpected Error", str(e))
                self.logger.error(f"Unexpected error in interactive loop: {e}", exc_info=True)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

logger = None

def main():
    """Main entry point"""
    global logger
    
    # Load environment variables
    load_dotenv()
    
    # Initialize logger
    logger = Logger()
    logger.info("SDX Agent initializing...")
    
    try:
        # Initialize and run agent
        agent = SDXAgent()
        agent.run_interactive()
    
    except ValueError as e:
        console = Console()
        console.print(f"[bold {Theme.RED}]✗ Configuration Error[/bold {Theme.RED}]")
        console.print(f"[{Theme.YELLOW}]Please create a .env file with:[/{Theme.YELLOW}]")
        console.print("  GEMINI_API_KEY=your_api_key_here")
        if logger:
            logger.error(str(e))
        sys.exit(1)
    
    except Exception as e:
        console = Console()
        console.print(f"[bold {Theme.RED}]✗ Fatal Error: {str(e)}[/bold {Theme.RED}]")
        if logger:
            logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
