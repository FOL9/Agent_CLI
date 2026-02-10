"""
Team Agent Functions - Integration with SDX Agent
These functions are called by the main agent via the function calling interface
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from google.genai import types

from team_agent.team_agent import (
    TeamLeadOrchestrator,
    TaskStatus,
    AgentStatus,
    MessageType,
    Message
)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

# Global team orchestrator instance
_active_team: Optional[TeamLeadOrchestrator] = None
_api_key: Optional[str] = None


def set_api_key(api_key: str):
    """Set API key for team operations"""
    global _api_key
    _api_key = api_key


def get_active_team() -> Optional[TeamLeadOrchestrator]:
    """Get current active team"""
    return _active_team


# ============================================================================
# FUNCTION SCHEMAS FOR SDX AGENT
# ============================================================================

schema_create_team = types.FunctionDeclaration(
    name="create_team",
    description="""Create a team of specialized AI agents to work on complex tasks collaboratively.
    
Use this when:
- Task is large and benefits from parallel work
- Need specialized expertise (backend, frontend, QA, etc.)
- Multiple independent subtasks exist
- Want agents to collaborate and communicate

Example: "Create a team to build a full-stack authentication system"
""",
    parameters={
        "type": "object",
        "properties": {
            "team_size": {
                "type": "integer",
                "description": "Number of agents in the team (1-6 recommended)"
            },
            "roles": {
                "type": "array",
                "description": "List of agent roles and specializations",
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {
                            "type": "string",
                            "description": "Agent role (e.g., 'Backend Developer', 'QA Engineer')"
                        },
                        "specialization": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Skills/technologies (e.g., ['python', 'fastapi', 'postgresql'])"
                        }
                    }
                }
            },
            "delegation_mode": {
                "type": "boolean",
                "description": "If true, Team Lead only coordinates. If false, can execute tasks too",
                "default": True
            },
            "planning_mode": {
                "type": "boolean",
                "description": "If true, agents must submit plans for approval before executing",
                "default": False
            }
        },
        "required": ["team_size", "roles"]
    }
)

schema_assign_task_to_team = types.FunctionDeclaration(
    name="assign_task_to_team",
    description="""Assign a task to the active team. The team will handle it autonomously.
    
Tasks can have:
- Dependencies on other tasks
- Required skills
- Priority levels

The team will self-organize and execute the task collaboratively.""",
    parameters={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Short task title"
            },
            "description": {
                "type": "string",
                "description": "Detailed task description with requirements and context"
            },
            "priority": {
                "type": "integer",
                "description": "Priority 1-10 (10 = highest)",
                "default": 5
            },
            "required_skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Skills needed for this task (helps with agent matching)"
            },
            "dependencies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Task IDs that must complete before this task can start"
            }
        },
        "required": ["title", "description"]
    }
)

schema_get_team_status = types.FunctionDeclaration(
    name="get_team_status",
    description="""Get comprehensive status of the active team.
    
Returns:
- Number of active/idle agents
- Task breakdown (ready, in progress, completed, failed)
- Team configuration
- Overall progress""",
    parameters={
        "type": "object",
        "properties": {}
    }
)

schema_get_team_messages = types.FunctionDeclaration(
    name="get_team_messages",
    description="""View inter-agent communications and collaboration.
    
Shows messages between team members including:
- Status updates
- Requests for help
- Shared findings
- Alerts and notifications""",
    parameters={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": "Specific agent ID to view messages for (or 'all' for team-wide)",
                "default": "all"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of recent messages to show",
                "default": 10
            }
        }
    }
)

schema_execute_team_tasks = types.FunctionDeclaration(
    name="execute_team_tasks",
    description="""Start autonomous team execution of all assigned tasks.
    
Agents will:
- Self-select tasks based on their specialization
- Execute tasks in parallel (respecting dependencies)
- Communicate with each other as needed
- Report progress and results

This runs the team autonomously until all tasks complete or max iterations reached.""",
    parameters={
        "type": "object",
        "properties": {
            "max_iterations": {
                "type": "integer",
                "description": "Maximum task execution cycles",
                "default": 10
            },
            "verbose": {
                "type": "boolean",
                "description": "Show detailed execution logs",
                "default": False
            }
        }
    }
)

schema_shutdown_team = types.FunctionDeclaration(
    name="shutdown_team",
    description="""Shutdown the active team and release all resources.
    
