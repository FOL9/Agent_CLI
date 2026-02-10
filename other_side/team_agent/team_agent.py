"""
Team Agent System - Multi-agent orchestration with persistent agents
Based on Agent Teams architecture for collaborative AI task execution
"""

import os
import sys
import json
import uuid
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from enum import Enum
from dataclasses import dataclass, field, asdict
from collections import defaultdict

from google import genai
from google.genai import types

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from rich import box
from rich.layout import Layout
from rich.live import Live

console = Console()


# ============================================================================
# DATA MODELS
# ============================================================================

class TaskStatus(Enum):
    """Task lifecycle states"""
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class AgentStatus(Enum):
    """Agent lifecycle states"""
    IDLE = "idle"
    ACTIVE = "active"
    WORKING = "working"
    PLANNING = "planning"
    WAITING_APPROVAL = "waiting_approval"
    SHUTDOWN = "shutdown"


class MessageType(Enum):
    """Message classification"""
    INFO = "info"
    REQUEST = "request"
    RESPONSE = "response"
    ALERT = "alert"
    PLAN_SUBMISSION = "plan_submission"
    PLAN_FEEDBACK = "plan_feedback"


@dataclass
class Task:
    """Task data structure with dependencies"""
    task_id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.READY
    assigned_to: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    created_by: str = "team_lead"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    priority: int = 5
    required_skills: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            'status': self.status.value,
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'Task':
        data['status'] = TaskStatus(data['status'])
        return Task(**data)


@dataclass
class Message:
    """Inter-agent message structure"""
    message_id: str
    from_agent: str
    to_agents: List[str]  # Can be specific agents or ["broadcast"]
    message_type: MessageType
    subject: str
    content: str
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    read: bool = False
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            'message_type': self.message_type.value,
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'Message':
        data['message_type'] = MessageType(data['message_type'])
        return Message(**data)


@dataclass
class Plan:
    """Agent execution plan for Planning Mode"""
    plan_id: str
    agent_id: str
    task_id: str
    research_findings: str
    proposed_steps: List[str]
    files_to_modify: List[str]
    risks: List[str]
    success_criteria: List[str]
    status: str = "pending_approval"  # pending_approval, approved, needs_revision, rejected
    version: int = 1
    feedback: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict) -> 'Plan':
        return Plan(**data)


@dataclass
class AgentContext:
    """Persistent agent session context"""
    agent_id: str
    role: str
    specialization: List[str]
    model: str
    context_history: List[Dict] = field(default_factory=list)
    tasks_completed: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            'status': self.status.value,
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'AgentContext':
        data['status'] = AgentStatus(data['status'])
        return AgentContext(**data)


# ============================================================================
# TASK QUEUE MANAGER
# ============================================================================

class TaskQueueManager:
    """Manages task queue with dependency resolution"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.lock = threading.Lock()
    
    def add_task(self, task: Task) -> str:
        """Add task to queue"""
        with self.lock:
            self.tasks[task.task_id] = task
            return task.task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, **kwargs):
        """Update task attributes"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
    
    def can_start_task(self, task_id: str) -> bool:
        """Check if task dependencies are satisfied"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        for dep_id in task.dependencies:
            dep_task = self.get_task(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    def get_available_tasks(self, agent_id: Optional[str] = None) -> List[Task]:
        """Get tasks available for assignment"""
        available = []
        
        for task in self.tasks.values():
            # Task must be ready and not assigned
            if task.status != TaskStatus.READY:
                continue
            
            if task.assigned_to is not None:
                continue
            
            # Check dependencies
            if not self.can_start_task(task.task_id):
                continue
            
            available.append(task)
        
        # Sort by priority (higher first)
        available.sort(key=lambda t: t.priority, reverse=True)
        return available
    
    def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign task to agent"""
        with self.lock:
            task = self.get_task(task_id)
            if not task or not self.can_start_task(task_id):
                return False
            
            task.assigned_to = agent_id
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now().isoformat()
            return True
    
    def complete_task(self, task_id: str, result: str) -> bool:
        """Mark task as completed"""
        with self.lock:
            task = self.get_task(task_id)
            if not task:
                return False
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.result = result
            return True
    
    def fail_task(self, task_id: str, reason: str) -> bool:
        """Mark task as failed"""
        with self.lock:
            task = self.get_task(task_id)
            if not task:
                return False
            
            task.status = TaskStatus.FAILED
            task.result = f"FAILED: {reason}"
            return True
    
    def get_status_summary(self) -> Dict[str, int]:
        """Get task status counts"""
        summary = defaultdict(int)
        for task in self.tasks.values():
            summary[task.status.value] += 1
        return dict(summary)
    
    def get_all_tasks(self) -> List[Task]:
        """Get all tasks"""
        return list(self.tasks.values())


