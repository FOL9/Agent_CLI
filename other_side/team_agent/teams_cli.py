"""
Teams CLI — Terminal UI for the Team Agent System
Integrates with the existing SDX Agent rich/prompt_toolkit stack.

Commands:
  /team spawn <config>     - spawn team from inline config or preset
  /team status             - show all members + task board
  /team tasks              - show task list
  /team mail               - show mailbox
  /team chat <name> <msg>  - talk directly to a member
  /team assign <tid> <name>- manually assign task
  /team dismiss <name>     - dismiss a member
  /team dismiss all        - shut down entire team
  /team plan approve <name>- approve a member's plan
  /team plan reject <name> - reject with feedback

Or just talk normally → orchestrator handles it.
"""

import os
import sys
import json
import threading
import time
from typing import Optional, List
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich import box
from rich.rule import Rule
from rich.padding import Padding
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style as PromptStyle

from team_agent.team_engine import (
    APIKeyPool, AgentStatus, TaskStatus, MailScope
)
from team_agent.orchestrator import Orchestrator, MemberConfig

# ─────────────────────────────────────────────────────────────────────────────
# THEME (matches SDX Agent)
# ─────────────────────────────────────────────────────────────────────────────

ORANGE  = "#FF8C42"
GREEN   = "#10B981"
RED     = "#EF4444"
YELLOW  = "#F59E0B"
CYAN    = "#06B6D4"
PURPLE  = "#A78BFA"
DIM     = "#6B7280"
TEXT    = "#F9FAFB"

STATUS_COLOR = {
    AgentStatus.IDLE:      GREEN,
    AgentStatus.EXECUTING: CYAN,
    AgentStatus.PLANNING:  YELLOW,
    AgentStatus.WAITING:   PURPLE,
    AgentStatus.SHUTDOWN:  DIM,
}

TASK_COLOR = {
    TaskStatus.PENDING:     DIM,
    TaskStatus.IN_PROGRESS: CYAN,
    TaskStatus.COMPLETED:   GREEN,
    TaskStatus.BLOCKED:     YELLOW,
}


# ─────────────────────────────────────────────────────────────────────────────
# EVENT LOG (real-time output thread-safe)
# ─────────────────────────────────────────────────────────────────────────────

