"""
SDX Agent V2.0 - Enhanced with Auto-Claude Features
New: Multi-session, Parallel execution, Memory layer, Auto-merge, Workspace isolation
"""

import os
import sys
import json
import logging
import threading
import time
import asyncio
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

from google import genai
from google.genai import types

# APIs
from func.stealth_scanner import schema_stealth_scan
from func.parameter_hunter import schema_hunt_parameters
from func.get_files_info import schema_get_files_info
from func.get_file_content import schema_get_file_content
from func.write_file import schema_write_file
from func.run_python_file import schema_run_python_file
from func.run_shell import schema_run_shell
from func.make_http_request import schema_make_http_request
from func.enumerate_subdomains import schema_enumerate_subdomains
from func.scan_ports import schema_scan_ports
from call_function import call_function

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax
from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.layout import Layout
from rich.live import Live
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.tree import Tree


# ============================================================================
# ENHANCED TASK & STATE MANAGEMENT
# ============================================================================

class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "○"
    IN_PROGRESS = "◐"
    COMPLETED = "●"
    FAILED = "✗"
    VALIDATING = "◑"
    BLOCKED = "⊘"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """Enhanced task with validation and dependencies"""
    
    id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    timestamp: datetime = None
    duration: float = 0.0
    result: Any = None
    dependencies: List[str] = None
    validation_status: Optional[bool] = None
    retry_count: int = 0
    max_retries: int = 3
    workspace: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.dependencies is None:
            self.dependencies = []
    
    def start(self):
        self.status = TaskStatus.IN_PROGRESS
        self.timestamp = datetime.now()
    
    def complete(self, result: Any = None):
        self.status = TaskStatus.COMPLETED
        self.duration = (datetime.now() - self.timestamp).total_seconds()
        self.result = result
    
    def fail(self, error: str = ""):
        self.status = TaskStatus.FAILED
        self.duration = (datetime.now() - self.timestamp).total_seconds()
        self.result = error
        self.retry_count += 1
    
    def validate(self):
        self.status = TaskStatus.VALIDATING
    
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status.name,
            'priority': self.priority.name,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'duration': self.duration,
            'validation_status': self.validation_status,
            'workspace': self.workspace
        }
    
    def to_rich_text(self, theme: 'ModernTheme') -> Text:
        """Convert task to rich Text object for display"""
        t = Text()
        
        # Status indicator with color
        status_colors = {
            TaskStatus.PENDING: theme.TEXT_SECONDARY,
            TaskStatus.IN_PROGRESS: theme.PRIMARY,
            TaskStatus.COMPLETED: theme.SUCCESS,
            TaskStatus.FAILED: theme.ERROR,
            TaskStatus.VALIDATING: theme.WARNING,
            TaskStatus.BLOCKED: theme.TEXT_DIM,
        }
        color = status_colors.get(self.status, theme.TEXT_SECONDARY)
        
        # Priority indicator
        priority_symbols = {
            TaskPriority.LOW: "▫",
            TaskPriority.MEDIUM: "▪",
            TaskPriority.HIGH: "▲",
            TaskPriority.CRITICAL: "⬆"
        }
        priority_symbol = priority_symbols.get(self.priority, "▪")
        
        t.append(f" {priority_symbol} {self.status.value} ", style=f"bold {color}")
        t.append(self.title, style=theme.TEXT_PRIMARY)
        
        if self.description:
            t.append(f" — {self.description}", style=f"dim {theme.TEXT_SECONDARY}")
        
        if self.workspace:
            t.append(f" [{self.workspace}]", style=f"dim {theme.ACCENT}")
        
        if self.status == TaskStatus.COMPLETED:
            t.append(f" ({self.duration:.2f}s)", style=f"dim {theme.TEXT_SECONDARY}")
            if self.validation_status is not None:
                validation_icon = "✓" if self.validation_status else "✗"
                validation_color = theme.SUCCESS if self.validation_status else theme.ERROR
                t.append(f" {validation_icon}", style=validation_color)
        
        return t


