"""
Team Agent Engine
Core: AgentRegistry, TaskList, MailboxSystem, TeamMember, Orchestrator
Each member gets its own API key from .env rotation
"""

from func.get_files_info import schema_get_files_info
from func.get_file_content import schema_get_file_content
from func.write_file import schema_write_file
from func.run_python_file import schema_run_python_file
from func.run_shell import schema_run_shell
from func.patch_file import schema_patch_file
from func.build import schema_build_project, schema_install_dependencies
from func.task_executor import schema_execute_task
from func.plan_project import schema_plan_project


import os
import json
import uuid
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

from google import genai
from google.genai import types


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class AgentStatus(str, Enum):
    IDLE       = "idle"
    PLANNING   = "planning"
    EXECUTING  = "executing"
    WAITING    = "waiting"       # waiting for dep
    SHUTDOWN   = "shutdown"


class TaskStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    BLOCKED     = "blocked"      # dep not resolved


class MailScope(str, Enum):
    DIRECT    = "direct"
    GROUP     = "group"
    BROADCAST = "broadcast"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Mail:
    id: str
    from_id: str          # agent id or "orchestrator" or "user"
    to_ids: List[str]     # list of agent ids, or ["all"]
    subject: str
    body: str
    scope: MailScope
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    read: bool = False


@dataclass
class Task:
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None       # agent_id or None
    dependencies: List[str] = field(default_factory=list)  # task ids
    created_by: str = "orchestrator"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    result: Optional[str] = None


@dataclass  
class AgentState:
    id: str
    name: str
    role: str
    model: str
    status: AgentStatus = AgentStatus.IDLE
    plan_mode: bool = False
    plan_approved: bool = False
    plan_content: Optional[str] = None
    api_key: Optional[str] = None
    context_history: List[Dict] = field(default_factory=list)
    mailbox: List[Mail] = field(default_factory=list)
    current_task_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# API KEY POOL
# ============================================================================

class APIKeyPool:
    """Loads all active API keys from .env and distributes them round-robin"""

    def __init__(self, env_path: str = ".env"):
        self.keys: List[str] = []
        self._index = 0
        self._lock = threading.Lock()
        self._load(env_path)

    def _load(self, env_path: str):
        """Parse .env — collect all uncommented GEMINI_API_KEY lines"""
        path = Path(env_path)
        if not path.exists():
            # Fallback: read from environment
            key = os.environ.get("GEMINI_API_KEY1")
            if key:
                self.keys = [key]
            return

        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                if line.startswith("GEMINI_API_KEY1="):
                    key = line.split("=", 1)[1].strip()
                    if key and len(key) > 10:
                        self.keys.append(key)

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for k in self.keys:
            if k not in seen:
                seen.add(k)
                unique.append(k)
        self.keys = unique

        if not self.keys:
            key = os.environ.get("GEMINI_API_KEY")
            if key:
                self.keys = [key]

    def get(self) -> str:
        """Get next available API key (round-robin)"""
        if not self.keys:
            raise ValueError("No API keys available in .env")
        with self._lock:
            key = self.keys[self._index % len(self.keys)]
            self._index += 1
            return key

    def count(self) -> int:
        return len(self.keys)


# ============================================================================
# MAILBOX SYSTEM
# ============================================================================

class MailboxSystem:
    """Central message bus for all agents + orchestrator + user"""

    def __init__(self):
        self._messages: List[Mail] = []
        self._lock = threading.Lock()
        self._listeners: Dict[str, List[Callable]] = {}  # agent_id -> callbacks

    def send(self, from_id: str, to_ids: List[str], subject: str, body: str,
             scope: MailScope = MailScope.DIRECT) -> Mail:
        mail = Mail(
            id=str(uuid.uuid4())[:8],
            from_id=from_id,
            to_ids=to_ids,
            subject=subject,
            body=body,
            scope=scope
        )
        with self._lock:
            self._messages.append(mail)
        # Fire callbacks
        for tid in to_ids:
            if tid in self._listeners:
                for cb in self._listeners[tid]:
                    try:
                        cb(mail)
                    except Exception:
                        pass
        return mail

    def broadcast(self, from_id: str, subject: str, body: str,
                  all_ids: List[str]) -> Mail:
        return self.send(from_id, all_ids, subject, body, MailScope.BROADCAST)

    def get_inbox(self, agent_id: str, unread_only: bool = False) -> List[Mail]:
        with self._lock:
            msgs = [
                m for m in self._messages
                if (agent_id in m.to_ids or "all" in m.to_ids)
                and (not unread_only or not m.read)
            ]
        return sorted(msgs, key=lambda m: m.timestamp)

    def mark_read(self, mail_id: str):
        with self._lock:
            for m in self._messages:
                if m.id == mail_id:
                    m.read = True
                    break

    def register_listener(self, agent_id: str, callback: Callable):
        if agent_id not in self._listeners:
            self._listeners[agent_id] = []
        self._listeners[agent_id].append(callback)

    def get_thread(self, agent_a: str, agent_b: str) -> List[Mail]:
        """Get conversation between two agents"""
        with self._lock:
            return [
                m for m in self._messages
                if (m.from_id in [agent_a, agent_b])
                and (agent_a in m.to_ids or agent_b in m.to_ids)
            ]