Important:
- Always shutdown teams when work is complete
- Prevents resource leaks
- Saves final state
- Terminates all agents cleanly""",
    parameters={
        "type": "object",
        "properties": {}
    }
)


# ============================================================================
# FUNCTION IMPLEMENTATIONS
# ============================================================================

def create_team(
    working_directory: str,
    team_size: int,
    roles: List[Dict[str, Any]],
    delegation_mode: bool = True,
    planning_mode: bool = False
) -> str:
    """Create a team of AI agents"""
    global _active_team, _api_key
    
    if _active_team is not None:
        return "ERROR: A team is already active. Shutdown the current team first with shutdown_team()."
    
    if not _api_key:
        return "ERROR: API key not set. Cannot create team."
    
    try:
        # Initialize team orchestrator
        _active_team = TeamLeadOrchestrator(
            api_key=_api_key,
            delegation_mode=delegation_mode,
            planning_mode=planning_mode
        )
        
        # Ensure we have correct number of roles
        if len(roles) < team_size:
            # Pad with generic agents
            default_roles = [
                {"role": "Backend Developer", "specialization": ["python", "api"]},
                {"role": "Frontend Developer", "specialization": ["javascript", "react"]},
                {"role": "QA Engineer", "specialization": ["testing", "automation"]},
                {"role": "DevOps Engineer", "specialization": ["docker", "ci/cd"]},
                {"role": "Documentation Writer", "specialization": ["documentation"]},
            ]
            while len(roles) < team_size:
                roles.append(default_roles[len(roles) % len(default_roles)])
        
        # Spawn team
        agent_ids = _active_team.spawn_team(roles[:team_size])
        
        # Build response
        result = f"""✓ Team Created Successfully!

Configuration:
- Team Size: {team_size} agents
- Delegation Mode: {'ON (Team Lead coordinates only)' if delegation_mode else 'OFF'}
- Planning Mode: {'ON (Plans require approval)' if planning_mode else 'OFF'}

Team Members:
"""
        for i, (agent_id, role_config) in enumerate(zip(agent_ids, roles[:team_size]), 1):
            result += f"\n{i}. {agent_id}"
            result += f"\n   Role: {role_config.get('role', 'Agent')}"
            result += f"\n   Skills: {', '.join(role_config.get('specialization', []))}"
        
        result += f"\n\nThe team is ready to receive tasks. Use assign_task_to_team() to assign work."
        
        return result
    
    except Exception as e:
        return f"ERROR: Failed to create team: {str(e)}"


def assign_task_to_team(
    working_directory: str,
    title: str,
    description: str,
    priority: int = 5,
    required_skills: List[str] = None,
    dependencies: List[str] = None
) -> str:
    """Assign a task to the active team"""
    global _active_team
    
    if _active_team is None:
        return "ERROR: No active team. Create a team first with create_team()."
    
    try:
        task_id = _active_team.create_task(
            title=title,
            description=description,
            priority=priority,
            required_skills=required_skills or [],
            dependencies=dependencies or []
        )
        
        result = f"""✓ Task Created: {task_id}

Title: {title}
Priority: {priority}/10
Required Skills: {', '.join(required_skills or ['none specified'])}
Dependencies: {len(dependencies or [])} task(s)

Status: Task added to queue. Agents can now self-assign this task.