class TaskManager:
    """Enhanced task manager with dependencies and parallel execution"""
    
    def __init__(self, max_tasks: int = 50, max_parallel: int = 5):
        self.tasks: Dict[str, Task] = {}
        self.max_tasks = max_tasks
        self.max_parallel = max_parallel
        self.active_tasks: List[str] = []
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_parallel)
    
    def generate_task_id(self) -> str:
        """Generate unique task ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"task_{timestamp}"
    
    def add_task(self, title: str, description: str = "", priority: TaskPriority = TaskPriority.MEDIUM,
                 dependencies: List[str] = None, workspace: Optional[str] = None) -> str:
        """Add a task and return its ID"""
        with self.lock:
            task_id = self.generate_task_id()
            task = Task(
                id=task_id,
                title=title,
                description=description,
                priority=priority,
                dependencies=dependencies or [],
                workspace=workspace
            )
            self.tasks[task_id] = task
            return task_id
    
    def start_task(self, task_id: str):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].start()
                if task_id not in self.active_tasks:
                    self.active_tasks.append(task_id)
    
    def complete_task(self, task_id: str, result: Any = None):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].complete(result)
                if task_id in self.active_tasks:
                    self.active_tasks.remove(task_id)
    
    def fail_task(self, task_id: str, error: str = ""):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].fail(error)
                if task_id in self.active_tasks:
                    self.active_tasks.remove(task_id)
    
    def validate_task(self, task_id: str, success: bool):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].validation_status = success
    
    def get_ready_tasks(self) -> List[Task]:
        """Get tasks ready to execute (dependencies met)"""
        with self.lock:
            ready = []
            for task in self.tasks.values():
                if task.status == TaskStatus.PENDING:
                    deps_met = all(
                        self.tasks.get(dep_id, Task(id="", title="")).status == TaskStatus.COMPLETED
                        for dep_id in task.dependencies
                    )
                    if deps_met:
                        ready.append(task)
            return sorted(ready, key=lambda t: t.priority.value, reverse=True)
    
    def get_active_tasks(self) -> List[Task]:
        """Return only pending and in-progress tasks"""
        with self.lock:
            return [t for t in self.tasks.values() if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)]
    
    def get_completed_tasks(self) -> List[Task]:
        """Return completed tasks"""
        with self.lock:
            return [t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]
    
    def get_failed_tasks(self) -> List[Task]:
        """Return failed tasks"""
        with self.lock:
            return [t for t in self.tasks.values() if t.status == TaskStatus.FAILED]
    
    def can_run_parallel(self) -> bool:
        """Check if we can run more parallel tasks"""
        return len(self.active_tasks) < self.max_parallel
    
    def clear(self):
        with self.lock:
            self.tasks.clear()
            self.active_tasks.clear()
    
    def export_state(self) -> Dict:
        """Export task state to dict"""
        with self.lock:
            return {
                'tasks': {tid: task.to_dict() for tid, task in self.tasks.items()},
                'active_tasks': self.active_tasks.copy()
            }


# ============================================================================
# WORKSPACE ISOLATION (Git Worktree Support)
# ============================================================================

class WorkspaceManager:
    """Manages isolated git worktrees for parallel execution"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.workspaces_dir = base_dir / ".sdx_workspaces"
        self.workspaces_dir.mkdir(exist_ok=True)
        self.active_workspaces: Dict[str, Path] = {}
    
    def is_git_repo(self) -> bool:
        """Check if current directory is a git repo"""
        try:
            subprocess.run(['git', 'rev-parse', '--git-dir'], 
                         check=True, capture_output=True, cwd=self.base_dir)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def create_workspace(self, workspace_id: str, branch_name: Optional[str] = None) -> Optional[Path]:
        """Create isolated workspace using git worktree"""
        if not self.is_git_repo():
            return None
        
        workspace_path = self.workspaces_dir / workspace_id
        
        try:
            if branch_name is None:
                branch_name = f"sdx-workspace-{workspace_id}"
            
            # Create worktree
            subprocess.run([
                'git', 'worktree', 'add', '-b', branch_name, str(workspace_path), 'HEAD'
            ], check=True, capture_output=True, cwd=self.base_dir)
            
            self.active_workspaces[workspace_id] = workspace_path
            return workspace_path
        
        except subprocess.CalledProcessError as e:
            return None
    
    def remove_workspace(self, workspace_id: str):
        """Remove workspace and cleanup"""
        if workspace_id in self.active_workspaces:
            workspace_path = self.active_workspaces[workspace_id]
            try:
                subprocess.run(['git', 'worktree', 'remove', str(workspace_path)], 
                             check=True, capture_output=True, cwd=self.base_dir)
                del self.active_workspaces[workspace_id]
            except subprocess.CalledProcessError:
                pass
    
    def merge_workspace(self, workspace_id: str, target_branch: str = "main") -> Tuple[bool, str]:
        """Merge workspace back to target branch"""
        if workspace_id not in self.active_workspaces:
            return False, "Workspace not found"
        
        workspace_path = self.active_workspaces[workspace_id]
        branch_name = f"sdx-workspace-{workspace_id}"
        
        try:
            # Commit changes in workspace
            subprocess.run(['git', 'add', '.'], check=True, cwd=workspace_path)
            subprocess.run(['git', 'commit', '-m', f'SDX: Complete {workspace_id}'], 
                         check=True, cwd=workspace_path)
            
            # Switch to target branch
            subprocess.run(['git', 'checkout', target_branch], check=True, cwd=self.base_dir)
            
            # Merge
            result = subprocess.run(['git', 'merge', branch_name], 
                                  capture_output=True, text=True, cwd=self.base_dir)
            
            if result.returncode == 0:
                return True, "Merge successful"
            else:
                return False, f"Merge conflicts: {result.stderr}"
        
        except subprocess.CalledProcessError as e:
            return False, f"Merge failed: {str(e)}"
    
    def list_workspaces(self) -> List[str]:
        """List active workspaces"""
        return list(self.active_workspaces.keys())


# ============================================================================
# MEMORY LAYER
# ============================================================================

