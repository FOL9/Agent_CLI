import os
import sys
import json
import logging
import threading
import time
import shutil
import re
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
from func.run_shell import schema_run_shell
from func.patch_file import schema_patch_file
from func.build import (    
    schema_build_project,
    schema_install_dependencies
)

# MCP CLIENT FUNCTIONS
from func.mcp_client import (
    schema_mcp_start_server,
    schema_mcp_stop_server,
    schema_mcp_list_tools,
    schema_mcp_call_tool,
    schema_mcp_status,
    get_mcp_manager
)

# MEMORY FUNCTIONS
from func.memory_functions import (
    schema_memory_save_file_purpose,
    schema_memory_add_pattern,
    schema_memory_add_gotcha,
    schema_memory_get_context,
    schema_memory_get_stats,
    schema_memory_clear
)
from func.agent_memory import get_memory

# TEAM AGENT FUNCTIONS
from func.team_functions import (
    schema_create_team,
    schema_assign_task_to_team,
    schema_get_team_status,
    schema_get_team_messages,
    schema_execute_team_tasks,
    schema_shutdown_team,
    set_api_key
)

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

# Import prompt_toolkit for autocomplete
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, merge_completers
from prompt_toolkit.styles import Style as PromptStyle


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
    CYANa = "#ffffff"
    PURPLE = "#A78BFA"
    BLUE = "#3B82F6"


# ============================================================================
# AUTOCOMPLETE SYSTEM
# ============================================================================

class CommandCompleter(Completer):
    """Completer for / commands"""
    
    COMMANDS = [
        'help', 'history', 'clear', 'status', 
        'monitor_on', 'monitor_off', 'reload', 'exit', 'quit', 'q',
        'team_help', 'mcp_help'  # New commands
    ]
    
    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor(pattern=re.compile(r'/[^\s]*'))
        
        if not word_before_cursor.startswith('/'):
            return
        
        search_term = word_before_cursor[1:].lower()
        
        for cmd in self.COMMANDS:
            if search_term in cmd.lower():
                yield Completion(
                    f"/{cmd}",
                    start_position=-len(word_before_cursor),
                    display=f"/{cmd}"
                )


class FilePathCompleter(Completer):
    """Completer for @ file paths"""
    
    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor(pattern=re.compile(r'@[^\s]*'))
        
        if not word_before_cursor.startswith('@'):
            return
        
        search_term = word_before_cursor[1:].lower()
        
        # Walk through directories
        for root, dirs, files in os.walk('.'):
            # Filter out hidden folders and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', '.git']]
            
            for entry in files + dirs:
                # Build the relative path
                full_path = os.path.join(root, entry)
                display_path = full_path.replace('./', '', 1) if full_path.startswith('./') else full_path
                
                # Check if search term is in the path
                if search_term in display_path.lower():
                    # Add indicator for directories
                    display = f"@{display_path}/" if entry in dirs else f"@{display_path}"
                    yield Completion(
                        f"@{display_path}",
                        start_position=-len(word_before_cursor),
                        display=display
                    )


# Custom prompt style matching the dark theme
autocomplete_style = PromptStyle.from_dict({
    'completion-menu': 'bg:#121212 fg:#888888',
    'completion-menu.completion.current': 'bg:#222222 fg:#ffffff',
    'completion-menu.completion': 'fg:#888888',
})


# ============================================================================
# TERMINAL SIZE UTILITIES
# ============================================================================