Next Step: Call execute_team_tasks() to start autonomous execution.
"""
        return result
    
    except Exception as e:
        return f"ERROR: Failed to create task: {str(e)}"


def get_team_status(working_directory: str) -> str:
    """Get current team status"""
    global _active_team
    
    if _active_team is None:
        return "No active team. Create a team with create_team()."
    
    try:
        status = _active_team.get_team_status()
        
        # Build formatted status report
        result = "═══ TEAM STATUS ═══\n\n"
        
        # Agent summary
        result += f"👥 AGENTS:\n"
        result += f"   Active: {status['active_agents']}\n"
        result += f"   Idle: {status['idle_agents']}\n\n"
        
        # Task summary
        result += f"📋 TASKS:\n"
        result += f"   Total: {status['total_tasks']}\n"
        if status['task_summary']:
            for task_status, count in status['task_summary'].items():
                icon = {
                    'ready': '○',
                    'in_progress': '⚙',
                    'completed': '✓',
                    'failed': '✗',
                    'blocked': '⊗'
                }.get(task_status, '•')
                result += f"   {icon} {task_status.replace('_', ' ').title()}: {count}\n"
        
        result += f"\n⚙ CONFIGURATION:\n"
        result += f"   Delegation Mode: {status['delegation_mode']}\n"
        result += f"   Planning Mode: {status['planning_mode']}\n"
        
        if status['pending_plans'] > 0:
            result += f"\n📝 PENDING PLANS: {status['pending_plans']}\n"
        
        # Get detailed agent info
        agents = _active_team.agent_sessions.get_active_agents()
        if agents:
            result += f"\n\n👤 AGENT DETAILS:\n"
            for agent in agents:
                status_icon = {
                    AgentStatus.IDLE: '💤',
                    AgentStatus.WORKING: '⚙',
                    AgentStatus.PLANNING: '📝',
                    AgentStatus.WAITING_APPROVAL: '⏳',
                }.get(agent.status, '•')
                
                result += f"\n{agent.agent_id}"
                result += f"\n  Role: {agent.role}"
                result += f"\n  Status: {status_icon} {agent.status.value}"
                result += f"\n  Tasks Completed: {len(agent.tasks_completed)}"
                if agent.current_task:
                    result += f"\n  Current Task: {agent.current_task}"
        
        # Get task details
        all_tasks = _active_team.task_queue.get_all_tasks()
        if all_tasks:
            result += f"\n\n📊 TASK DETAILS:\n"
            for task in all_tasks:
                status_icon = {
                    TaskStatus.READY: '○',
                    TaskStatus.IN_PROGRESS: '⚙',
                    TaskStatus.COMPLETED: '✓',
                    TaskStatus.FAILED: '✗',
                    TaskStatus.BLOCKED: '⊗'
                }.get(task.status, '•')
                
                result += f"\n{status_icon} {task.title} [{task.status.value}]"
                result += f"\n  ID: {task.task_id}"
                result += f"\n  Priority: {task.priority}/10"
                if task.assigned_to:
                    result += f"\n  Assigned To: {task.assigned_to}"
                if task.dependencies:
                    result += f"\n  Dependencies: {len(task.dependencies)} tasks"
        
        return result
    
    except Exception as e:
        return f"ERROR: Failed to get status: {str(e)}"


def get_team_messages(
    working_directory: str,
    agent_id: str = "all",
    limit: int = 10
) -> str:
    """Get team messages"""
    global _active_team
    
    if _active_team is None:
        return "No active team."
    
    try:
        result = "═══ TEAM MESSAGES ═══\n\n"
        
        if agent_id == "all":
            # Show messages for all agents
            agents = _active_team.agent_sessions.get_active_agents()
            agents_to_check = [a.agent_id for a in agents] + ["team_lead"]
        else:
            agents_to_check = [agent_id]
        
        total_messages = 0
        for current_agent_id in agents_to_check:
            messages = _active_team.message_bus.receive(current_agent_id, mark_read=False)
            
            if messages:
                result += f"\n📧 Messages for {current_agent_id}:\n"
                result += f"   Unread: {sum(1 for m in messages if not m.read)}\n\n"
                
                for msg in messages[-limit:]:
                    read_marker = "  " if msg.read else "🔵"
                    result += f"{read_marker} From: {msg.from_agent}\n"
                    result += f"   Subject: {msg.subject}\n"
                    result += f"   Type: {msg.message_type.value}\n"
                    result += f"   {msg.content[:200]}{'...' if len(msg.content) > 200 else ''}\n"
                    result += f"   Time: {msg.timestamp}\n\n"
                
                total_messages += len(messages)
        
        if total_messages == 0:
            result += "No messages yet.\n"
        
        return result
    
    except Exception as e:
        return f"ERROR: Failed to get messages: {str(e)}"


def execute_team_tasks(
    working_directory: str,
    max_iterations: int = 10,
    verbose: bool = False
) -> str:
    """Execute team tasks autonomously"""
    global _active_team
    
    if _active_team is None:
        return "ERROR: No active team."
    
    try:
        console.print("\n[bold cyan]🚀 Starting Autonomous Team Execution[/bold cyan]\n")
        
        # Import worker
        from agent_worker import AgentWorker
        
        # Get available tools from SDX Agent
        from func.get_files_info import schema_get_files_info
        from func.get_file_content import schema_get_file_content
        from func.write_file import schema_write_file
        from func.run_python_file import schema_run_python_file
        from func.run_shell import schema_run_shell
        
        tools = [
            schema_get_files_info,
            schema_get_file_content,
            schema_write_file,
            schema_run_python_file,
            schema_run_shell
        ]
        
        # Create workers for each agent
        agents = _active_team.agent_sessions.get_active_agents()
        
        if not agents:
            return "No active agents in team."
        
        results = []
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            console.print(f"[yellow]Iteration {iteration}/{max_iterations}[/yellow]")
            
            # Check for available tasks
            available_tasks = _active_team.task_queue.get_available_tasks()
            
            if not available_tasks:
                console.print("[green]No more available tasks. Team work complete![/green]")
                break
            
            # Each idle agent tries to self-assign and execute
            idle_agents = _active_team.agent_sessions.get_idle_agents()
            
            if not idle_agents:
                console.print("[yellow]All agents busy, waiting...[/yellow]")
                import time
                time.sleep(2)
                continue
            
            work_done = False
            
            for agent in idle_agents:
                # Create worker
                worker = AgentWorker(_active_team, agent.agent_id, tools)
                
                # Try autonomous work (1 task)
                from team_agent import AutonomyEngine
                
                available_tasks = _active_team.task_queue.get_available_tasks()
                if not available_tasks:
                    break
                
                # Select best task
                selected_task = AutonomyEngine.select_best_task(agent, available_tasks)
                
                if selected_task:
                    # Self-assign
                    if _active_team.task_queue.assign_task(selected_task.task_id, agent.agent_id):
                        agent.current_task = selected_task.task_id
                        console.print(f"[cyan]🎯 {agent.agent_id} self-assigned: {selected_task.title}[/cyan]")
                        
                        # Execute
                        success = worker.execute_task(selected_task)
                        
                        if success:
                            results.append(f"✓ {agent.role} completed: {selected_task.title}")
                            work_done = True
                        else:
                            results.append(f"✗ {agent.role} failed: {selected_task.title}")
            
            if not work_done:
                console.print("[yellow]No work done this iteration, checking dependencies...[/yellow]")
        
        # Build final report
        final_status = _active_team.get_team_status()
        
        report = f"""