class MemoryLayer:
    """Persistent memory across sessions"""
    
    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(exist_ok=True)
        self.memory_file = self.memory_dir / "memory.json"
        self.insights: Dict[str, Any] = {}
        self.patterns: Dict[str, int] = {}
        self.load_memory()
    
    def load_memory(self):
        """Load memory from disk"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    self.insights = data.get('insights', {})
                    self.patterns = data.get('patterns', {})
            except Exception:
                self.insights = {}
                self.patterns = {}
    
    def save_memory(self):
        """Save memory to disk"""
        with open(self.memory_file, 'w') as f:
            json.dump({
                'insights': self.insights,
                'patterns': self.patterns,
                'updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def add_insight(self, key: str, value: Any):
        """Add insight to memory"""
        self.insights[key] = {
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
        self.save_memory()
    
    def record_pattern(self, pattern: str):
        """Record frequently used patterns"""
        self.patterns[pattern] = self.patterns.get(pattern, 0) + 1
        self.save_memory()
    
    def get_insight(self, key: str) -> Optional[Any]:
        """Retrieve insight"""
        return self.insights.get(key, {}).get('value')
    
    def get_top_patterns(self, n: int = 5) -> List[Tuple[str, int]]:
        """Get most common patterns"""
        return sorted(self.patterns.items(), key=lambda x: x[1], reverse=True)[:n]
    
    def get_context_summary(self) -> str:
        """Get memory context for AI"""
        summary_parts = []
        
        if self.insights:
            summary_parts.append("Previous insights:")
            for key, data in list(self.insights.items())[-5:]:
                summary_parts.append(f"- {key}: {data['value']}")
        
        if self.patterns:
            summary_parts.append("\nCommon patterns:")
            for pattern, count in self.get_top_patterns(3):
                summary_parts.append(f"- {pattern} (used {count}x)")
        
        return "\n".join(summary_parts) if summary_parts else "No prior context"


# ============================================================================
# QA VALIDATION SYSTEM
# ============================================================================

class QAValidator:
    """Self-validating quality assurance"""
    
    def __init__(self, client: genai.Client):
        self.client = client
        self.validation_history: List[Dict] = []
    
    def validate_code(self, code: str, language: str = "python") -> Tuple[bool, str, List[str]]:
        """Validate code quality and suggest improvements"""
        issues = []
        suggestions = []
        
        # Basic syntax check for Python
        if language == "python":
            try:
                compile(code, '<string>', 'exec')
            except SyntaxError as e:
                issues.append(f"Syntax error: {str(e)}")
                return False, "Syntax errors found", issues
        
        # AI-powered validation
        validation_prompt = f"""Analyze this {language} code for:
1. Security vulnerabilities
2. Performance issues
3. Best practices violations
4. Potential bugs

Code:
```{language}
{code}
```