# ============================================================================
# MESSAGE BUS
# ============================================================================

class MessageBus:
    """Inter-agent communication system"""
    
    def __init__(self):
        self.messages: Dict[str, List[Message]] = defaultdict(list)
        self.lock = threading.Lock()
    
    def send(self, message: Message):
        """Send message to specific agents or broadcast"""
        with self.lock:
            if "broadcast" in message.to_agents:
                # Broadcast to all known agents
                for agent_id in self.messages.keys():
                    if agent_id != message.from_agent:
                        self.messages[agent_id].append(message)
            else:
                # Send to specific agents
                for agent_id in message.to_agents:
                    self.messages[agent_id].append(message)
    
    def receive(self, agent_id: str, mark_read: bool = True) -> List[Message]:
        """Get messages for specific agent"""
        with self.lock:
            messages = self.messages.get(agent_id, [])
            if mark_read:
                for msg in messages:
                    msg.read = True
            return messages.copy()
    
    def get_unread_count(self, agent_id: str) -> int:
        """Get count of unread messages"""
        messages = self.messages.get(agent_id, [])
        return sum(1 for msg in messages if not msg.read)
    
    def clear_messages(self, agent_id: str):
        """Clear all messages for agent"""
        with self.lock:
            if agent_id in self.messages:
                self.messages[agent_id] = []
    
    def register_agent(self, agent_id: str):
        """Register agent in message bus"""
        if agent_id not in self.messages:
            self.messages[agent_id] = []


# ============================================================================
# PLANNING MODE MANAGER
# ============================================================================

class PlanningModeManager:
    """Manages plan creation, review, and approval workflow"""
    
    def __init__(self):
        self.plans: Dict[str, Plan] = {}
        self.lock = threading.Lock()
    
    def create_plan(self, plan: Plan) -> str:
        """Create new plan"""
        with self.lock:
            self.plans[plan.plan_id] = plan
            return plan.plan_id
    
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get plan by ID"""
        return self.plans.get(plan_id)
    
    def approve_plan(self, plan_id: str) -> bool:
        """Approve plan for execution"""
        with self.lock:
            plan = self.get_plan(plan_id)
            if not plan:
                return False
            plan.status = "approved"
            return True
    
    def reject_plan(self, plan_id: str, feedback: str) -> bool:
        """Reject plan with feedback"""
        with self.lock:
            plan = self.get_plan(plan_id)
            if not plan:
                return False
            plan.status = "needs_revision"
            plan.feedback = feedback
            plan.version += 1
            return True
    
    def get_pending_plans(self) -> List[Plan]:
        """Get plans awaiting approval"""
        return [p for p in self.plans.values() if p.status == "pending_approval"]
    
    def get_plans_by_agent(self, agent_id: str) -> List[Plan]:
        """Get all plans for specific agent"""
        return [p for p in self.plans.values() if p.agent_id == agent_id]


# ============================================================================
# PERMISSION MANAGER
# ============================================================================

class PermissionManager:
    """Manages permission inheritance from Team Lead"""
    
    def __init__(self, base_permissions: Dict[str, Any]):
        self.base_permissions = base_permissions
        self.agent_permissions: Dict[str, Dict[str, Any]] = {}
    
    def spawn_agent(self, agent_id: str) -> Dict[str, Any]:
        """New agent inherits Team Lead permissions"""
        self.agent_permissions[agent_id] = self.base_permissions.copy()
        return self.agent_permissions[agent_id]
    
    def get_permissions(self, agent_id: str) -> Dict[str, Any]:
        """Get agent's inherited permissions"""
        return self.agent_permissions.get(agent_id, self.base_permissions)
    
    def has_permission(self, agent_id: str, permission: str) -> bool:
        """Check if agent has specific permission"""
        perms = self.get_permissions(agent_id)
        return perms.get(permission, False)