class TerminalUtils:
    """Utilities for responsive terminal handling"""
    
    @staticmethod
    def get_terminal_size() -> tuple:
        """Get current terminal dimensions"""
        try:
            return shutil.get_terminal_size()
        except:
            return (80, 24)
    
    @staticmethod
    def get_width() -> int:
        """Get terminal width"""
        return TerminalUtils.get_terminal_size()[0]
    
    @staticmethod
    def get_height() -> int:
        """Get terminal height"""
        return TerminalUtils.get_terminal_size()[1]
    
    @staticmethod
    def truncate_text(text: str, max_width: int, suffix: str = "...") -> str:
        """Truncate text to fit width"""
        if len(text) <= max_width:
            return text
        return text[:max_width - len(suffix)] + suffix
    
    @staticmethod
    def wrap_text(text: str, width: int) -> List[str]:
        """Wrap text to specified width"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1
            if current_length + word_length <= width:
                current_line.append(word)
                current_length += word_length
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    @staticmethod
    def is_narrow_terminal() -> bool:
        """Check if terminal is narrow (less than 80 columns)"""
        return TerminalUtils.get_width() < 80


# ============================================================================
# THINKING ANIMATION
# ============================================================================

class ThinkingSpinner:
    """Animated thinking spinner with responsive width support"""
    
    FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    def __init__(self, prefix: str = "⚙  Processing your request", color: str = Theme.YELLOW):
        self.prefix = prefix
        self.color = color
        self.running = False
        self.thread = None
        self._frame_index = 0
    
    def _animate(self):
        """Animation loop with responsive text"""
        while self.running:
            frame = self.FRAMES[self._frame_index % len(self.FRAMES)]
            width = TerminalUtils.get_width()
            
            display_prefix = TerminalUtils.truncate_text(self.prefix, width - 10)
            
            sys.stdout.write(f'\r\033[{self._get_color_code()}m{display_prefix} {frame}\033[0m')
            sys.stdout.flush()
            self._frame_index += 1
            time.sleep(0.08)
    
    def _get_color_code(self):
        """Convert hex color to ANSI color code"""
        color_map = {
            Theme.CYAN: '96',
            Theme.GREEN: '92',
            Theme.YELLOW: '93',
            Theme.ORANGE: '91',
            Theme.PURPLE: '95',
            Theme.BLUE: '94',
        }
        return color_map.get(self.color, '93')
    
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
            
            width = TerminalUtils.get_width()
            if success_msg:
                msg = TerminalUtils.truncate_text(success_msg, width - 5)
                sys.stdout.write(f'\r\033[92m✔\033[0m {msg}\n')
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
        self.monitoring_enabled = False
        
        log_file = self.log_dir / f"sdx_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format="( %(asctime)s )",
            handlers=[
                RichHandler(console=Console(), show_time=True, show_path=True),
                logging.FileHandler(log_file)
            ]
        )
        self.logger = logging.getLogger("SDX Agent")
        
        self.rich_handler = None
        self.file_handler = None
        for handler in self.logger.handlers:
            if isinstance(handler, RichHandler):
                self.rich_handler = handler
            elif isinstance(handler, logging.FileHandler):
                self.file_handler = handler
        
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
        'team_help': 'Show Team Agent help and examples',
        'mcp_help': 'Show MCP integration help',
        'reload': 'Reload the agent',
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
        
        if cmd == 'reload':
            return "RELOAD"
        
        if cmd in ['exit', 'quit', 'q']:
            return "EXIT"
        
        if cmd == 'help':
            return self._show_help()
        
        if cmd == 'team_help':
            return self._show_team_help()
        
        if cmd == 'mcp_help':
            return self._show_mcp_help()
        
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
        """Show help with responsive formatting"""
        width = TerminalUtils.get_width()
        is_narrow = TerminalUtils.is_narrow_terminal()
        
        help_text = "Available Commands:\n"
        for cmd, desc in self.COMMANDS.items():
            if is_narrow:
                help_text += f"/{cmd}\n  {desc}\n"
            else:
                help_text += f"  /{cmd:<15} - {desc}\n"
        
        help_text += "\nFile Reference:\n"
        help_text += "  Type @ to autocomplete file paths\n"
        help_text += "  Example: @src/main.py\n"
        
        return help_text
    
    def _show_team_help(self) -> str:
        """Show Team Agent help"""
        return """
🤖 TEAM AGENT - COLLABORATIVE AI DEVELOPMENT

The Team Agent system allows you to spawn multiple specialized AI agents
that work together on complex tasks autonomously.

═══ CORE CONCEPTS ═══

1. PERSISTENT AGENTS
   - Agents stay active across multiple tasks
   - Build context and knowledge over time
   - Work independently but collaboratively

2. AUTONOMOUS TASK SELECTION
   - Agents self-assign tasks based on their skills
   - Score tasks by fit and priority
   - Make independent decisions