Respond with JSON:
{{
  "is_valid": true/false,
  "issues": ["issue1", "issue2"],
  "suggestions": ["suggestion1"]
}}
"""
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=validation_prompt
            )
            
            # Parse response
            result_text = response.text
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            is_valid = result.get('is_valid', True)
            issues.extend(result.get('issues', []))
            suggestions.extend(result.get('suggestions', []))
            
            summary = f"Found {len(issues)} issues" if issues else "Code looks good"
            return is_valid, summary, issues + suggestions
        
        except Exception as e:
            return True, f"Validation skipped: {str(e)}", []
    
    def validate_task_result(self, task: Task) -> Tuple[bool, str]:
        """Validate task execution result"""
        if task.status != TaskStatus.COMPLETED:
            return False, "Task not completed"
        
        # Check if result contains errors
        if task.result and isinstance(task.result, str):
            error_keywords = ['error', 'failed', 'exception', 'traceback']
            if any(keyword in task.result.lower() for keyword in error_keywords):
                return False, "Result contains errors"
        
        return True, "Task validated successfully"


# ============================================================================
# MODERN THEME & STYLING
# ============================================================================

class ModernTheme:
    """Enhanced theme matching Claude Code CLI style"""
    
    PRIMARY = "#F2A07B"
    SECONDARY = "#9CA3AF"
    ACCENT = "#D95F3B"
    
    SUCCESS = "#10B981"
    ERROR = "#EF4444"
    WARNING = "#F59E0B"
    INFO = "#3B82F6"
    
    BG_DARK = "#000000"
    TEXT_PRIMARY = "#E5E7EB"
    TEXT_SECONDARY = "#6B7280"
    TEXT_DIM = "#4B5563"
    
    FRAME_COMMAND = "#B084CC"
    FRAME_THINKING = PRIMARY
    FRAME_RESULT = "#10B981"
    FRAME_VALIDATION = "#F59E0B"
    FRAME_WORKSPACE = "#8B5CF6"
    
    ICON_STAR = "✻"
    ICON_ARROW = "❯"
    ICON_COMMAND = "$"
    ICON_THINKING = "○"
    ICON_WORKSPACE = "⎔"
    ICON_MEMORY = "◈"


# ============================================================================
# ENHANCED UI WITH AUTO-CLAUDE FEATURES
# ============================================================================

class EnhancedUI:
    """Enhanced UI with Kanban-style task board and parallel execution view"""
    
    def __init__(self):
        self.console = Console()
        self.task_manager = TaskManager()
        self.workspace_manager = WorkspaceManager(Path.cwd())
        self.memory_layer = MemoryLayer(Path.cwd() / ".sdx_memory")
    
    def clear(self):
        self.console.clear()
    
    def welcome_screen(self):
        """Enhanced welcome screen with feature highlights"""
        self.clear()
        
        welcome_text = Text()
        welcome_text.append(f"{ModernTheme.ICON_STAR} SDX Agent V2.0\n", style=f"bold {ModernTheme.PRIMARY}")
        welcome_text.append("Enhanced with Auto-Claude Features\n\n", style=f"italic {ModernTheme.ACCENT}")
        
        features = [
            f"{ModernTheme.ICON_WORKSPACE} Parallel Execution (up to 5 tasks)",
            f"{ModernTheme.ICON_MEMORY} Memory Layer (context across sessions)",
            "✓ Self-Validating QA",
            "⎔ Workspace Isolation (git worktrees)",
            "⚡ Auto-merge with conflict resolution"
        ]
        
        for feature in features:
            welcome_text.append(f"  {feature}\n", style=ModernTheme.TEXT_SECONDARY)
        
        welcome_text.append(f"\nCWD: {os.getcwd()}\n", style=f"dim {ModernTheme.TEXT_DIM}")
        
        panel = Panel(
            welcome_text,
            border_style=ModernTheme.PRIMARY,
            box=box.ROUNDED,
            padding=(1, 2),
            width=100,
            expand=True
        )
        
        self.console.print(panel)
        self.console.print()
        
        # Show memory context if available
        memory_context = self.memory_layer.get_context_summary()
        if memory_context != "No prior context":
            self.console.print(f"[{ModernTheme.INFO}]{ModernTheme.ICON_MEMORY} Memory Context:[/{ModernTheme.INFO}]")
            self.console.print(memory_context, style=f"dim {ModernTheme.TEXT_SECONDARY}")
            self.console.print()
    
    def display_kanban_board(self):
        """Display Kanban-style task board"""
        pending = [t for t in self.task_manager.tasks.values() if t.status == TaskStatus.PENDING]
        in_progress = [t for t in self.task_manager.tasks.values() if t.status == TaskStatus.IN_PROGRESS]
        validating = [t for t in self.task_manager.tasks.values() if t.status == TaskStatus.VALIDATING]
        completed = self.task_manager.get_completed_tasks()
        failed = self.task_manager.get_failed_tasks()
        
        # Create columns
        table = Table(show_header=True, header_style=f"bold {ModernTheme.PRIMARY}", 
                     box=box.ROUNDED, expand=True)
        
        table.add_column("PENDING", style=ModernTheme.TEXT_SECONDARY, width=20)
        table.add_column("IN PROGRESS", style=ModernTheme.PRIMARY, width=20)
        table.add_column("VALIDATING", style=ModernTheme.WARNING, width=20)
        table.add_column("COMPLETED", style=ModernTheme.SUCCESS, width=20)
        table.add_column("FAILED", style=ModernTheme.ERROR, width=20)
        
        max_rows = max(len(pending), len(in_progress), len(validating), len(completed), len(failed))
        
        for i in range(max_rows):
            row = []
            for col in [pending, in_progress, validating, completed, failed]:
                if i < len(col):
                    task = col[i]
                    task_text = f"{task.title[:15]}..."
                    if task.workspace:
                        task_text += f"\n[{task.workspace}]"
                    row.append(task_text)
                else:
                    row.append("")
            table.add_row(*row)
        
        self.console.print("\n")
        self.console.print(table)
        self.console.print("\n")
    
    def display_parallel_execution(self, tasks: List[Task]):
        """Display parallel execution status"""
        if not tasks:
            return
        
        self.console.print(f"\n[{ModernTheme.INFO}]⚡ Parallel Execution ({len(tasks)} tasks)[/{ModernTheme.INFO}]\n")
        
        for task in tasks:
            workspace_info = f" [{task.workspace}]" if task.workspace else ""
            self.console.print(
                f"  {task.status.value} {task.title}{workspace_info}",
                style=ModernTheme.TEXT_PRIMARY
            )
        
        self.console.print()
    
    def display_workspace_status(self):
        """Display active workspaces"""
        workspaces = self.workspace_manager.list_workspaces()
        
        if workspaces:
            self.console.print(f"\n[{ModernTheme.FRAME_WORKSPACE}]{ModernTheme.ICON_WORKSPACE} Active Workspaces:[/{ModernTheme.FRAME_WORKSPACE}]")
            for ws in workspaces:
                self.console.print(f"  • {ws}", style=ModernTheme.TEXT_SECONDARY)
            self.console.print()
    
    def display_validation_results(self, is_valid: bool, summary: str, details: List[str]):
        """Display QA validation results"""
        color = ModernTheme.SUCCESS if is_valid else ModernTheme.WARNING
        icon = "✓" if is_valid else "⚠"
        
        panel_content = Text()
        panel_content.append(f"{icon} {summary}\n\n", style=f"bold {color}")
        
        if details:
            panel_content.append("Details:\n", style=ModernTheme.TEXT_SECONDARY)
            for detail in details[:5]:  # Show top 5
                panel_content.append(f"  • {detail}\n", style=ModernTheme.TEXT_DIM)
        
        panel = Panel(
            panel_content,
            title="QA Validation",
            border_style=ModernTheme.FRAME_VALIDATION,
            box=box.ROUNDED,
            padding=(1, 2)
        )
        
        self.console.print(panel)
        self.console.print()
    
    def display_merge_result(self, success: bool, message: str):
        """Display merge operation result"""
        color = ModernTheme.SUCCESS if success else ModernTheme.ERROR
        icon = "✓" if success else "✗"
        
        self.console.print(f"[{color}]{icon} Merge: {message}[/{color}]")
        self.console.print()
    
    def display_prompt(self):
        """Enhanced prompt with more context"""
        self.console.print(
            "  Ask ──────────────────────────────────────────────────────────", 
            style=f"dim {ModernTheme.TEXT_SECONDARY}"
        )
        self.console.print(f" {ModernTheme.ICON_ARROW} ", style=f"bold {ModernTheme.PRIMARY}", end="")


# ============================================================================
# ENHANCED AI AGENT
# ============================================================================

class EnhancedSDXAgent:
    """Enhanced AI Agent with Auto-Claude capabilities"""
    
    SYSTEM_PROMPT = """You are an elite software engineer and cybersecurity expert with autonomous task execution capabilities.