class EventLog:
    """Stores events from all agents for display"""

    EVENT_ICON = {
        "lifecycle": "◈",
        "task":      "◆",
        "mail":      "✉",
        "plan":      "📋",
        "plan_review":"🔍",
        "user_chat": "💬",
        "spawn":     "⚡",
        "error":     "✗",
    }

    EVENT_COLOR = {
        "lifecycle": CYAN,
        "task":      GREEN,
        "mail":      PURPLE,
        "plan":      YELLOW,
        "plan_review": ORANGE,
        "user_chat": TEXT,
        "spawn":     ORANGE,
        "error":     RED,
    }

    def __init__(self, console: Console, max_lines: int = 200):
        self.console = console
        self._events: List[dict] = []
        self._lock = threading.Lock()
        self.max_lines = max_lines

    def add(self, agent_id: str, event_type: str, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self._events.append({
                "ts": ts,
                "agent": agent_id,
                "type": event_type,
                "msg": message
            })
            if len(self._events) > self.max_lines:
                self._events = self._events[-self.max_lines:]
        self._print(ts, agent_id, event_type, message)

    def _print(self, ts: str, agent_id: str, event_type: str, message: str):
        icon  = self.EVENT_ICON.get(event_type, "·")
        color = self.EVENT_COLOR.get(event_type, DIM)
        agent_label = f"[{DIM}][{agent_id[:10]:>10}][/{DIM}]"
        self.console.print(
            f"[{DIM}]{ts}[/{DIM}] {agent_label} [{color}]{icon} {message}[/{color}]"
        )


# ─────────────────────────────────────────────────────────────────────────────
# RENDER HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def render_team_status(orchestrator: Orchestrator, console: Console):
    members = orchestrator.get_all_members_info()
    task_summary = orchestrator.task_list.summary()

    # Members table
    t = Table(
        title="[bold]Team Members[/bold]",
        box=box.SIMPLE_HEAD,
        border_style=ORANGE,
        show_lines=False,
        expand=False
    )
    t.add_column("ID",     style=DIM,  width=8)
    t.add_column("Name",   style=TEXT, width=14)
    t.add_column("Role",   style=CYAN, width=16)
    t.add_column("Status", width=12)
    t.add_column("Plan",   width=10)
    t.add_column("Task",   style=DIM,  width=10)
    t.add_column("API Key",style=DIM,  width=12)

    for m in members:
        status_color = STATUS_COLOR.get(AgentStatus(m["status"]), DIM)
        plan_str = (
            "[green]approved[/green]" if m["plan_approved"] else
            "[yellow]pending[/yellow]" if m["plan_mode"] else
            "[dim]off[/dim]"
        )
        t.add_row(
            m["id"],
            m["name"],
            m["role"],
            f"[{status_color}]{m['status']}[/{status_color}]",
            plan_str,
            m["current_task"] or "—",
            f"...{m['api_key_tail']}"
        )

    console.print(t)

    # Task board
    all_tasks = orchestrator.task_list.get_all()
    if all_tasks:
        tt = Table(
            title="[bold]Task Board[/bold]",
            box=box.SIMPLE_HEAD,
            border_style=CYAN,
            show_lines=False,
            expand=False
        )
        tt.add_column("ID",     style=DIM,  width=8)
        tt.add_column("Title",  style=TEXT, width=30)
        tt.add_column("Status", width=14)
        tt.add_column("Assignee", width=14)
        tt.add_column("Deps",   style=DIM,  width=12)

        for task in all_tasks:
            sc = TASK_COLOR.get(task.status, DIM)
            tt.add_row(
                task.id,
                task.title[:28],
                f"[{sc}]{task.status.value}[/{sc}]",
                task.assigned_to or "—",
                ",".join(task.dependencies) or "—"
            )
        console.print(tt)

    # Summary line
    console.print(
        f"[{DIM}]Tasks: "
        f"[{GREEN}]{task_summary.get('completed',0)} done[/{GREEN}] · "
        f"[{CYAN}]{task_summary.get('in_progress',0)} running[/{CYAN}] · "
        f"[{DIM}]{task_summary.get('pending',0)} pending[/{DIM}]"
        f"[/{DIM}]"
    )


def render_mailbox(orchestrator: Orchestrator, console: Console):
    # Collect all mails across all agents
    all_mails = []
    for agent in orchestrator.registry.get_all():
        inbox = orchestrator.mailbox.get_inbox(agent.id)
        for m in inbox:
            all_mails.append(m)
    # Also orchestrator inbox
    o_inbox = orchestrator.mailbox.get_inbox("orchestrator")
    all_mails.extend(o_inbox)

    # Deduplicate by id
    seen = set()
    unique = []
    for m in all_mails:
        if m.id not in seen:
            seen.add(m.id)
            unique.append(m)
    unique.sort(key=lambda m: m.timestamp)

    if not unique:
        console.print(f"[{DIM}]No messages yet.[/{DIM}]")
        return

    mt = Table(
        title="[bold]Mailbox[/bold]",
        box=box.SIMPLE_HEAD,
        border_style=PURPLE,
        expand=False
    )
    mt.add_column("ID",      style=DIM,    width=8)
    mt.add_column("From",    style=TEXT,   width=14)
    mt.add_column("To",      style=PURPLE, width=16)
    mt.add_column("Subject", style=TEXT,   width=28)
    mt.add_column("Time",    style=DIM,    width=10)

    for m in unique[-30:]:
        mt.add_row(
            m.id,
            m.from_id[:12],
            ",".join(m.to_ids)[:14],
            m.subject[:26],
            m.timestamp[11:19]
        )
    console.print(mt)


# ─────────────────────────────────────────────────────────────────────────────
# PRESET TEAM CONFIGS
# ─────────────────────────────────────────────────────────────────────────────

PRESETS = {
    "fullstack": [
        MemberConfig("Architect",  "architect",  plan_mode=True),
        MemberConfig("Backend",    "backend",    plan_mode=False),
        MemberConfig("Frontend",   "frontend",   plan_mode=False),
        MemberConfig("QA",         "qa",         plan_mode=False),
    ],
    "backend": [
        MemberConfig("BackendLead","backend",    plan_mode=True),
        MemberConfig("DBExpert",   "database",   plan_mode=False),
        MemberConfig("Tester",     "qa",         plan_mode=False),
    ],
    "research": [
        MemberConfig("Researcher1","researcher", plan_mode=True, autonomy=True),
        MemberConfig("Researcher2","researcher", plan_mode=True, autonomy=True),
        MemberConfig("Synthesizer","analyst",    plan_mode=False, autonomy=True),
    ],
    "small": [
        MemberConfig("Dev",        "fullstack",  plan_mode=False),
        MemberConfig("QA",         "qa",         plan_mode=False),
    ],
}


def parse_inline_config(config_str: str) -> List[MemberConfig]:
    """
    Parse inline member config like:
    "Alice:backend, Bob:frontend:plan, Carol:qa"
    Format: name:role[:plan]
    """
    configs = []
    for part in config_str.split(","):
        part = part.strip()
        if not part:
            continue
        pieces = part.split(":")
        name = pieces[0].strip()
        role = pieces[1].strip() if len(pieces) > 1 else "generalist"
        plan = "plan" in [p.strip().lower() for p in pieces[2:]]
        configs.append(MemberConfig(name=name, role=role, plan_mode=plan))
    return configs


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND PARSER
# ─────────────────────────────────────────────────────────────────────────────

class TeamCommandParser:
    """
    Parses /team <subcommand> ...
    Returns a dict with {action, args}
    """

    @staticmethod
    def parse(text: str) -> Optional[dict]:
        text = text.strip()
        if not text.lower().startswith("/team"):
            return None

        parts = text.split(None, 2)  # /team <sub> <rest>
        if len(parts) < 2:
            return {"action": "help"}

        sub = parts[1].lower()
        rest = parts[2] if len(parts) > 2 else ""

        if sub == "spawn":
            return {"action": "spawn", "config": rest.strip()}
        elif sub == "status":
            return {"action": "status"}
        elif sub == "tasks":
            return {"action": "tasks"}
        elif sub == "mail":
            return {"action": "mail"}
        elif sub == "dismiss":
            return {"action": "dismiss", "target": rest.strip()}
        elif sub == "assign":
            # Format: assign <task_id> <AgentName>
            # Only take first two words — ignore anything after (AI often appends description)
            target_parts = rest.strip().split()
            return {
                "action": "assign",
                "task_id": target_parts[0] if len(target_parts) > 0 else "",
                "agent":   target_parts[1] if len(target_parts) > 1 else ""
            }
        elif sub == "chat":
            chat_parts = rest.strip().split(None, 1)
            return {
                "action": "chat",
                "agent":  chat_parts[0] if chat_parts else "",
                "msg":    chat_parts[1] if len(chat_parts) > 1 else ""
            }
        elif sub == "plan":
            plan_parts = rest.strip().split(None, 1)
            decision = plan_parts[0].lower() if plan_parts else ""
            agent = plan_parts[1] if len(plan_parts) > 1 else ""
            return {"action": "plan", "decision": decision, "agent": agent}
        elif sub == "help":
            return {"action": "help"}
        else:
            return {"action": "unknown", "sub": sub}


# ─────────────────────────────────────────────────────────────────────────────
# TEAMS CLI
# ─────────────────────────────────────────────────────────────────────────────

class TeamsCLI:
    """
    Main entry point for the Teams feature.
    Can be dropped into the existing SDX Agent run_interactive() loop.
    """

    HELP_TEXT = """
[bold orange1]Teams Agent Commands[/bold orange1]

  [cyan]/team spawn <preset|config>[/cyan]
      Spawn a team. Presets: fullstack, backend, research, small
      Inline: [dim]"Alice:backend, Bob:frontend:plan, Carol:qa"[/dim]

  [cyan]/team status[/cyan]        — Show team + task board
  [cyan]/team tasks[/cyan]         — Show task list only
  [cyan]/team mail[/cyan]          — Show full mailbox

  [cyan]/team chat <name> <msg>[/cyan]
      Talk directly to a specific team member

  [cyan]/team assign <task_id> <name>[/cyan]
      Manually assign a task to a member

  [cyan]/team plan approve <name>[/cyan]   — Approve a member's plan
  [cyan]/team plan reject <name>[/cyan]    — Reject with interactive feedback

  [cyan]/team dismiss <name|all>[/cyan]    — Dismiss a member or entire team

  [cyan]Any other input[/cyan] → goes to orchestrator (team lead)
"""

    def __init__(self, env_path: str = ".env", tools=None):
        self.console = Console()
        self.event_log = EventLog(self.console)
        self.orchestrator: Optional[Orchestrator] = None
        self.env_path = env_path
        self.tools = tools
        self._api_pool: Optional[APIKeyPool] = None
        self._active = False

        self.prompt_session = PromptSession(
            style=PromptStyle.from_dict({"prompt": ORANGE})
        )

    def _ensure_orchestrator(self):
        """Lazily init orchestrator with API pool"""
        if self.orchestrator is None:
            self._api_pool = APIKeyPool(self.env_path)
            self.console.print(
                f"[{CYAN}]API pool loaded: {self._api_pool.count()} key(s) available[/{CYAN}]"
            )
            self.orchestrator = Orchestrator(
                api_key_pool=self._api_pool,
                tools=self.tools,
                delegate_mode=True,
                plan_review_enabled=True,
                always_reject_first=False,
                on_output=self.event_log.add
            )

    def handle(self, text: str) -> str:
        """Handle /team command or pass to orchestrator. Returns response string."""
        parsed = TeamCommandParser.parse(text)

        # Not a /team command — pass to orchestrator if active
        if parsed is None:
            if self.orchestrator:
                response = self.orchestrator.chat(text)
                return response
            return "[dim]No active team. Use /team spawn to create one.[/dim]"

        action = parsed["action"]

        # ── help ──────────────────────────────────────────────────────────
        if action == "help":
            self.console.print(self.HELP_TEXT)
            return ""

        # ── spawn ─────────────────────────────────────────────────────────
        if action == "spawn":
            self._ensure_orchestrator()
            config_str = parsed.get("config", "").strip()

            if not config_str:
                self.console.print(f"[{YELLOW}]Usage: /team spawn <preset|inline_config>[/{YELLOW}]")
                self.console.print(f"[{DIM}]Presets: {', '.join(PRESETS.keys())}[/{DIM}]")
                return ""

            if config_str.lower() in PRESETS:
                configs = PRESETS[config_str.lower()]
            else:
                configs = parse_inline_config(config_str)

            if not configs:
                return f"[{RED}]Could not parse team config: {config_str}[/{RED}]"

            spawned = self.orchestrator.spawn_team(configs)
            self._active = True

            lines = [f"[{GREEN}]✓ Team spawned ({len(spawned)} members):[/{GREEN}]"]
            for a in spawned:
                lines.append(f"  [{CYAN}]{a.name}[/{CYAN}] [{DIM}]{a.role}[/{DIM}] key:...{a.api_key[-8:]}")
            return "\n".join(lines)

        # ── status ────────────────────────────────────────────────────────
        if action == "status":
            if not self.orchestrator:
                return "No active team."
            render_team_status(self.orchestrator, self.console)
            return ""

        # ── tasks ─────────────────────────────────────────────────────────
        if action == "tasks":
            if not self.orchestrator:
                return "No active team."
            tasks = self.orchestrator.task_list.get_all()
            if not tasks:
                return f"[{DIM}]No tasks yet. Describe what you need done.[/{DIM}]"
            for t in tasks:
                sc = TASK_COLOR.get(t.status, DIM)
                deps = f" (deps: {','.join(t.dependencies)})" if t.dependencies else ""
                self.console.print(
                    f"  [{DIM}][{t.id}][/{DIM}] [{sc}]{t.status.value:12}[/{sc}] "
                    f"[{TEXT}]{t.title}[/{TEXT}][{DIM}]{deps}[/{DIM}]"
                )
            return ""

        # ── mail ──────────────────────────────────────────────────────────
        if action == "mail":
            if not self.orchestrator:
                return "No active team."
            render_mailbox(self.orchestrator, self.console)
            return ""

        # ── chat ──────────────────────────────────────────────────────────
        if action == "chat":
            if not self.orchestrator:
                return "No active team."
            agent_name = parsed.get("agent", "")
            msg        = parsed.get("msg", "")
            if not agent_name or not msg:
                return "Usage: /team chat <name> <message>"
            response = self.orchestrator.chat_with_member(agent_name, msg)
            self.console.print(
                Panel(
                    response,
                    title=f"[{CYAN}]{agent_name}[/{CYAN}]",
                    border_style=CYAN,
                    padding=(0, 2)
                )
            )
            return ""

        # ── assign ────────────────────────────────────────────────────────
        if action == "assign":
            if not self.orchestrator:
                return "No active team."
            task_id   = parsed.get("task_id", "")
            agent_name = parsed.get("agent", "")
            agent = self.orchestrator.registry.find_by_name(agent_name)
            if not agent:
                return f"Member '{agent_name}' not found."
            ok = self.orchestrator.task_list.assign(task_id, agent.id)
            if ok:
                # Wake member
                with self.orchestrator._members_lock:
                    m = self.orchestrator._members.get(agent.id)
                if m:
                    m.signal_work()
                return f"[{GREEN}]✓ Task [{task_id}] assigned to {agent.name}[/{GREEN}]"
            return f"[{RED}]Could not assign task [{task_id}][/{RED}]"

        # ── plan approve/reject ───────────────────────────────────────────
        if action == "plan":
            if not self.orchestrator:
                return "No active team."
            decision   = parsed.get("decision", "")
            agent_name = parsed.get("agent", "")
            agent = self.orchestrator.registry.find_by_name(agent_name)
            if not agent:
                return f"Member '{agent_name}' not found."
            if decision == "approve":
                self.orchestrator._approve_plan(agent.id)
                return f"[{GREEN}]✓ Plan approved for {agent.name}[/{GREEN}]"
            elif decision == "reject":
                feedback = self.prompt_session.prompt(
                    "Rejection feedback: ",
                    style=PromptStyle.from_dict({"prompt": YELLOW})
                )
                self.orchestrator._reject_plan(agent.id, feedback)
                return f"[{YELLOW}]Plan rejected → feedback sent to {agent.name}[/{YELLOW}]"
            return "Usage: /team plan approve <name>  or  /team plan reject <name>"

        # ── dismiss ───────────────────────────────────────────────────────
        if action == "dismiss":
            if not self.orchestrator:
                return "No active team."
            target = parsed.get("target", "").strip()
            if target.lower() == "all":
                self.orchestrator.dismiss_all()
                self._active = False
                return f"[{GREEN}]✓ All team members dismissed[/{GREEN}]"
            else:
                agent = self.orchestrator.registry.find_by_name(target)
                if not agent:
                    return f"Member '{target}' not found."
                self.orchestrator.dismiss_member(agent.id)
                return f"[{GREEN}]✓ {agent.name} dismissed[/{GREEN}]"

        # ── unknown sub-command → treat as natural language to orchestrator ──
        if action == "unknown":
            if not self.orchestrator:
                return f"[{DIM}]No active team. Use /team spawn first.[/{DIM}]"
            # Strip the /team prefix and pass the full text as a task request
            natural = text.replace("/team", "", 1).strip()
            response = self.orchestrator.chat(natural)
            return response

        return f"[{RED}]Unknown command. Try /team help[/{RED}]"

    # ─────────────────────────────────────────────────────────────────────
    # STANDALONE RUN (for testing without SDX Agent)
    # ─────────────────────────────────────────────────────────────────────

    def run_standalone(self):
        """Run Teams CLI standalone (without SDX Agent host)"""
        self.console.print(
            Panel(
                Text.from_markup(
                    f"[bold {ORANGE}]✻ Teams Agent[/bold {ORANGE}]\n"
                    f"[{DIM}]/team help for commands · /exit to quit[/{DIM}]"
                ),
                border_style=ORANGE,
                box=box.ROUNDED,
                padding=(1, 2)
            )
        )

        while True:
            try:
                user_input = self.prompt_session.prompt(
                    [("class:prompt", "team → ")],
                    style=PromptStyle.from_dict({"prompt": ORANGE})
                ).strip()

                if not user_input:
                    continue
                if user_input.lower() in ["/exit", "/quit", "exit", "quit"]:
                    if self.orchestrator:
                        self.orchestrator.dismiss_all()
                    self.console.print(f"[{DIM}]Goodbye.[/{DIM}]")
                    break

                response = self.handle(user_input)
                if response:
                    self.console.print(
                        Panel(
                            Text.from_markup(response),
                            border_style=GREEN,
                            padding=(0, 2),
                            expand=False
                        )
                    )

            except KeyboardInterrupt:
                self.console.print(f"\n[{DIM}]Interrupted.[/{DIM}]")
                if self.orchestrator:
                    self.orchestrator.dismiss_all()
                break
            except EOFError:
                break

from google.genai import types

schema_team_agent = types.FunctionDeclaration(
    name="team_agent",
    description="""Spawn and manage a persistent multi-agent team to work on complex tasks in parallel.
    Use this when a task requires multiple specialized agents working simultaneously.
    Each team member gets their own API key and can communicate with each other via mailbox.""",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "command": types.Schema(
                type=types.Type.STRING,
                description="""The team command to execute. Examples:
                - 'spawn fullstack' — spawn preset team
                - 'spawn Alice:backend, Bob:frontend:plan, Carol:qa' — custom team
                - 'status' — show team + task board
                - 'chat Alice what is your progress?' — talk to specific member
                - 'assign task_id Alice' — assign task to member
                - 'plan approve Alice' — approve a member plan
                - 'plan reject Alice' — reject with feedback
                - 'dismiss all' — shut down entire team
                - 'dismiss Alice' — dismiss one member
                - Any natural language → goes to orchestrator as a task request""",
            ),
        },
        required=["command"],
    ),
)