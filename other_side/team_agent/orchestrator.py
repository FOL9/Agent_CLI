"""
Orchestrator — The Team Lead
- Spawns/dismisses team members
- Manages task list
- Reviews plans (approve/reject)
- In delegate mode: never executes, only coordinates
- Forwards user direct-chat to correct member
"""

import os
import json
import time
import threading
from typing import Optional, List, Dict, Any, Callable

from google import genai
from google.genai import types

from team_agent.team_engine import (
    AgentState, AgentStatus, AgentRegistry,
    TaskList, Task, TaskStatus,
    MailboxSystem, Mail, MailScope,
    APIKeyPool
)
from team_agent.team_member import TeamMember


# ============================================================================
# ORCHESTRATOR SYSTEM PROMPT
# ============================================================================

ORCHESTRATOR_SYSTEM = """You are the Team Lead Orchestrator for a software engineering team.

Your responsibilities:
1. Parse user requests and create structured task lists
2. Assign tasks to the right team members based on their roles
3. Monitor progress via the mailbox
4. Approve or reject team member plans with clear feedback
5. Coordinate inter-member communication
6. Report overall progress to the user

TASK CREATION FORMAT (when user requests work):
Respond with JSON inside a ```tasks block:
```tasks
[
  {"title": "Task title", "description": "Detailed description", "role": "backend", "dependencies": []},
  {"title": "Another task", "description": "...", "role": "frontend", "dependencies": ["task_id_of_first"]}
]
```

PLAN REVIEW FORMAT:
When reviewing a plan, respond with:
APPROVE or REJECT: <specific feedback>

Be decisive, professional, and always think about the big picture.
In DELEGATE MODE you never do implementation yourself — only coordinate.
"""


# ============================================================================
# TEAM CONFIGURATION
# ============================================================================

class MemberConfig:
    """Configuration for a team member to spawn"""
    def __init__(self, name: str, role: str, model: str = "gemini-3-flash-preview",
                 plan_mode: bool = False, autonomy: bool = True):
        self.name = name
        self.role = role
        self.model = model
        self.plan_mode = plan_mode
        self.autonomy = autonomy


# ============================================================================
# ORCHESTRATOR
# ============================================================================

