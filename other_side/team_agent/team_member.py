"""
TeamMember — Persistent AI agent that:
- Executes tasks autonomously
- Communicates via mailbox
- Supports plan_mode (research only → submit plan → await approval → execute)
- Has its own Gemini client with dedicated API key
"""

import os
import json
import threading
import time
from typing import Optional, List, Dict, Any, Callable

from google import genai
from google.genai import types

from team_agent.team_engine import (
    AgentState, AgentStatus, AgentRegistry,
    TaskList, Task, TaskStatus,
    MailboxSystem, Mail, MailScope
)

# Tool schemas — same set as main.py SDXAgent.get_tools()
from func.get_files_info import schema_get_files_info
from func.get_file_content import schema_get_file_content
from func.write_file import schema_write_file
from func.run_python_file import schema_run_python_file
from func.run_shell import schema_run_shell
from func.patch_file import schema_patch_file
from func.build import schema_build_project, schema_install_dependencies
from func.task_executor import schema_execute_task
from func.plan_project import schema_plan_project


# ============================================================================
# TEAM MEMBER SYSTEM PROMPT BUILDER
# ============================================================================

def build_member_system_prompt(agent: AgentState, plan_mode: bool,
                                plan_approved: bool, delegate_mode: bool) -> str:
    mode_lines = []
    if plan_mode and not plan_approved:
        mode_lines.append("**PLAN MODE ACTIVE** — You MUST submit a plan before doing any work.")
        mode_lines.append("Rules in plan mode:")
        mode_lines.append("  • You can READ and RESEARCH only — NO file writes, NO code execution")
        mode_lines.append("  • Write a detailed plan describing exactly what you will do")
        mode_lines.append("  • End your response with: PLAN_SUBMIT: <your complete plan here>")
        mode_lines.append("  • Wait for PLAN_APPROVED before proceeding")
    elif plan_mode and plan_approved:
        mode_lines.append("**PLAN APPROVED** — You may now execute your approved plan.")

    return f"""You are {agent.name}, a {agent.role} on a software engineering team.

Your agent ID: {agent.id}
Your role: {agent.role}

{chr(10).join(mode_lines)}

BEHAVIOR RULES:
- You are persistent — you will handle multiple tasks over time
- Complete tasks thoroughly before marking them done
- After completing a task, reply with: TASK_COMPLETE: <brief result summary>
- When you need to communicate with a teammate, say: SEND_MAIL to:<agent_id> subject:<subject> body:<message>
- When you want to self-assign an available task, say: SELF_ASSIGN: <task_id>
- Be concise, precise, and professional
- Always report blockers immediately via mail to the orchestrator

COMMUNICATION FORMAT:
  TASK_COMPLETE: <result summary>
  SEND_MAIL to:<id> subject:<subject> body:<body>
  PLAN_SUBMIT: <plan text>
  SELF_ASSIGN: <task_id>
"""


# ============================================================================
# TEAM MEMBER CLASS
# ============================================================================