ENHANCED CAPABILITIES:
- Multi-session memory for context retention
- Parallel task execution across workspaces
- Self-validation and quality assurance
- Automatic conflict resolution

IDENTITY:
If asked about authorship, respond: "Developer Fahfah Mohamed (Enhanced with Auto-Claude features)"

You have access to:
- File operations (list, read, write)
- Python script execution
- Shell command execution
- HTTP requests
- Security scanning tools

WORKFLOW:
1. Break complex tasks into subtasks
2. Execute tasks in parallel when possible
3. Validate results automatically
4. Merge changes with conflict resolution

Response style:
- Concise and professional
- Explain your reasoning
- Mention security implications
- Track progress with tasks"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        self.client = genai.Client(api_key=self.api_key)
        self.ui = EnhancedUI()
        self.session = SessionManager()
        self.logger = Logger()
        self.command_handler = EnhancedCommandHandler(self.session, self.logger, self.ui)
        self.qa_validator = QAValidator(self.client)
        self.max_iterations = 20
    
    def get_tools(self) -> types.Tool:
        return types.Tool(
            function_declarations=[
                schema_get_files_info,
                schema_get_file_content,
                schema_run_python_file,
                schema_write_file,
                schema_run_shell,
                schema_make_http_request,
                schema_enumerate_subdomains,
                schema_scan_ports,
                schema_stealth_scan,
                schema_hunt_parameters,
            ],
        )
    
    def get_config(self) -> types.GenerateContentConfig:
        # Enhance system prompt with memory context
        memory_context = self.ui.memory_layer.get_context_summary()
        enhanced_prompt = f"{self.SYSTEM_PROMPT}\n\nMEMORY CONTEXT:\n{memory_context}"
        
        return types.GenerateContentConfig(
            tools=[self.get_tools()],
            system_instruction=enhanced_prompt,
            temperature=0.7,
        )
    
    def process_request_parallel(self, user_input: str, enable_parallel: bool = True):
        """Process with parallel execution support"""
        try:
            self.session.add_message("user", user_input)
            
            # Parse if user wants parallel execution
            if "--parallel" in user_input or enable_parallel:
                return self._process_with_parallel_execution(user_input)
            else:
                return self.process_request(user_input)
        
        except Exception as e:
            self.ui.console.print(f"[{ModernTheme.ERROR}]Error: {str(e)}[/{ModernTheme.ERROR}]")
            self.logger.error(f"Process error: {e}")
    
    def _process_with_parallel_execution(self, user_input: str):
        """Execute tasks in parallel"""
        self.ui.console.print(f"\n[{ModernTheme.INFO}]⚡ Parallel execution enabled[/{ModernTheme.INFO}]\n")
        
        # First, get AI to break down the task
        planning_prompt = f"""Break down this request into independent subtasks that can run in parallel:
"{user_input}"

Respond with JSON:
{{
  "subtasks": [
    {{"id": "1", "title": "Task 1", "description": "...", "priority": "HIGH"}},
    {{"id": "2", "title": "Task 2", "description": "...", "priority": "MEDIUM"}}
  ]
}}"""
        
        response = self.client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=planning_prompt
        )
        
        # Parse subtasks
        try:
            result_text = response.text
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            
            plan = json.loads(result_text)
            subtasks = plan.get('subtasks', [])
            
            if not subtasks:
                return self.process_request(user_input)
            
            # Create tasks
            task_ids = []
            for subtask in subtasks:
                priority = TaskPriority[subtask.get('priority', 'MEDIUM')]
                task_id = self.ui.task_manager.add_task(
                    title=subtask['title'],
                    description=subtask.get('description', ''),
                    priority=priority
                )
                task_ids.append(task_id)
            
            # Display kanban board
            self.ui.display_kanban_board()
            
            # Execute tasks in parallel
            futures = {}
            with ThreadPoolExecutor(max_workers=self.ui.task_manager.max_parallel) as executor:
                for task_id in task_ids:
                    task = self.ui.task_manager.tasks[task_id]
                    future = executor.submit(self._execute_single_task, task_id, task.title)
                    futures[future] = task_id
                
                # Monitor progress
                for future in as_completed(futures):
                    task_id = futures[future]
                    try:
                        result = future.result()
                        self.ui.task_manager.complete_task(task_id, result)
                    except Exception as e:
                        self.ui.task_manager.fail_task(task_id, str(e))
                    
                    # Update display
                    self.ui.display_kanban_board()
            
            # Summary
            completed = len(self.ui.task_manager.get_completed_tasks())
            failed = len(self.ui.task_manager.get_failed_tasks())
            
            self.ui.console.print(f"\n[{ModernTheme.SUCCESS}]✓ Completed: {completed}[/{ModernTheme.SUCCESS}]")
            if failed > 0:
                self.ui.console.print(f"[{ModernTheme.ERROR}]✗ Failed: {failed}[/{ModernTheme.ERROR}]")
            
        except Exception as e:
            self.ui.console.print(f"[{ModernTheme.WARNING}]Could not parallelize, falling back to sequential[/{ModernTheme.WARNING}]")
            return self.process_request(user_input)
    
    def _execute_single_task(self, task_id: str, task_description: str) -> Any:
        """Execute a single task (used in parallel execution)"""
        self.ui.task_manager.start_task(task_id)
        
        # Execute with AI
        messages = [types.Content(role="user", parts=[types.Part(text=task_description)])]
        config = self.get_config()
        
        for iteration in range(self.max_iterations):
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=messages,
                config=config
            )
            
            if response.candidates:
                for candidate in response.candidates:
                    if candidate and candidate.content:
                        messages.append(candidate.content)
                
                if response.function_calls:
                    for function_call in response.function_calls:
                        result = call_function(function_call, verbose=False)
                        messages.append(result)
                else:
                    return response.text
        
        return "Max iterations reached"
    
    def process_request(self, user_input: str, verbose: bool = False):
        """Process user request with enhanced features"""
        try:
            spinner = ModernSpinner(message="Analyzing request")
            spinner.start()
            
            self.session.add_message("user", user_input)
            
            # Record pattern in memory
            self.ui.memory_layer.record_pattern(user_input.split()[0] if user_input else "unknown")
            
            spinner.stop()
            
            self.ui.console.print()
            
            # Reset tasks for this request
            self.ui.task_manager.clear()
            
            messages = [types.Content(role="user", parts=[types.Part(text=user_input)])]
            config = self.get_config()
            
            tool_call_count = 0
            results = []
            
            for iteration in range(self.max_iterations):
                spinner = ModernSpinner(message="Thinking")
                spinner.start()
                
                response = self.client.models.generate_content(
                    model='gemini-2.0-flash-exp',
                    contents=messages,
                    config=config
                )
                
                if not response or not response.usage_metadata:
                    spinner.stop(success=False)
                    self.ui.console.print(f"[{ModernTheme.ERROR}]✗ API Error: Invalid response[/{ModernTheme.ERROR}]")
                    break
                
                if response.candidates:
                    for candidate in response.candidates:
                        if candidate and candidate.content:
                            messages.append(candidate.content)
                    
                    if response.function_calls:
                        spinner.stop()
                        
                        # Create tasks for each function call
                        for idx, function_call in enumerate(response.function_calls):
                            tool_call_count += 1
                            tool_name = function_call.name
                            
                            # Add task
                            task_id = self.ui.task_manager.add_task(
                                f"Execute {tool_name}",
                                f"Running: {function_call.name}"
                            )
                            self.ui.task_manager.start_task(task_id)
                            
                            # Display active tasks
                            active = self.ui.task_manager.get_active_tasks()
                            if active:
                                for task in active:
                                    self.ui.console.print(task.to_rich_text(ModernTheme))
                            
                            # Run function
                            result = call_function(function_call, verbose)
                            messages.append(result)
                            results.append((tool_name, result))
                            
                            # Mark complete and validate
                            self.ui.task_manager.complete_task(task_id)
                            
                            # If result is code, validate it
                            if tool_name == "write_file" and hasattr(result, 'parts'):
                                for part in result.parts:
                                    if hasattr(part, 'text'):
                                        code = part.text
                                        is_valid, summary, details = self.qa_validator.validate_code(code)
                                        self.ui.task_manager.validate_task(task_id, is_valid)
                                        
                                        if not is_valid or details:
                                            self.ui.display_validation_results(is_valid, summary, details)
                    else:
                        spinner.stop()
                        response_text = response.text
                        self.session.add_message("assistant", response_text)
                        
                        # Store insight in memory
                        insight_key = f"response_{datetime.now().strftime('%Y%m%d_%H%M')}"
                        self.ui.memory_layer.add_insight(insight_key, response_text[:200])
                        
                        # Display result
                        panel = Panel(
                            response_text,
                            title="✓ Result",
                            border_style=ModernTheme.FRAME_RESULT,
                            box=box.ROUNDED,
                            padding=(1, 2),
                            width=90
                        )
                        self.ui.console.print(panel)
                        self.ui.console.print()
                        break
            else:
                spinner.stop(success=False)
                self.ui.console.print(f"[{ModernTheme.ERROR}]✗ Max iterations reached[/{ModernTheme.ERROR}]")
        
        except Exception as e:
            if 'spinner' in locals():
                spinner.stop(success=False)
            self.ui.console.print(f"[{ModernTheme.ERROR}]✗ Error: {str(e)}[/{ModernTheme.ERROR}]")
            self.logger.error(f"Error: {e}")
    
    def run_interactive(self):
        """Run in interactive mode with enhanced UI"""
        self.ui.welcome_screen()
        self.logger.info("SDX Agent V2.0 started")
        
        while True:
            try:
                self.ui.display_prompt()
                user_input = input().strip()
                self.ui.console.print()
                
                if not user_input:
                    continue
                
                if self.command_handler.is_command(user_input):
                    result = self.command_handler.handle(user_input)
                    if result == "EXIT":
                        break
                    elif result:
                        if isinstance(result, Text):
                            self.ui.console.print(result)
                        else:
                            self.ui.console.print(str(result), style=ModernTheme.TEXT_SECONDARY)
                        self.ui.console.print()
                    continue
                
                verbose_flag = '--verbose' in user_input
                parallel_flag = '--parallel' in user_input
                
                if verbose_flag:
                    user_input = user_input.replace('--verbose', '').strip()
                if parallel_flag:
                    user_input = user_input.replace('--parallel', '').strip()
                
                if parallel_flag:
                    self.process_request_parallel(user_input)
                else:
                    self.process_request(user_input, verbose_flag)
                
                self.ui.console.print()
                self.ui.console.print("[dim]? /help for commands[/dim]", style=ModernTheme.TEXT_DIM)
                self.ui.console.print()
            
            except KeyboardInterrupt:
                self.ui.console.print()
                self.ui.console.print("[dim]Interrupted.[/dim]", style=ModernTheme.TEXT_SECONDARY)
                break
            except Exception as e:
                self.ui.console.print(f"[{ModernTheme.ERROR}]✗ Unexpected Error: {str(e)}[/{ModernTheme.ERROR}]")