# ============================================================================
# TASK LIST
# ============================================================================

class TaskList:
    """Manages all team tasks with dependency resolution"""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()

    def create(self, title: str, description: str,
               dependencies: List[str] = None,
               created_by: str = "orchestrator") -> Task:
        task = Task(
            id=str(uuid.uuid4())[:6],
            title=title,
            description=description,
            dependencies=dependencies or [],
            created_by=created_by
        )
        with self._lock:
            self._tasks[task.id] = task
        return task

    def assign(self, task_id: str, agent_id: str) -> bool:
        with self._lock:
            if task_id not in self._tasks:
                return False
            task = self._tasks[task_id]
            if task.status == TaskStatus.COMPLETED:
                return False
            task.assigned_to = agent_id
            task.status = TaskStatus.IN_PROGRESS
            return True

    def complete(self, task_id: str, result: str = "") -> bool:
        with self._lock:
            if task_id not in self._tasks:
                return False
            task = self._tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.result = result
            return True

    def get_available(self) -> List[Task]:
        """Tasks whose dependencies are all completed"""
        with self._lock:
            completed_ids = {
                tid for tid, t in self._tasks.items()
                if t.status == TaskStatus.COMPLETED
            }
            return [
                t for t in self._tasks.values()
                if t.status == TaskStatus.PENDING
                and all(dep in completed_ids for dep in t.dependencies)
            ]

    def get_by_assignee(self, agent_id: str) -> List[Task]:
        with self._lock:
            return [t for t in self._tasks.values()
                    if t.assigned_to == agent_id
                    and t.status != TaskStatus.COMPLETED]

    def get_all(self) -> List[Task]:
        with self._lock:
            return list(self._tasks.values())

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def summary(self) -> Dict[str, int]:
        with self._lock:
            counts: Dict[str, int] = {s.value: 0 for s in TaskStatus}
            for t in self._tasks.values():
                counts[t.status.value] += 1
            counts["total"] = len(self._tasks)
            return counts

    def to_dict_list(self) -> List[Dict]:
        with self._lock:
            return [asdict(t) for t in self._tasks.values()]


# ============================================================================
# AGENT REGISTRY
# ============================================================================

class AgentRegistry:
    """Tracks all spawned team members"""

    def __init__(self):
        self._agents: Dict[str, AgentState] = {}
        self._lock = threading.Lock()

    def register(self, agent: AgentState):
        with self._lock:
            self._agents[agent.id] = agent

    def get(self, agent_id: str) -> Optional[AgentState]:
        return self._agents.get(agent_id)

    def get_active(self) -> List[AgentState]:
        with self._lock:
            return [a for a in self._agents.values()
                    if a.status != AgentStatus.SHUTDOWN]

    def get_idle(self) -> List[AgentState]:
        with self._lock:
            return [a for a in self._agents.values()
                    if a.status == AgentStatus.IDLE]

    def shutdown(self, agent_id: str):
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].status = AgentStatus.SHUTDOWN

    def shutdown_all(self):
        with self._lock:
            for a in self._agents.values():
                a.status = AgentStatus.SHUTDOWN

    def get_all(self) -> List[AgentState]:
        with self._lock:
            return list(self._agents.values())

    def find_by_name(self, name: str) -> Optional[AgentState]:
        name_lower = name.lower()
        with self._lock:
            for a in self._agents.values():
                if a.name.lower() == name_lower or a.id == name:
                    return a
        return None

    def all_ids(self) -> List[str]:
        with self._lock:
            return list(self._agents.keys())

    def active_ids(self) -> List[str]:
        return [a.id for a in self.get_active()]