class TeamMember:
    """
    A persistent AI agent that runs in its own thread,
    processes tasks, sends mail, and can operate in plan mode.
    """

    def __init__(
        self,
        agent: AgentState,
        registry: AgentRegistry,
        task_list: TaskList,
        mailbox: MailboxSystem,
        tools: Optional[types.Tool] = None,
        on_output: Optional[Callable[[str, str, str], None]] = None,
        plan_mode: bool = False,
        autonomy: bool = True,
    ):
        self.agent = agent
        self.registry = registry
        self.task_list = task_list
        self.mailbox = mailbox
        self.tools = tools
        self.on_output = on_output   # callback(agent_id, event_type, message)
        self.plan_mode = plan_mode
        self.autonomy = autonomy
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._work_event = threading.Event()  # signal: new work available
        self._thread: Optional[threading.Thread] = None
        self._plan_approved_event = threading.Event()
        self._plan_rejected_feedback: Optional[str] = None

        # Build Gemini client with agent's dedicated API key
        self._client = genai.Client(api_key=agent.api_key)

        # Cache expensive objects — build once, reuse across all LLM calls
        from rich.console import Console as RichConsole
        self._console = RichConsole()
        self._tools_obj = types.Tool(function_declarations=[
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

        # Register mail listener
        self.mailbox.register_listener(agent.id, self._on_mail_received)

    # -------------------------------------------------------------------------
    # LIFECYCLE
    # -------------------------------------------------------------------------

    def start(self):
        """Start the member's worker thread"""
        self.agent.status = AgentStatus.IDLE
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._emit("lifecycle", f"[{self.agent.name}] started and ready")

    def stop(self):
        """Gracefully shut down the member"""
        self._stop_event.set()
        self._work_event.set()  # unblock if waiting
        self.agent.status = AgentStatus.SHUTDOWN
        if self._thread:
            self._thread.join(timeout=3)
        self._emit("lifecycle", f"[{self.agent.name}] shutdown complete")

    def signal_work(self):
        """Notify member that new work may be available"""
        self._work_event.set()

    def approve_plan(self):
        """Orchestrator approves this member's submitted plan"""
        self.agent.plan_approved = True
        self._plan_rejected_feedback = None
        self._plan_approved_event.set()
        self._emit("plan", f"[{self.agent.name}] plan APPROVED → starting execution")

    def reject_plan(self, feedback: str):
        """Orchestrator rejects plan with feedback"""
        self.agent.plan_approved = False
        self.agent.plan_content = None
        self._plan_rejected_feedback = feedback
        self._plan_approved_event.set()
        self._emit("plan", f"[{self.agent.name}] plan REJECTED → feedback: {feedback}")

    # -------------------------------------------------------------------------
    # MAIN LOOP
    # -------------------------------------------------------------------------

    def _run_loop(self):
        while not self._stop_event.is_set():
            # ── Plan mode: submit plan first ──────────────────────────────
            if self.plan_mode and not self.agent.plan_approved:
                self._handle_plan_phase()
                if self._stop_event.is_set():
                    break
                continue

            # ── Find / pick task ─────────────────────────────────────────
            task = self._find_task()
            if task is None:
                self.agent.status = AgentStatus.IDLE
                self._work_event.clear()
                self._work_event.wait(timeout=5)
                continue

            # ── Execute task ─────────────────────────────────────────────
            self._execute_task(task)

    # -------------------------------------------------------------------------
    # PLAN PHASE
    # -------------------------------------------------------------------------

    def _handle_plan_phase(self):
        self.agent.status = AgentStatus.PLANNING
        self._emit("plan", f"[{self.agent.name}] entering plan mode — researching...")

        prompt = (
            f"You are in PLAN MODE. Your assigned task is:\n\n"
            f"{self._get_assigned_task_description()}\n\n"
            f"Research what needs to be done (read files if needed), "
            f"then produce a detailed step-by-step plan.\n"
            f"End with: PLAN_SUBMIT: <your complete plan>"
        )

        response_text = self._call_llm(prompt, allow_tools=True)

        # Extract plan
        if "PLAN_SUBMIT:" in response_text:
            plan = response_text.split("PLAN_SUBMIT:", 1)[1].strip()
            self.agent.plan_content = plan
            self._emit("plan", f"[{self.agent.name}] submitted plan for review")

            # Notify orchestrator via mail
            self.mailbox.send(
                from_id=self.agent.id,
                to_ids=["orchestrator"],
                subject=f"Plan submission from {self.agent.name}",
                body=plan,
                scope=MailScope.DIRECT
            )

            # Wait for approval/rejection
            self._plan_approved_event.clear()
            self._plan_approved_event.wait(timeout=300)  # 5 min max

            if self._plan_rejected_feedback:
                # Revise plan
                self._emit("plan", f"[{self.agent.name}] revising plan...")
                self.agent.plan_approved = False

    def _get_assigned_task_description(self) -> str:
        tasks = self.task_list.get_by_assignee(self.agent.id)
        if tasks:
            t = tasks[0]
            return f"{t.title}\n{t.description}"
        return "Explore the project and propose what to build/fix."

    # -------------------------------------------------------------------------
    # TASK EXECUTION
    # -------------------------------------------------------------------------

    def _find_task(self) -> Optional[Task]:
        # Check if already assigned
        my_tasks = self.task_list.get_by_assignee(self.agent.id)
        if my_tasks:
            return my_tasks[0]

        # Self-assign if autonomy enabled
        if self.autonomy:
            available = self.task_list.get_available()
            if available:
                # Pick first available
                task = available[0]
                if self.task_list.assign(task.id, self.agent.id):
                    self.agent.current_task_id = task.id
                    self._emit("task", f"[{self.agent.name}] self-assigned: {task.title}")
                    # Notify team
                    active_ids = self.registry.active_ids()
                    others = [i for i in active_ids if i != self.agent.id]
                    if others:
                        self.mailbox.send(
                            from_id=self.agent.id,
                            to_ids=others + ["orchestrator"],
                            subject=f"Task assigned: {task.title}",
                            body=f"I've taken task [{task.id}]: {task.title}",
                            scope=MailScope.BROADCAST
                        )
                    return task
        return None

    def _execute_task(self, task: Task):
        self.agent.status = AgentStatus.EXECUTING
        self._emit("task", f"[{self.agent.name}] executing: {task.title}")

        # Check unread mail for context
        inbox = self.mailbox.get_inbox(self.agent.id, unread_only=True)
        mail_context = ""
        if inbox:
            mail_context = "\n\nRECENT MESSAGES TO YOU:\n"
            for m in inbox:
                mail_context += f"  FROM {m.from_id}: [{m.subject}] {m.body}\n"
                self.mailbox.mark_read(m.id)

        prompt = (
            f"TASK [{task.id}]: {task.title}\n"
            f"Description: {task.description}\n"
            f"{mail_context}\n"
            f"Complete this task now. When done, reply with:\n"
            f"TASK_COMPLETE: <result summary>"
        )

        response_text = self._call_llm(prompt, allow_tools=True)

        # Parse response
        self._parse_and_act(response_text, task)

    def _parse_and_act(self, response_text: str, task: Optional[Task]):
        """Parse TASK_COMPLETE, SEND_MAIL, SELF_ASSIGN markers from response"""

        # TASK_COMPLETE
        if "TASK_COMPLETE:" in response_text and task:
            result = response_text.split("TASK_COMPLETE:", 1)[1].strip().split("\n")[0]
            self.task_list.complete(task.id, result)
            self.agent.current_task_id = None
            self.agent.status = AgentStatus.IDLE
            self._emit("task", f"[{self.agent.name}] completed: {task.title} → {result}")

            # Notify team about completion
            active_ids = self.registry.active_ids()
            others = [i for i in active_ids if i != self.agent.id]
            if others:
                self.mailbox.send(
                    from_id=self.agent.id,
                    to_ids=others + ["orchestrator"],
                    subject=f"Task done: {task.title}",
                    body=f"Completed [{task.id}]: {task.title}\nResult: {result}",
                    scope=MailScope.BROADCAST
                )

        # SEND_MAIL (can appear multiple times)
        lines = response_text.split("\n")
        for line in lines:
            if line.strip().startswith("SEND_MAIL"):
                self._parse_send_mail(line.strip())

        # PLAN_SUBMIT (during plan mode)
        if "PLAN_SUBMIT:" in response_text and self.plan_mode and not self.agent.plan_approved:
            plan = response_text.split("PLAN_SUBMIT:", 1)[1].strip()
            self.agent.plan_content = plan
            self.mailbox.send(
                from_id=self.agent.id,
                to_ids=["orchestrator"],
                subject=f"Plan from {self.agent.name}",
                body=plan,
                scope=MailScope.DIRECT
            )

    def _parse_send_mail(self, line: str):
        """Parse: SEND_MAIL to:<id> subject:<subject> body:<body>"""
        try:
            to_part = ""
            subject_part = ""
            body_part = ""

            if "to:" in line:
                to_part = line.split("to:", 1)[1].split(" ", 1)[0].strip()
            if "subject:" in line:
                subject_part = line.split("subject:", 1)[1].split("body:", 1)[0].strip()
            if "body:" in line:
                body_part = line.split("body:", 1)[1].strip()

            if not to_part:
                return

            to_ids = [to_part] if to_part != "all" else self.registry.active_ids()
            scope = MailScope.BROADCAST if to_part == "all" else MailScope.DIRECT

            self.mailbox.send(
                from_id=self.agent.id,
                to_ids=to_ids,
                subject=subject_part or "Message",
                body=body_part or "",
                scope=scope
            )
            self._emit("mail", f"[{self.agent.name}] → {to_part}: {subject_part}")

        except Exception:
            pass

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # LLM CALL  (agentic loop — actually executes tool calls)
    # -------------------------------------------------------------------------

    def _extract_retry_delay(self, error_str: str) -> float:
        """Parse retryDelay seconds from 429 error message"""
        import re
        match = re.search(r"retryDelay.*?(\d+)s", error_str)
        if match:
            return float(match.group(1))
        match = re.search(r"retry in (\d+)s", error_str)
        if match:
            return float(match.group(1))
        return 60.0

    def _execute_tool_call(self, function_call) -> str:
        """
        Execute a tool call by routing through call_function — 
        exactly the same router that main.py uses.
        """
        from call_function import call_function as route

        self._emit("task", f"[{self.agent.name}] → {function_call.name}({list(dict(function_call.args).keys())})")

        try:
            result_content = route(function_call, verbose=False)
            # Extract the string result from the Content object
            if result_content and result_content.parts:
                fr = result_content.parts[0].function_response
                if fr:
                    return str(fr.response.get("result", ""))
            return ""
        except Exception as e:
            self._emit("error", f"[{self.agent.name}] tool error ({function_call.name}): {e}")
            return f"Tool error: {e}"

    def _call_llm(self, prompt: str, allow_tools: bool = True,
                  extra_context: str = "") -> str:
        """
        Agentic LLM loop:
        1. Send prompt
        2. If response has function_calls → execute them → feed results back → repeat
        3. When response is pure text → return it
        Also handles 429 with clean TUI countdown (printed once, never spammed).
        """
        from rich.console import Console as RichConsole
        from rich.panel import Panel
        from rich.text import Text
        from rich.progress import Progress, BarColumn, TextColumn

        _console = self._console   # reuse — cached in __init__
        MAX_RETRIES = 3
        MAX_TOOL_ITERS = 15  # prevent infinite tool loops

        system = build_member_system_prompt(
            self.agent,
            self.plan_mode,
            self.agent.plan_approved,
            delegate_mode=False
        )

        # Build initial messages
        messages: List[types.Content] = []
        for h in self.agent.context_history[-6:]:
            messages.append(types.Content(
                role=h["role"],
                parts=[types.Part(text=h["content"])]
            ))
        messages.append(types.Content(
            role="user",
            parts=[types.Part(text=prompt + extra_context)]
        ))

        config_args: Dict[str, Any] = {
            "system_instruction": system,
            "temperature": 0.4,
        }
        if allow_tools:
            config_args["tools"] = [self._tools_obj]   # cached — built once in __init__
        config = types.GenerateContentConfig(**config_args)

        # ── Agentic tool loop ─────────────────────────────────────────────
        for tool_iter in range(MAX_TOOL_ITERS):
            # ── API call with 429 retry ───────────────────────────────────
            response = None
            for attempt in range(MAX_RETRIES):
                try:
                    response = self._client.models.generate_content(
                        model=self.agent.model,
                        contents=messages,
                        config=config
                    )
                    break  # success

                except Exception as e:
                    err_str = str(e)
                    is_429 = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str

                    if is_429 and attempt < MAX_RETRIES - 1:
                        wait = self._extract_retry_delay(err_str)

                        body = Text()
                        body.append("  Agent   ", style="dim")
                        body.append(f"{self.agent.name}\n", style="bold cyan")
                        body.append("  Model   ", style="dim")
                        body.append(f"{self.agent.model}\n", style="cyan")
                        body.append("  Attempt ", style="dim")
                        body.append(f"{attempt + 1}/{MAX_RETRIES - 1}\n", style="yellow")
                        body.append("  Waiting ", style="dim")
                        body.append(f"{int(wait)}s ", style="bold green")
                        body.append("before retry", style="dim")
                        _console.print(Panel(body, title="[bold yellow]⏳ Rate Limited[/bold yellow]",
                                             border_style="yellow", padding=(0, 2), expand=False))

                        with Progress(
                            TextColumn("  [dim]retrying in[/dim]"),
                            BarColumn(bar_width=28, style="yellow", complete_style="green"),
                            TextColumn("[bold green]{task.fields[remaining]}s[/bold green]"),
                            console=_console, transient=True,
                        ) as progress:
                            tid = progress.add_task("", total=int(wait), remaining=int(wait))
                            for elapsed in range(int(wait)):
                                time.sleep(1)
                                progress.update(tid, advance=1, remaining=int(wait) - elapsed - 1)

                        _console.print(f"  [dim]↻ Retrying [{self.agent.name}]...[/dim]")
                        continue

                    elif is_429 and attempt >= MAX_RETRIES - 1:
                        _console.print(Panel(
                            Text.from_markup(
                                f"[bold red]✗ Rate limit — retries exhausted[/bold red]\n"
                                f"[dim]Agent [cyan]{self.agent.name}[/cyan] paused.[/dim]"
                            ), border_style="red", padding=(0, 2), expand=False))
                        self.agent.status = AgentStatus.WAITING
                        return "ERROR: rate limit exhausted"
                    else:
                        self._emit("error", f"[{self.agent.name}] LLM error: {err_str[:120]}")
                        return f"ERROR: {err_str}"

            if response is None:
                return "ERROR: no response"

            # ── Check for tool calls ──────────────────────────────────────
            has_tool_calls = bool(response.function_calls)

            if has_tool_calls:
                # Append model response to messages
                if response.candidates and response.candidates[0].content:
                    messages.append(response.candidates[0].content)

                # Execute each tool call and collect results
                tool_results = []
                for fc in response.function_calls:
                    result_str = self._execute_tool_call(fc)
                    tool_results.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fc.name,
                                response={"result": result_str}
                            )
                        )
                    )

                # Feed results back
                messages.append(types.Content(role="user", parts=tool_results))
                # Continue loop → model will process results
                continue

            else:
                # Pure text response — done
                result_text = response.text or ""

                # Store in context history
                self.agent.context_history.append({"role": "user", "content": prompt})
                self.agent.context_history.append({"role": "model", "content": result_text})
                if len(self.agent.context_history) > 20:
                    self.agent.context_history = self.agent.context_history[-20:]

                return result_text

        return "ERROR: max tool iterations reached"

    # -------------------------------------------------------------------------
    # DIRECT USER CONVERSATION
    # -------------------------------------------------------------------------

    def chat(self, user_message: str) -> str:
        """User speaks directly to this member — tools enabled so they can actually do work"""
        self._emit("user_chat", f"User → [{self.agent.name}]: {user_message}")
        response = self._call_llm(
            user_message,
            allow_tools=True,   # ← tools ON so member can write files, run shell etc.
            extra_context=""
        )
        self._emit("user_chat", f"[{self.agent.name}] → User: {response[:200]}")
        return response

    def _on_mail_received(self, mail: Mail):
        """Called when new mail arrives — wake up loop if idle"""
        if self.agent.status == AgentStatus.IDLE:
            self._work_event.set()

    def _emit(self, event_type: str, message: str):
        if self.on_output:
            try:
                self.on_output(self.agent.id, event_type, message)
            except Exception:
                pass