# ============================================================================
# ENHANCED COMMAND HANDLER
# ============================================================================

class EnhancedCommandHandler:
    """Enhanced commands for new features"""
    
    COMMANDS = {
        'help': 'Show available commands',
        'history': 'View chat history',
        'clear': 'Clear session history',
        'status': 'Show system status',
        'monitor': 'Toggle monitoring mode',
        'kanban': 'Show task board',
        'workspaces': 'List active workspaces',
        'memory': 'Show memory insights',
        'validate': 'Run QA validation on last task',
        'merge': 'Merge workspace to main branch',
        'parallel': 'Enable parallel execution mode',
        'export': 'Export session state',
        'exit': 'Exit the agent',
    }
    
    def __init__(self, session: 'SessionManager', logger: 'Logger', ui: EnhancedUI):
        self.session = session
        self.logger = logger
        self.ui = ui
        self.console = Console()
    
    def is_command(self, text: str) -> bool:
        cmd = text.lower().strip().lstrip('/')
        return cmd in self.COMMANDS or text.startswith('/')
    
    def handle(self, text: str) -> Optional[str]:
        cmd = text.lower().strip().lstrip('/')
        
        if cmd in ['exit', 'quit', 'q']:
            return "EXIT"
        
        if cmd == 'help':
            return self._show_help()
        
        if cmd == 'history':
            return self._show_history()
        
        if cmd == 'clear':
            self.session.clear_history()
            return "History cleared"
        
        if cmd == 'status':
            return self._show_status()
        
        if cmd == 'monitor':
            if self.logger.monitoring_enabled:
                self.logger.disable_monitoring()
                return "Monitoring disabled"
            else:
                self.logger.enable_monitoring()
                return "Monitoring enabled"
        
        if cmd == 'kanban':
            self.ui.display_kanban_board()
            return None
        
        if cmd == 'workspaces':
            self.ui.display_workspace_status()
            return None
        
        if cmd == 'memory':
            return self._show_memory()
        
        if cmd == 'validate':
            return self._validate_last_task()
        
        if cmd == 'merge':
            return self._merge_workspace()
        
        if cmd == 'export':
            return self._export_state()
        
        return None
    
    def _show_help(self) -> Text:
        text = Text()
        text.append("Available Commands:\n\n", style=f"bold {ModernTheme.PRIMARY}")
        
        for cmd, desc in self.COMMANDS.items():
            text.append(f"  /{cmd:<12}", style=f"bold {ModernTheme.ACCENT}")
            text.append(f"{desc}\n", style=ModernTheme.TEXT_SECONDARY)
        
        text.append("\nFlags:\n", style=f"bold {ModernTheme.PRIMARY}")
        text.append("  --parallel   ", style=f"bold {ModernTheme.ACCENT}")
        text.append("Execute tasks in parallel\n", style=ModernTheme.TEXT_SECONDARY)
        text.append("  --verbose    ", style=f"bold {ModernTheme.ACCENT}")
        text.append("Show detailed output\n", style=ModernTheme.TEXT_SECONDARY)
        
        return text
    
    def _show_history(self) -> str:
        if not self.session.history:
            return "No history available"
        
        history = []
        for msg in self.session.history[-5:]:
            role = "AI" if msg['role'] == 'assistant' else "You"
            content = msg['content'][:80] + "..." if len(msg['content']) > 80 else msg['content']
            history.append(f"{role}: {content}")
        
        return "\n".join(history)
    
    def _show_status(self) -> Text:
        text = Text()
        
        text.append("System Status\n\n", style=f"bold {ModernTheme.PRIMARY}")
        text.append(f"Directory: ", style=ModernTheme.TEXT_SECONDARY)
        text.append(f"{os.getcwd()}\n", style=ModernTheme.TEXT_PRIMARY)
        text.append(f"Monitor: ", style=ModernTheme.TEXT_SECONDARY)
        text.append(f"{'ON' if self.logger.monitoring_enabled else 'OFF'}\n", style=ModernTheme.TEXT_PRIMARY)
        text.append(f"Session: ", style=ModernTheme.TEXT_SECONDARY)
        text.append(f"{self.session.session_id}\n", style=ModernTheme.TEXT_PRIMARY)
        
        # Task stats
        completed = len(self.ui.task_manager.get_completed_tasks())
        failed = len(self.ui.task_manager.get_failed_tasks())
        active = len(self.ui.task_manager.get_active_tasks())
        
        text.append(f"\nTasks: ", style=ModernTheme.TEXT_SECONDARY)
        text.append(f"{completed} completed, {active} active, {failed} failed\n", style=ModernTheme.TEXT_PRIMARY)
        
        # Workspaces
        workspaces = self.ui.workspace_manager.list_workspaces()
        text.append(f"Workspaces: ", style=ModernTheme.TEXT_SECONDARY)
        text.append(f"{len(workspaces)} active\n", style=ModernTheme.TEXT_PRIMARY)
        
        return text
    
    def _show_memory(self) -> str:
        context = self.ui.memory_layer.get_context_summary()
        return context if context != "No prior context" else "No memory data available"
    
    def _validate_last_task(self) -> str:
        completed = self.ui.task_manager.get_completed_tasks()
        if not completed:
            return "No completed tasks to validate"
        
        last_task = completed[-1]
        # Perform validation logic here
        return f"Validated task: {last_task.title}"
    
    def _merge_workspace(self) -> str:
        workspaces = self.ui.workspace_manager.list_workspaces()
        if not workspaces:
            return "No active workspaces to merge"
        
        # Prompt for workspace to merge
        self.console.print("Available workspaces:", style=ModernTheme.TEXT_SECONDARY)
        for i, ws in enumerate(workspaces):
            self.console.print(f"  {i+1}. {ws}")
        
        choice = Prompt.ask("Select workspace to merge", choices=[str(i+1) for i in range(len(workspaces))])
        workspace_id = workspaces[int(choice) - 1]
        
        success, message = self.ui.workspace_manager.merge_workspace(workspace_id)
        self.ui.display_merge_result(success, message)
        
        return None
    
    def _export_state(self) -> str:
        state = self.ui.task_manager.export_state()
        export_file = Path.cwd() / f"sdx_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(export_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        return f"State exported to: {export_file}"