# ============================================================================
# AGENT SESSION MANAGER
# ============================================================================

class AgentSessionManager:
    """Manages persistent agent sessions"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.agents: Dict[str, AgentContext] = {}
        self.lock = threading.Lock()
    
    def spawn_agent(self, role: str, specialization: List[str], model: str = "gemini-2.0-flash-exp") -> str:
        """Create new persistent agent"""
        with self.lock:
            agent_id = f"agent_{uuid.uuid4().hex[:8]}"
            
            agent = AgentContext(
                agent_id=agent_id,
                role=role,
                specialization=specialization,
                model=model,
                status=AgentStatus.IDLE
            )
            
            self.agents[agent_id] = agent
            console.print(f"[green]✓ Spawned agent:[/green] {agent_id} ({role})")
            return agent_id
    
    def get_agent(self, agent_id: str) -> Optional[AgentContext]:
        """Get agent context"""
        return self.agents.get(agent_id)
    
    def update_agent_status(self, agent_id: str, status: AgentStatus):
        """Update agent status"""
        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id].status = status
                self.agents[agent_id].last_active = datetime.now().isoformat()
    
    def add_context(self, agent_id: str, context: Dict):
        """Add context to agent history"""
        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id].context_history.append(context)
                self.agents[agent_id].last_active = datetime.now().isoformat()
    
    def complete_task_for_agent(self, agent_id: str, task_id: str):
        """Record completed task for agent"""
        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id].tasks_completed.append(task_id)
                self.agents[agent_id].current_task = None
                self.agents[agent_id].status = AgentStatus.IDLE
    
    def shutdown_agent(self, agent_id: str):
        """Shutdown and cleanup agent"""
        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id].status = AgentStatus.SHUTDOWN
                console.print(f"[yellow]⚠ Shutdown agent:[/yellow] {agent_id}")
    
    def get_active_agents(self) -> List[AgentContext]:
        """Get all active agents"""
        return [a for a in self.agents.values() if a.status != AgentStatus.SHUTDOWN]
    
    def get_idle_agents(self) -> List[AgentContext]:
        """Get idle agents available for work"""
        return [a for a in self.agents.values() if a.status == AgentStatus.IDLE]


# ============================================================================
# AUTONOMY ENGINE
# ============================================================================

class AutonomyEngine:
    """Agent autonomous decision making and task selection"""
    
    @staticmethod
    def evaluate_task_fit(agent: AgentContext, task: Task) -> float:
        """Score task based on agent specialization (0-100)"""
        score = 0.0
        
        # Base priority weight
        score += task.priority * 10
        
        # Match with specialization
        for skill in task.required_skills:
            if skill.lower() in [s.lower() for s in agent.specialization]:
                score += 50
        
        # Bonus for related previous work
        if task.task_id in agent.tasks_completed:
            score += 30
        
        # Penalty for busy agents
        if agent.status == AgentStatus.WORKING:
            score -= 40
        
        return max(0, score)
    
    @staticmethod
    def select_best_task(agent: AgentContext, available_tasks: List[Task]) -> Optional[Task]:
        """Agent selects most suitable task autonomously"""
        if not available_tasks:
            return None
        
        scored_tasks = [
            (task, AutonomyEngine.evaluate_task_fit(agent, task))
            for task in available_tasks
        ]
        
        # Sort by score descending
        scored_tasks.sort(key=lambda x: x[1], reverse=True)
        
        # Return best fit task
        return scored_tasks[0][0] if scored_tasks[0][1] > 0 else None
    
    @staticmethod
    def should_request_help(agent: AgentContext, task: Task, attempts: int) -> bool:
        """Determine if agent should request help from team"""
        # Request help after 2 failed attempts
        if attempts >= 2:
            return True
        
        # Request help if task requires skills agent doesn't have
        for skill in task.required_skills:
            if skill not in agent.specialization:
                return True
        
        return False


# ============================================================================
# TEAM LEAD ORCHESTRATOR
# ============================================================================

class TeamLeadOrchestrator:
    """Team Lead coordination and delegation logic"""
    
    def __init__(
        self,
        api_key: str,
        delegation_mode: bool = True,
        planning_mode: bool = False,
        always_reject_first_plan: bool = False
    ):
        self.api_key = api_key
        self.delegation_mode = delegation_mode
        self.planning_mode = planning_mode
        self.always_reject_first_plan = always_reject_first_plan
        
        # Core managers
        self.task_queue = TaskQueueManager()
        self.message_bus = MessageBus()
        self.planning_manager = PlanningModeManager()
        self.agent_sessions = AgentSessionManager(api_key)
        
        # Permission management (inherit from Team Lead settings)
        base_permissions = {
            "file_read": True,
            "file_write": True,
            "file_delete": False,
            "code_execution": True,
            "network_access": True,
            "dangerous_skip": False,
        }
        self.permission_manager = PermissionManager(base_permissions)
        
        # Team Lead metadata
        self.team_lead_id = "team_lead"
        self.message_bus.register_agent(self.team_lead_id)
        
        console.print(f"[bold cyan]Team Lead Orchestrator Initialized[/bold cyan]")
        console.print(f"  Delegation Mode: {delegation_mode}")
        console.print(f"  Planning Mode: {planning_mode}")
    
    def create_task(
        self,
        title: str,
        description: str,
        dependencies: List[str] = None,
        priority: int = 5,
        required_skills: List[str] = None
    ) -> str:
        """Team Lead creates new task"""
        task = Task(
            task_id=f"task_{uuid.uuid4().hex[:8]}",
            title=title,
            description=description,
            dependencies=dependencies or [],
            priority=priority,
            required_skills=required_skills or [],
            created_by=self.team_lead_id
        )
        
        task_id = self.task_queue.add_task(task)
        console.print(f"[cyan]📋 Created task:[/cyan] {title} ({task_id})")
        return task_id
    
    def spawn_team(self, team_config: List[Dict[str, Any]]) -> List[str]:
        """Spawn multiple agents as a team"""
        agent_ids = []
        
        for config in team_config:
            agent_id = self.agent_sessions.spawn_agent(
                role=config.get('role', 'Agent'),
                specialization=config.get('specialization', []),
                model=config.get('model', 'gemini-2.0-flash-exp')
            )
            
            # Inherit permissions
            self.permission_manager.spawn_agent(agent_id)
            
            # Register in message bus
            self.message_bus.register_agent(agent_id)
            
            agent_ids.append(agent_id)
        
        console.print(f"[bold green]✓ Team spawned with {len(agent_ids)} agents[/bold green]")
        return agent_ids
    
    def assign_task_to_agent(self, task_id: str, agent_id: str) -> bool:
        """Team Lead assigns task to specific agent"""
        if self.task_queue.assign_task(task_id, agent_id):
            agent = self.agent_sessions.get_agent(agent_id)
            task = self.task_queue.get_task(task_id)
            
            if agent and task:
                self.agent_sessions.update_agent_status(agent_id, AgentStatus.WORKING)
                agent.current_task = task_id
                
                # Send task assignment message
                msg = Message(
                    message_id=uuid.uuid4().hex,
                    from_agent=self.team_lead_id,
                    to_agents=[agent_id],
                    message_type=MessageType.REQUEST,
                    subject=f"Task Assignment: {task.title}",
                    content=f"You have been assigned task: {task.description}",
                    context={"task_id": task_id}
                )
                self.message_bus.send(msg)
                
                console.print(f"[green]✓ Assigned task {task_id} to {agent_id}[/green]")
                return True
        
        return False
    
    def review_plan(self, plan_id: str) -> Dict[str, Any]:
        """Team Lead reviews agent's plan"""
        plan = self.planning_manager.get_plan(plan_id)
        if not plan:
            return {"approved": False, "reason": "Plan not found"}
        
        # Auto-reject first version if configured
        if self.always_reject_first_plan and plan.version == 1:
            feedback = (
                "Initial plan needs improvement:\n"
                "1. Add more detailed step-by-step breakdown\n"
                "2. Include specific file paths and line numbers\n"
                "3. Add risk mitigation strategies"
            )
            self.planning_manager.reject_plan(plan_id, feedback)
            
            # Send feedback to agent
            msg = Message(
                message_id=uuid.uuid4().hex,
                from_agent=self.team_lead_id,
                to_agents=[plan.agent_id],
                message_type=MessageType.PLAN_FEEDBACK,
                subject="Plan Revision Required",
                content=feedback,
                context={"plan_id": plan_id}
            )
            self.message_bus.send(msg)
            
            console.print(f"[yellow]⚠ Rejected plan {plan_id} (v{plan.version}) - needs revision[/yellow]")
            return {"approved": False, "feedback": feedback}
        
        # Approve plan
        self.planning_manager.approve_plan(plan_id)
        
        # Send approval to agent
        msg = Message(
            message_id=uuid.uuid4().hex,
            from_agent=self.team_lead_id,
            to_agents=[plan.agent_id],
            message_type=MessageType.PLAN_FEEDBACK,
            subject="Plan Approved",
            content="Your plan has been approved. You may proceed with execution.",
            context={"plan_id": plan_id}
        )
        self.message_bus.send(msg)
        
        console.print(f"[green]✓ Approved plan {plan_id} (v{plan.version})[/green]")
        return {"approved": True}
    
    def shutdown_team(self):
        """Shutdown all agents"""
        active_agents = self.agent_sessions.get_active_agents()
        for agent in active_agents:
            self.agent_sessions.shutdown_agent(agent.agent_id)
        
        console.print(f"[yellow]⚠ Team shutdown: {len(active_agents)} agents terminated[/yellow]")
    
    def get_team_status(self) -> Dict[str, Any]:
        """Get comprehensive team status"""
        return {
            "active_agents": len(self.agent_sessions.get_active_agents()),
            "idle_agents": len(self.agent_sessions.get_idle_agents()),
            "task_summary": self.task_queue.get_status_summary(),
            "total_tasks": len(self.task_queue.get_all_tasks()),
            "pending_plans": len(self.planning_manager.get_pending_plans()),
            "delegation_mode": self.delegation_mode,
            "planning_mode": self.planning_mode
        }