3. PEER-TO-PEER COMMUNICATION
   - Agents message each other directly
   - Broadcast team-wide updates
   - Escalate to Team Lead when needed

4. DEPENDENCY MANAGEMENT
   - Tasks can depend on other tasks
   - Automatic blocking until dependencies complete
   - Parallel execution when possible

═══ QUICK START ═══

Step 1: Create a team
"Create a team of 4 agents: backend dev, frontend dev, QA, and devops"

Step 2: Assign tasks
"Assign task to team: Build user authentication API with JWT"
"Assign task to team: Create login UI component (depends on API)"
"Assign task to team: Write integration tests (depends on API and UI)"

Step 3: Execute
"Execute team tasks"

Step 4: Check progress
"Get team status"
"Get team messages"

Step 5: Cleanup
"Shutdown the team"

═══ EXAMPLE USAGE ═══

User: "I need to build a complete blog system with backend, frontend, and tests. Can you create a team to handle this?"

Agent: [Creates team of 4 specialists]

User: "Assign these tasks:
1. Build REST API for blog posts (CRUD operations)
2. Create React components for blog listing and post detail
3. Add markdown editor for creating posts
4. Write API tests
5. Write UI tests"

Agent: [Assigns all tasks with proper dependencies]

User: "Execute team tasks"

Agent: [Agents work autonomously, communicate, complete tasks in parallel]

User: "Get team status"

Agent: [Shows all tasks completed, agents idle]

═══ MODES ═══

DELEGATION MODE (Default: ON)
- Team Lead only coordinates, doesn't execute
- Pure orchestration role
- Recommended for large teams

PLANNING MODE (Default: OFF)
- Agents submit execution plans before working
- Team Lead reviews and approves plans
- Good for high-risk changes

═══ ADVANCED FEATURES ═══

• Task Dependencies: Tasks wait for prerequisites
• Skill Matching: Agents select tasks matching their expertise
• Message Bus: Full inter-agent communication
• Permission Inheritance: All agents inherit Team Lead permissions
• Resource Management: Clean shutdown prevents leaks

═══ TIPS ═══

✓ Assign 3-6 agents for optimal performance
✓ Create specialized roles (backend, frontend, QA, devops, etc.)
✓ Use dependencies to sequence tasks correctly
✓ Check team messages to see agent collaboration
✓ Always shutdown teams when done

Try it now: "Create a team of 3 agents to build a simple todo app"
"""
    
    def _show_mcp_help(self) -> str:
        """Show MCP integration help"""
        return """
🔌 MCP INTEGRATION - EXTEND YOUR AGENT WITH EXTERNAL TOOLS

Model Context Protocol (MCP) allows you to connect external tool servers
to your agent, dramatically expanding its capabilities.

═══ WHAT IS MCP? ═══

MCP is a standard protocol for connecting AI assistants to external tools
and data sources. Think of it as a plugin system for your agent.

═══ AVAILABLE MCP SERVERS ═══

1. CHROME DEVTOOLS (@executeautomation/chrome-mcp)
   - Launch and control Chrome browser
   - Navigate to URLs, click elements
   - Fill forms, take screenshots
   - Execute JavaScript in browser context
   - Perfect for: web scraping, testing, automation

2. VERCEL SKILLS (@vercel/agent-skills)
   - Deploy projects to Vercel
   - Manage deployments
   - Configure domains
   - Perfect for: deployment automation

═══ QUICK START ═══

Step 1: Start an MCP server
"Start the chrome-devtools MCP server"

Step 2: List available tools
"List all MCP tools"

Step 3: Use the tools
"Use the chrome tool to navigate to https://example.com and take a screenshot"

Step 4: Stop when done
"Stop the chrome-devtools MCP server"

═══ EXAMPLE WORKFLOWS ═══

WEB AUTOMATION:
User: "Start chrome-devtools MCP server"
Agent: [Starts server, lists tools]
User: "Navigate to GitHub, search for 'python async', and screenshot the results"
Agent: [Uses chrome tools to automate the task]