class Orchestrator:
    """
    Team Lead that manages all members.
    User talks to Orchestrator by default; can also address members directly.
    """

    def __init__(
        self,
        api_key_pool: APIKeyPool,
        tools: Optional[types.Tool] = None,
        delegate_mode: bool = True,
        plan_review_enabled: bool = False,
        always_reject_first: bool = False,
        on_output: Optional[Callable[[str, str, str], None]] = None,
    ):
        self.api_key_pool = api_key_pool
        self.tools = tools
        self.delegate_mode = delegate_mode
        self.plan_review_enabled = plan_review_enabled
        self.always_reject_first = always_reject_first
        self.on_output = on_output

        # Core systems
        self.registry = AgentRegistry()
        self.task_list = TaskList()
        self.mailbox = MailboxSystem()

        # Active team members (agent_id → TeamMember)
        self._members: Dict[str, TeamMember] = {}
        self._members_lock = threading.Lock()

        # Orchestrator's own Gemini client
        self._client = genai.Client(api_key=api_key_pool.get())

        # Plan review tracking (agent_id → pending review)
        self._pending_plan_reviews: Dict[str, str] = {}

        # Register orchestrator as mailbox recipient
        self.mailbox.register_listener("orchestrator", self._on_orchestrator_mail)

        self._emit("lifecycle", "Orchestrator initialized and ready")

    # -------------------------------------------------------------------------
    # TEAM SPAWNING
    # -------------------------------------------------------------------------

    def spawn_team(self, configs: List[MemberConfig]) -> List[AgentState]:
        """Spawn a list of team members"""
        spawned = []
        for cfg in configs:
            agent = self._spawn_member(cfg)
            spawned.append(agent)
        self._emit("lifecycle", f"Team spawned: {[c.name for c in configs]}")
        return spawned

    def _spawn_member(self, cfg: MemberConfig) -> AgentState:
        """Create and start a single team member"""
        import uuid
        agent = AgentState(
            id=str(uuid.uuid4())[:6],
            name=cfg.name,
            role=cfg.role,
            model=cfg.model,
            plan_mode=cfg.plan_mode,
            api_key=self.api_key_pool.get()
        )
        self.registry.register(agent)

        member = TeamMember(
            agent=agent,
            registry=self.registry,
            task_list=self.task_list,
            mailbox=self.mailbox,
            tools=self.tools,
            on_output=self.on_output,
            plan_mode=cfg.plan_mode,
            autonomy=cfg.autonomy,
        )
        member.start()

        with self._members_lock:
            self._members[agent.id] = member

        # Broadcast welcome
        self.mailbox.broadcast(
            from_id="orchestrator",
            subject="New team member",
            body=f"Welcome {agent.name} ({agent.role}) to the team!",
            all_ids=self.registry.active_ids()
        )

        self._emit("spawn", f"Spawned [{agent.id}] {agent.name} ({agent.role}) with key ...{agent.api_key[-8:]}")
        return agent

    def dismiss_member(self, agent_id: str):
        """Shut down a specific team member"""
        with self._members_lock:
            member = self._members.get(agent_id)
        if not member:
            self._emit("error", f"Member {agent_id} not found")
            return

        # Reassign their tasks
        orphaned = self.task_list.get_by_assignee(agent_id)
        for task in orphaned:
            task.assigned_to = None
            task.status = TaskStatus.PENDING
            self._emit("task", f"Reassigned task [{task.id}] {task.title} back to pool")

        member.stop()
        self.registry.shutdown(agent_id)

        self.mailbox.broadcast(
            from_id="orchestrator",
            subject="Team update",
            body=f"{member.agent.name} has left the team.",
            all_ids=self.registry.active_ids()
        )
        self._emit("lifecycle", f"Dismissed {member.agent.name}")

    def dismiss_all(self):
        """Shut down entire team"""
        with self._members_lock:
            member_ids = list(self._members.keys())
        for mid in member_ids:
            self.dismiss_member(mid)
        self._emit("lifecycle", "All team members dismissed")

    # -------------------------------------------------------------------------
    # TASK MANAGEMENT
    # -------------------------------------------------------------------------

    def create_tasks_from_request(self, user_request: str) -> List[Task]:
        """Ask the orchestrator LLM to parse request into tasks"""
        prompt = (
            f"User request: {user_request}\n\n"
            f"Create a structured task list for the team. "
            f"Return a JSON tasks block with title, description, role, dependencies."
        )
        response = self._call_orchestrator_llm(prompt)
        tasks = self._parse_tasks_from_response(response)
        return tasks

    def _parse_tasks_from_response(self, response: str) -> List[Task]:
        """Extract ```tasks JSON from orchestrator response"""
        tasks = []
        if "```tasks" in response:
            try:
                raw = response.split("```tasks", 1)[1].split("```", 1)[0].strip()
                task_defs = json.loads(raw)
                for t in task_defs:
                    task = self.task_list.create(
                        title=t.get("title", "Untitled"),
                        description=t.get("description", ""),
                        dependencies=t.get("dependencies", []),
                        created_by="orchestrator"
                    )
                    tasks.append(task)
                    self._emit("task", f"Created task [{task.id}]: {task.title}")
            except Exception as e:
                self._emit("error", f"Failed to parse tasks: {e}")
        return tasks

    def assign_tasks_to_roles(self):
        """Match available tasks to idle members by role"""
        available = self.task_list.get_available()
        idle = self.registry.get_idle()

        for task in available:
            if task.assigned_to:
                continue
            # Try to find member whose role matches
            for member_agent in idle:
                with self._members_lock:
                    member = self._members.get(member_agent.id)
                if member and member_agent.status == AgentStatus.IDLE:
                    self.task_list.assign(task.id, member_agent.id)
                    member.signal_work()
                    self._emit("task", f"Assigned [{task.id}] to {member_agent.name}")
                    break

    def create_and_assign(self, user_request: str):
        """Full flow: parse request → create tasks → assign"""
        tasks = self.create_tasks_from_request(user_request)
        if tasks:
            self.assign_tasks_to_roles()
            # Signal all members
            with self._members_lock:
                for m in self._members.values():
                    m.signal_work()

    # -------------------------------------------------------------------------
    # PLAN REVIEW
    # -------------------------------------------------------------------------

    def _on_orchestrator_mail(self, mail: Mail):
        """Handle incoming mail to orchestrator"""
        if "Plan submission" in mail.subject or "Plan from" in mail.subject:
            self._handle_plan_submission(mail)
        else:
            self._emit("mail", f"Orchestrator received from {mail.from_id}: [{mail.subject}]")

    def _handle_plan_submission(self, mail: Mail):
        """Review a plan submitted by a team member"""
        agent_id = mail.from_id
        plan_text = mail.body

        self._emit("plan_review", f"Reviewing plan from agent {agent_id}...")

        if self.always_reject_first and agent_id not in self._pending_plan_reviews:
            # First submission — always reject
            self._pending_plan_reviews[agent_id] = plan_text
            feedback = "Good research, but the plan needs more detail. Add specific file paths, exact changes, and test strategy."
            self._reject_plan(agent_id, feedback)
            return

        # Ask orchestrator LLM to review
        if self.plan_review_enabled:
            review_prompt = (
                f"Review this plan from a team member:\n\n{plan_text}\n\n"
                f"Is this plan complete, specific, and actionable?\n"
                f"Respond with APPROVE or REJECT: <specific feedback>"
            )
            decision = self._call_orchestrator_llm(review_prompt)

            if decision.strip().upper().startswith("APPROVE"):
                self._approve_plan(agent_id)
            else:
                feedback = decision.split(":", 1)[1].strip() if ":" in decision else decision
                self._reject_plan(agent_id, feedback)
        else:
            # Auto-approve
            self._approve_plan(agent_id)

    def _approve_plan(self, agent_id: str):
        with self._members_lock:
            member = self._members.get(agent_id)
        if member:
            member.approve_plan()
            self.mailbox.send(
                from_id="orchestrator",
                to_ids=[agent_id],
                subject="Plan approved",
                body="Your plan has been approved. Proceed with implementation.",
                scope=MailScope.DIRECT
            )

    def _reject_plan(self, agent_id: str, feedback: str):
        with self._members_lock:
            member = self._members.get(agent_id)
        if member:
            member.reject_plan(feedback)
            self.mailbox.send(
                from_id="orchestrator",
                to_ids=[agent_id],
                subject="Plan rejected — revise",
                body=f"Plan rejected.\n\nFeedback:\n{feedback}\n\nPlease revise and resubmit.",
                scope=MailScope.DIRECT
            )

    # -------------------------------------------------------------------------
    # USER CONVERSATION
    # -------------------------------------------------------------------------

    def chat(self, user_message: str) -> str:
        """User talks to orchestrator"""
        if self.delegate_mode:
            # Orchestrator only coordinates — pass to team
            return self._orchestrate_response(user_message)
        else:
            return self._call_orchestrator_llm(user_message)

    def chat_with_member(self, agent_id_or_name: str, message: str) -> str:
        """User speaks directly to a specific team member"""
        # Try by ID first, then by name
        agent = self.registry.get(agent_id_or_name)
        if not agent:
            agent = self.registry.find_by_name(agent_id_or_name)

        if not agent:
            return f"Member '{agent_id_or_name}' not found. Active members: {[a.name for a in self.registry.get_active()]}"

        with self._members_lock:
            member = self._members.get(agent.id)

        if not member:
            return f"Member {agent.name} is not active."

        return member.chat(message)

    def _orchestrate_response(self, user_message: str) -> str:
        """Delegate mode: parse intent, coordinate team, report"""
        status = self.get_status_summary()
        prompt = (
            f"Team status:\n{status}\n\n"
            f"User message: {user_message}\n\n"
            f"As orchestrator in delegate mode: coordinate the team, "
            f"create tasks if needed, or report status. Do NOT do implementation yourself."
        )
        return self._call_orchestrator_llm(prompt)

    # -------------------------------------------------------------------------
    # STATUS
    # -------------------------------------------------------------------------

    def get_status_summary(self) -> str:
        """Return a readable team status"""
        lines = []
        lines.append("=== TEAM STATUS ===")
        for agent in self.registry.get_all():
            lines.append(f"  [{agent.id}] {agent.name} ({agent.role}) — {agent.status.value}")
            if agent.current_task_id:
                task = self.task_list.get(agent.current_task_id)
                if task:
                    lines.append(f"    └ Working on: {task.title}")

        task_summary = self.task_list.summary()
        lines.append("\n=== TASKS ===")
        for k, v in task_summary.items():
            lines.append(f"  {k}: {v}")

        return "\n".join(lines)

    def get_all_members_info(self) -> List[Dict]:
        """Return list of member info dicts"""
        result = []
        for agent in self.registry.get_all():
            result.append({
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "status": agent.status.value,
                "plan_mode": agent.plan_mode,
                "plan_approved": agent.plan_approved,
                "current_task": agent.current_task_id,
                "api_key_tail": agent.api_key[-8:] if agent.api_key else "N/A"
            })
        return result

    # -------------------------------------------------------------------------
    # LLM
    # -------------------------------------------------------------------------

    def _call_orchestrator_llm(self, prompt: str) -> str:
        try:
            config = types.GenerateContentConfig(
                system_instruction=ORCHESTRATOR_SYSTEM,
                temperature=0.3,
            )
            response = self._client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
                config=config
            )
            return response.text or ""
        except Exception as e:
            self._emit("error", f"Orchestrator LLM error: {e}")
            return f"[Orchestrator error: {e}]"

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _emit(self, event_type: str, message: str):
        if self.on_output:
            try:
                self.on_output("orchestrator", event_type, message)
            except Exception:
                pass