═══ TEAM EXECUTION COMPLETE ═══

Iterations: {iteration}/{max_iterations}

Results:
"""
        for result in results:
            report += f"  {result}\n"
        
        report += f"""
Final Status:
  Tasks Completed: {final_status['task_summary'].get('completed', 0)}
  Tasks In Progress: {final_status['task_summary'].get('in_progress', 0)}
  Tasks Ready: {final_status['task_summary'].get('ready', 0)}
  Tasks Failed: {final_status['task_summary'].get('failed', 0)}

The team has finished autonomous execution.
Use get_team_status() for detailed status.
"""
        
        return report
    
    except Exception as e:
        import traceback
        return f"ERROR: Team execution failed: {str(e)}\n\n{traceback.format_exc()}"


def shutdown_team(working_directory: str) -> str:
    """Shutdown the active team"""
    global _active_team
    
    if _active_team is None:
        return "No active team to shutdown."
    
    try:
        # Get final stats
        final_status = _active_team.get_team_status()
        
        # Shutdown
        _active_team.shutdown_team()
        _active_team = None
        
        result = f"""✓ Team Shutdown Complete

Final Statistics:
  Agents Terminated: {final_status['active_agents']}
  Total Tasks: {final_status['total_tasks']}
  Completed: {final_status['task_summary'].get('completed', 0)}
  Failed: {final_status['task_summary'].get('failed', 0)}

All resources released. You can create a new team anytime.
"""
        return result
    
    except Exception as e:
        return f"ERROR: Shutdown failed: {str(e)}"