# ============================================================================
# MAIN FUNCTION FOR TESTING
# ============================================================================

def main():
    """Example usage and testing"""
    
    # Initialize Team Lead
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]Error: GEMINI_API_KEY not found[/red]")
        return
    
    team_lead = TeamLeadOrchestrator(
        api_key=api_key,
        delegation_mode=True,
        planning_mode=True,
        always_reject_first_plan=True
    )
    
    # Define team composition
    team_config = [
        {
            "role": "Backend Developer",
            "specialization": ["python", "api", "database"],
            "model": "gemini-2.0-flash-exp"
        },
        {
            "role": "Frontend Developer",
            "specialization": ["javascript", "react", "ui"],
            "model": "gemini-2.0-flash-exp"
        },
        {
            "role": "QA Engineer",
            "specialization": ["testing", "quality", "automation"],
            "model": "gemini-2.0-flash-exp"
        }
    ]
    
    # Spawn team
    agent_ids = team_lead.spawn_team(team_config)
    
    # Create tasks
    task1 = team_lead.create_task(
        title="Build REST API",
        description="Create FastAPI backend with authentication",
        required_skills=["python", "api"],
        priority=10
    )
    
    task2 = team_lead.create_task(
        title="Build Login UI",
        description="Create React login component",
        dependencies=[task1],  # Depends on API being ready
        required_skills=["javascript", "react"],
        priority=8
    )
    
    task3 = team_lead.create_task(
        title="Write Tests",
        description="Create integration tests for login flow",
        dependencies=[task1, task2],
        required_skills=["testing"],
        priority=7
    )
    
    # Display status
    console.print("\n[bold]Team Status:[/bold]")
    status = team_lead.get_team_status()
    console.print(json.dumps(status, indent=2))
    
    # Simulate task assignment
    team_lead.assign_task_to_agent(task1, agent_ids[0])  # Backend dev
    
    # Shutdown
    console.print("\n[yellow]Shutting down team...[/yellow]")
    team_lead.shutdown_team()


if __name__ == "__main__":
    main()