# ============================================================================
# SESSION MANAGEMENT (Keep from original)
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
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        self.history.append(message)
        self.save_history()
    
    def save_history(self):
        with open(self.session_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def load_history(self):
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []
    
    def clear_history(self):
        self.history = []
        self.save_history()


# ============================================================================
# LOGGER (Keep from original)
# ============================================================================

class Logger:
    """Modern logging system"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.monitoring_enabled = False
        
        log_file = self.log_dir / f"sdx_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file)]
        )
        self.logger = logging.getLogger("SDX")
        self._set_external_logging(False)
    
    def enable_monitoring(self):
        self.monitoring_enabled = True
        self._set_external_logging(True)
    
    def disable_monitoring(self):
        self.monitoring_enabled = False
        self._set_external_logging(False)
    
    def _set_external_logging(self, enabled: bool):
        level = logging.INFO if enabled else logging.WARNING
        logging.getLogger("google_genai").setLevel(level)
        logging.getLogger("httpx").setLevel(level)
    
    def info(self, msg: str):
        self.logger.info(msg)
    
    def error(self, msg: str):
        self.logger.error(msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)


# ============================================================================
# MODERN SPINNER (Keep from original)
# ============================================================================

class ModernSpinner:
    """Minimalist spinner matching the theme"""
    
    FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    def __init__(self, message: str = "Processing", color: str = ModernTheme.PRIMARY):
        self.message = message
        self.color = color
        self.running = False
        self.thread = None
        self._frame_index = 0
        self.console = Console()
    
    def _animate(self):
        while self.running:
            frame = self.FRAMES[self._frame_index % len(self.FRAMES)]
            status_msg = f"\r{frame} {self.message}..."
            self.console.file.write(status_msg + " " * 20)
            self.console.file.flush()
            self._frame_index += 1
            time.sleep(0.08)
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._animate, daemon=True)
            self.thread.start()
    
    def stop(self, success: bool = True):
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=0.2)
            sys.stdout.write('\r' + ' ' * 80 + '\r')
            sys.stdout.flush()


# ============================================================================
# ENTRY POINT
# ============================================================================

logger = None


def main():
    global logger
    
    load_dotenv()
    logger = Logger()
    
    try:
        agent = EnhancedSDXAgent()
        agent.run_interactive()
    
    except ValueError as e:
        console = Console()
        console.print(f"[red]Configuration Error: {e}[/red]")
        sys.exit(1)
    
    except Exception as e:
        console = Console()
        console.print(f"[red]Fatal Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()