DEPLOYMENT:
User: "Start vercel-skills MCP server"
Agent: [Starts server]
User: "Deploy my Next.js project to Vercel"
Agent: [Uses Vercel tools to deploy]

═══ CONFIGURATION ═══

MCP servers are configured in `mcp_config.json`:

{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "@executeautomation/chrome-mcp"],
      "env": {}
    },
    "vercel-skills": {
      "command": "npx",
      "args": ["-y", "@vercel/agent-skills"],
      "env": {
        "VERCEL_TOKEN": "your-token-here"
      }
    }
  }
}

═══ COMMANDS ═══

/mcp_status          - Show running MCP servers and tools
mcp_start_server     - Start an MCP server
mcp_stop_server      - Stop an MCP server
mcp_list_tools       - List all available MCP tools
mcp_call_tool        - Call a specific MCP tool

═══ TIPS ═══

✓ Start servers only when needed (they use resources)
✓ Always stop servers when done
✓ Check available tools with mcp_list_tools
✓ MCP servers run as background processes
✓ Some servers require authentication (set in env)

Try it now: "Start the chrome-devtools MCP server and show me what it can do"
"""
    
    def _show_history(self) -> str:
        """Show history with responsive formatting"""
        if not self.session.history:
            return "No chat history available."
        
        width = TerminalUtils.get_width()
        max_content_width = max(50, width - 20)
        
        history_text = "\n[Recent Chat History]\n"
        for i, msg in enumerate(self.session.history[-10:], 1):
            role = msg['role'].upper()
            content = msg['content']
            if len(content) > max_content_width:
                content = content[:max_content_width] + "..."
            history_text += f"{i}. [{role}] {content}\n"
        return history_text
    
    def _show_status(self) -> str:
        """Show status with responsive formatting"""
        cwd = os.getcwd()
        width = TerminalUtils.get_width()
        
        if len(cwd) > width - 25:
            cwd = "..." + cwd[-(width - 28):]
        
        monitor_status = "ON" if self.logger.monitoring_enabled else "OFF"
        
        # Check if team is active
        from func.team_functions import get_active_team
        team = get_active_team()
        team_status = "ACTIVE" if team else "NO TEAM"
        
        # Check MCP status
        mcp_manager = get_mcp_manager()
        mcp_status = f"{len(mcp_manager.servers)} SERVERS" if mcp_manager.servers else "NO SERVERS"
        
        # Check memory stats
        from func.agent_memory import get_memory
        memory = get_memory(cwd)
        mem_stats = memory.get_memory_stats()
        memory_status = f"{mem_stats['conversations']} convs, {mem_stats['files_mapped']} files"
        
        return (
            f"Working Directory: {cwd}\n"
            f"Session ID: {self.session.session_id}\n"
            f"Messages: {len(self.session.history)}\n"
            f"Memory: {memory_status}\n"
            f"Monitoring: {monitor_status}\n"
            f"Team Agent: {team_status}\n"
            f"MCP Servers: {mcp_status}\n"
            f"Shell Execution: ENABLED ⚠️\n"
            f"Autocomplete: ENABLED (/ for commands, @ for files)\n"
            f"Terminal Size: {width}x{TerminalUtils.get_height()}"
        )


# ============================================================================
# UI COMPONENTS
# ============================================================================

class UI:
    """Centralized UI rendering with responsive design"""
    
    def __init__(self):
        self.console = Console()
    
    def clear(self):
        self.console.clear()
    
    def create_robot(self) -> str:
        """Create pixel art robot (responsive)"""
        if TerminalUtils.is_narrow_terminal():
            return (
                "     ▀▄ ▄▀\n"
                "    ███████\n"
                "   ██▄███▄██\n"
                "    ███████\n"
                "    █ █ █ █\n"
            )
        else:
            return (
                "                               ▀▄   ▄▀    \n"
                "                              █████████   \n"
                "                             ██▄█████▄██  \n"
                "                              █████████   \n"
                "                              █ █   █ █   \n"
            )
    
    def welcome_screen(self):
        """Display enhanced responsive welcome screen"""
        self.clear()
        
        width = TerminalUtils.get_width()
        is_narrow = TerminalUtils.is_narrow_terminal()
        
        username = os.getenv('USER') or os.getenv('USERNAME') or 'Developer'
        cwd = os.getcwd()
        
        max_cwd_width = width - 10
        if len(cwd) > max_cwd_width:
            cwd = "..." + cwd[-(max_cwd_width - 3):]
        
        if is_narrow:
            content = Text()
            content.append(f"✻ SDX Agent v3.0\n", style=f"bold {Theme.TEXT}")
            content.append(self.create_robot(), style=f"bold {Theme.ORANGE}")
            content.append(f"\n/help - commands\n", style=f"italic {Theme.TEXT}")
            content.append(f"/team_help - teams\n", style=f"italic {Theme.TEXT}")
            content.append(f"/mcp_help - MCP\n", style=f"italic {Theme.TEXT}")
            content.append(f"@ - files\n", style=f"italic {Theme.TEXT}")
            content.append(f"CWD: {cwd}\n", style=f"italic {Theme.CYANa}")
        else:
            grid = Table.grid(expand=True, padding=(0, 3))
            grid.add_column(justify="left", ratio=1)
            grid.add_column(justify="left", ratio=1)
            
            left = Text()
            left.append(f" ✻ Welcome to SDX Agent!\n", style=f"bold {Theme.TEXT}")
            left.append(f" │\n", style=f"bold {Theme.TEXT}")
            left.append(" └──Type / for commands, @ for files\n", style=f"italic {Theme.TEXT}")   
            left.append("    /help - help, /team_help - teams\n", style=f"italic {Theme.TEXT}")
            left.append("    /mcp_help - MCP integration\n\n", style=f"italic {Theme.TEXT}")
            left.append(f" 🤖 Team Agent: ENABLED\n", style=f"bold {Theme.PURPLE}")
            left.append(f"    Multi-agent collaboration ready!\n\n", style=f"italic {Theme.DIM}")
            left.append(f" 🔌 MCP: ENABLED\n", style=f"bold {Theme.BLUE}")
            left.append(f"    External tools integration ready!\n\n", style=f"italic {Theme.DIM}")
            left.append(f" CWD: {cwd}", style=f"italic {Theme.CYANa}")                            
            
            right = Text()
            right.append(self.create_robot(), style=f" {Theme.ORANGE}")
            
            grid.add_row(left, right)
            content = grid
        
        panel = Panel(
            content,
            title=f"[{Theme.ORANGE}]SDX Agent v3.0.0 (MCP + Team Edition)[/{Theme.ORANGE}]",
            title_align="left",
            border_style=Theme.ORANGE,
            box=box.ROUNDED,
            padding=(1, 2),
        )
        
        self.console.print(panel)
        self.console.print()
    
    def separator(self):
        """Print responsive separator line"""
        width = min(TerminalUtils.get_width(), 80)
        self.console.print(f"[{Theme.DIM}]{'─' * width}[/{Theme.DIM}]")
    
    def success(self, title: str, content: str):
        """Display success message (responsive)"""
        width = TerminalUtils.get_width()
        wrapped_content = self._wrap_content(content, width - 10)
        
        panel = Panel(
            wrapped_content,
            title=f"[{Theme.GREEN}]✓ {title}[/{Theme.GREEN}]",
            border_style=Theme.GREEN,
            padding=(1, 2),
            expand=False
        )
        self.console.print(panel)
    
    def error(self, title: str, content: str):
        """Display error message (responsive)"""
        width = TerminalUtils.get_width()
        wrapped_content = self._wrap_content(content, width - 10)
        
        panel = Panel(
            wrapped_content,
            title=f"[{Theme.RED}]✗ {title}[/{Theme.RED}]",
            border_style=Theme.RED,
            padding=(1, 2),
            expand=False
        )
        self.console.print(panel)
    
    def warning(self, title: str, content: str):
        """Display warning message (responsive)"""
        width = TerminalUtils.get_width()
        wrapped_content = self._wrap_content(content, width - 10)
        
        panel = Panel(
            wrapped_content,
            title=f"[{Theme.YELLOW}]⚠ {title}[/{Theme.YELLOW}]",
            border_style=Theme.YELLOW,
            padding=(1, 2),
            expand=False
        )
        self.console.print(panel)
    
    def info(self, title: str, content: str):
        """Display info message (responsive)"""
        width = TerminalUtils.get_width()
        wrapped_content = self._wrap_content(content, width - 10)
        
        panel = Panel(
            wrapped_content,
            title=f"[{Theme.CYAN}]ℹ {title}[/{Theme.CYAN}]",
            border_style=Theme.CYAN,
            padding=(1, 2),
            expand=False
        )
        self.console.print(panel)
    
    def code(self, code: str, language: str = "python"):
        """Display formatted code (responsive)"""
        width = TerminalUtils.get_width()
        syntax = Syntax(
            code, 
            language, 
            theme="monokai", 
            line_numbers=not TerminalUtils.is_narrow_terminal(),
            word_wrap=True
        )
        self.console.print(syntax)
    
    def _wrap_content(self, content: str, max_width: int) -> str:
        """Wrap content to fit terminal width"""
        lines = content.split('\n')
        wrapped_lines = []
        for line in lines:
            if len(line) <= max_width:
                wrapped_lines.append(line)
            else:
                wrapped_lines.extend(TerminalUtils.wrap_text(line, max_width))
        return '\n'.join(wrapped_lines)

    def print_tool_execution(self, tool_name: str, args: Dict[str, Any], result: str = None):
        """Print a tool execution log line with 'Green Dot' style (same as main code)"""
        
        # Format the arguments string
        args_str = ""
        if tool_name in ["read_file", "get_file_content"]:
            args_str = f'"{args.get("file_path", "")}"'
            display_name = "Read file"
        elif tool_name == "write_file":
            args_str = f'"{args.get("file_path", "")}"'
            display_name = "Update file"
        elif tool_name == "patch_file":
            args_str = f'"{args.get("file_path", "")}"'
            display_name = "Patch file"
        elif tool_name in ["run_shell", "run_cmd"]:
            args_str = f'{args.get("command", "")}'
            display_name = "Run Cmd"
        elif tool_name == "run_python_file":
            args_str = f'"{args.get("file_path", "")}"'
            display_name = "Run Python"
        elif tool_name == "get_files_info":
            args_str = f'"{args.get("path", ".")}"'
            display_name = "List files"
        else:
            # Default fallback for team tools, build tools, MCP tools, etc.
            display_name = tool_name.replace("_", " ").capitalize()
            vals = list(args.values())
            if vals:
                args_str = f'"{str(vals[0])}"'
        
        # Print the header line: ● Patch file "testing/index.html"
        self.console.print(
            f"[green]●[/green] [bold white]{display_name}[/bold white] [yellow]{args_str}[/yellow]"
        )
        
        # Print the result preview (first line only)
        if result:
            preview = str(result).strip()
            lines = preview.split('\n')
            if lines:
                first_line = lines[0]
                if len(first_line) > 80:
                    first_line = first_line[:77] + "..."
                self.console.print(f"  [dim]└─ {first_line}[/dim]")


# ============================================================================
# AI AGENT
# ============================================================================

class SDXAgent:
    """Main AI Agent class with Team Agent and MCP integration"""
    
    SYSTEM_PROMPT = """You are an elite software engineer and cybersecurity expert with deep expertise across multiple domains. You have access to:

1. File system operations
2. Shell command execution
3. Persistent memory system (remembers context across conversations)
4. Team agent orchestration (multi-agent collaboration)
5. MCP (Model Context Protocol) for external tool integration

## Memory System
You have access to persistent memory that preserves context across conversations:
- **File Purposes**: Save what each file does after reading it
- **Code Patterns**: Remember patterns you discover in the codebase
- **Gotchas**: Store pitfalls to avoid
- **Conversations**: Access to recent conversation history

Memory Functions:
- memory_save_file_purpose: Save a file's purpose after understanding it
- memory_add_pattern: Store discovered code patterns
- memory_add_gotcha: Record pitfalls to avoid
- memory_get_context: Retrieve full memory context
- memory_get_stats: Check what's in memory

IMPORTANT: Use memory proactively! When you:
- Read a file → Save its purpose to memory
- Discover a pattern → Add it to memory
- Encounter a pitfall → Save it as a gotcha
- Start a complex task → Get memory context first

## MCP Integration
You can connect to external tool servers using MCP:
- Chrome DevTools: Browser automation, screenshots, web scraping
- Vercel Skills: Deployment and project management
- Custom MCP servers configured by the user

To use MCP:
1. Start an MCP server: mcp_start_server
2. List available tools: mcp_list_tools
3. Call tools: mcp_call_tool
4. Stop when done: mcp_stop_server

## Processing 
When presenting tasks, plans, or todos:
- Always use a clean monospace tree layout
- Use characters: │ └ ├ ─ •
- No markdown bullets, no emojis
- One top-level title
- Nested subtasks aligned vertically
- Short, action-focused sentences
- Format exactly like a terminal todo list

Example style (do not explain, just output):

Update Todos
│ Add FrameworkSelector component to ProjectSettings.tsx
│ Add framework preset state and logic to ProjectSettingsForm
│ Import necessary icons and types for framework presets
└ Test the framework preset functionality

## Security Note:
You operate in a controlled lab environment with full permissions. Always explain security implications of actions."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Set API key for team functions
        set_api_key(self.api_key)
        
        self.client = genai.Client(api_key=self.api_key)
        self.ui = UI()
        self.session = SessionManager()
        self.logger = logger
        self.command_handler = CommandHandler(self.session, self.ui.console, self.logger)
        self.max_iterations = 20
        
        # Initialize prompt session with autocomplete
        self.prompt_session = PromptSession(
            completer=merge_completers([
                CommandCompleter(),
                FilePathCompleter()
            ]),
            style=autocomplete_style,
            complete_while_typing=True,
            complete_in_thread=True
        )
    
    def get_tools(self) -> types.Tool:
        """Define available tools for the agent"""
        return types.Tool(
            function_declarations=[
                # Original SDX Agent tools
                schema_get_files_info,
                schema_get_file_content,
                schema_run_python_file,
                schema_write_file,
                schema_run_shell,
                # Memory tools
                schema_memory_save_file_purpose,
                schema_memory_add_pattern,
                schema_memory_add_gotcha,
                schema_memory_get_context,
                schema_memory_get_stats,
                schema_memory_clear,
                # MCP tools
                schema_mcp_start_server,
                schema_mcp_stop_server,
                schema_mcp_list_tools,
                schema_mcp_call_tool,
                schema_mcp_status,
                # Team Agent tools
                schema_create_team,
                schema_assign_task_to_team,
                schema_get_team_status,
                schema_get_team_messages,
                schema_execute_team_tasks,
                schema_shutdown_team,
                # Building 
                schema_build_project,
                schema_install_dependencies,
                # file patching 
                schema_patch_file

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
            spinner = ThinkingSpinner()
            spinner.start()
            
            # Get memory and inject context
            working_dir = os.getcwd()
            memory = get_memory(working_dir)
            memory_context = memory.get_full_context()
            
            # Prepend memory context to user input if available
            if memory_context:
                enhanced_input = f"{memory_context}\n\nUSER REQUEST:\n{user_input}"
            else:
                enhanced_input = user_input
            
            self.session.add_message("user", user_input)
            
            messages = [types.Content(role="user", parts=[types.Part(text=enhanced_input)])]
            config = self.get_config()
            
            all_function_calls = []  # Track function calls for memory
            
            for iteration in range(self.max_iterations):
                response = self.client.models.generate_content(
                    model='gemini-3-flash-preview',
                    contents=messages,
                    config=config
                )
                
                if response is None or response.usage_metadata is None:
                    spinner.stop()
                    self.ui.error("Response Error", "Response is malformed or empty")
                    self.logger.error("Malformed response from API")
                    break
                
                if verbose:
                    spinner.stop()
                    self._display_verbose_info(iteration, response)
                    spinner.start()
                
                if response.candidates:
                    for candidate in response.candidates:
                        if candidate and candidate.content:
                            messages.append(candidate.content)
                    
                    if response.function_calls:
                        spinner.stop()
                        
                        for function_call in response.function_calls:
                            # Track function call
                            all_function_calls.append({
                                "name": function_call.name,
                                "args": dict(function_call.args) if function_call.args else {}
                            })
                            
                            result_msg = call_function(function_call, verbose)
                            messages.append(result_msg)
                            
                            # Extract the actual tool result string safely
                            result_content = ""
                            try:
                                if result_msg.parts and result_msg.parts[0].function_response:
                                    result_content = result_msg.parts[0].function_response.response.get("result", "")
                            except Exception:
                                result_content = ""
                            
                            # Print the nice UI for this tool execution (same as main code)
                            self.ui.print_tool_execution(function_call.name, function_call.args, result_content)
                        
                        # Restart spinner for next iteration
                        spinner = ThinkingSpinner(prefix="⚙  Processing results", color=Theme.CYAN)
                        spinner.start()
                    else:
                        spinner.stop("Request complete")
                        response_text = response.text
                        self.session.add_message("assistant", response_text)
                        
                        # Save conversation to memory
                        memory.save_conversation(user_input, response_text, all_function_calls)
                        
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
        """Run agent in interactive mode with autocomplete"""
        self.ui.welcome_screen()
        self.logger.info("SDX Agent started with Team Agent and MCP integration")
        
        while True:
            try:
                # Use prompt_toolkit session for autocomplete
                user_input = self.prompt_session.prompt(
                    [('class:prompt', '→ ')],
                    style=PromptStyle.from_dict({'prompt': f'{Theme.GREEN}'})
                ).strip()
                
                if not user_input:
                    continue
                
                if self.command_handler.is_command(user_input):
                    result = self.command_handler.handle(user_input)
                    if result == "EXIT":
                        # Shutdown any active team
                        from func.team_functions import get_active_team, shutdown_team
                        if get_active_team():
                            self.ui.console.print("[yellow]Shutting down active team...[/yellow]")
                            shutdown_team(os.getcwd())
                        
                        # Stop all MCP servers
                        mcp_manager = get_mcp_manager()
                        if mcp_manager.servers:
                            self.ui.console.print("[yellow]Stopping MCP servers...[/yellow]")
                            import asyncio
                            try:
                                loop = asyncio.get_event_loop()
                            except RuntimeError:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                            loop.run_until_complete(mcp_manager.stop_all_servers())
                        
                        self.ui.info("Goodbye", "👋 Happy coding! Session saved.")
                        self.logger.info("Agent session ended gracefully")
                        break
                    
                    elif result == "RELOAD":
                        self.ui.info("Reloading", "♻ Restarting SDX Agent...")
                        self.logger.info("Reloading agent via /reload command")
                        python = sys.executable
                        os.execv(python, [python] + sys.argv)
                    
                    elif result:
                        self.ui.console.print(f"[{Theme.CYAN}]{result}[/{Theme.CYAN}]\n")
                    continue
                
                verbose_flag = '--verbose' in user_input
                if verbose_flag:
                    user_input = user_input.replace('--verbose', '').strip()
                
                self.ui.separator()
                self.process_request(user_input, verbose_flag)
                self.ui.separator()
                self.ui.console.print()
            
            except KeyboardInterrupt:
                # Shutdown any active team
                from func.team_functions import get_active_team, shutdown_team
                if get_active_team():
                    self.ui.console.print("\n[yellow]Shutting down active team...[/yellow]")
                    shutdown_team(os.getcwd())
                
                # Stop all MCP servers
                mcp_manager = get_mcp_manager()
                if mcp_manager.servers:
                    self.ui.console.print("[yellow]Stopping MCP servers...[/yellow]")
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    loop.run_until_complete(mcp_manager.stop_all_servers())
                
                self.ui.info("Interrupted", "Session interrupted. Goodbye! 👋")
                self.logger.info("Agent session interrupted by user")
                break
            except EOFError:
                self.ui.info("Goodbye", "👋 Happy coding! Session saved.")
                self.logger.info("Agent session ended (EOF)")
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
    
    load_dotenv()
    logger = Logger()
    logger.info("SDX Agent initializing with Team Agent and MCP integration...")
    
    try:
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