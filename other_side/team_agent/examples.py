"""
Complete Team Agent Example
Demonstrates full workflow: team creation, task assignment, autonomous execution
"""

import os
import time
import json
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from team_agent import (
    TeamLeadOrchestrator,
    TaskStatus,
    AgentStatus,
    MessageType
)

console = Console()


def example_scenario_1_simple():
    """
    Scenario 1: Simple Task Execution
    Single task, single agent, basic workflow
    """
    console.print("\n[bold cyan]═══ Scenario 1: Simple Task Execution ═══[/bold cyan]\n")
    
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        console.print("[red]Error: GEMINI_API_KEY not found[/red]")
        return
    
    # 1. Initialize Team Lead
    console.print("[yellow]Step 1: Initializing Team Lead...[/yellow]")
    team_lead = TeamLeadOrchestrator(
        api_key=api_key,
        delegation_mode=True,
        planning_mode=False
    )
    
    # 2. Spawn single agent
    console.print("\n[yellow]Step 2: Spawning agent...[/yellow]")
    team_config = [
        {
            "role": "Python Developer",
            "specialization": ["python", "scripting"],
            "model": "gemini-2.0-flash-exp"
        }
    ]
    agent_ids = team_lead.spawn_team(team_config)
    
    # 3. Create simple task
    console.print("\n[yellow]Step 3: Creating task...[/yellow]")
    task_id = team_lead.create_task(
        title="Create Hello World script",
        description="Write a simple Python script that prints Hello World",
        required_skills=["python"],
        priority=5
    )
    
    # 4. Manual assignment
    console.print("\n[yellow]Step 4: Assigning task to agent...[/yellow]")
    success = team_lead.assign_task_to_agent(task_id, agent_ids[0])
    
    if success:
        console.print("[green]✓ Task assigned successfully[/green]")
    
    # 5. Show status
    console.print("\n[yellow]Step 5: Team status...[/yellow]")
    status = team_lead.get_team_status()
    console.print(Panel(
        json.dumps(status, indent=2),
        title="Status",
        border_style="cyan"
    ))
    
    # 6. Cleanup
    console.print("\n[yellow]Step 6: Shutting down team...[/yellow]")
    team_lead.shutdown_team()
    
    console.print("\n[bold green]✓ Scenario 1 Complete![/bold green]\n")


def example_scenario_2_dependencies():
    """
    Scenario 2: Task Dependencies
    Multiple tasks with dependencies, autonomous selection
    """
    console.print("\n[bold cyan]═══ Scenario 2: Task Dependencies ═══[/bold cyan]\n")
    
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        console.print("[red]Error: GEMINI_API_KEY not found[/red]")
        return
    
    # Initialize
    team_lead = TeamLeadOrchestrator(
        api_key=api_key,
        delegation_mode=True,
        planning_mode=False
    )
    
    # Spawn specialized team
    console.print("[yellow]Spawning specialized team...[/yellow]")
    team_config = [
        {"role": "Backend Developer", "specialization": ["python", "api", "fastapi"]},
        {"role": "Frontend Developer", "specialization": ["javascript", "react", "ui"]},
        {"role": "QA Engineer", "specialization": ["testing", "pytest", "automation"]},
    ]
    agent_ids = team_lead.spawn_team(team_config)
    
    # Create interdependent tasks
    console.print("\n[yellow]Creating task dependency chain...[/yellow]")
    
    task1 = team_lead.create_task(
        title="Build User API",
        description="Create FastAPI endpoint for user management (GET, POST, PUT, DELETE)",
        required_skills=["python", "api"],
        priority=10
    )
    
    task2 = team_lead.create_task(
        title="Build User UI Component",
        description="Create React component to display and manage users",
        dependencies=[task1],  # Depends on API
        required_skills=["javascript", "react"],
        priority=8
    )
    
    task3 = team_lead.create_task(
        title="Write Integration Tests",
        description="Create end-to-end tests for user management flow",
        dependencies=[task1, task2],  # Depends on both
        required_skills=["testing"],
        priority=7
    )
    
    # Display task tree
    console.print("\n[cyan]Task Dependency Tree:[/cyan]")
    console.print("┌─ Build User API [READY] (no dependencies)")
    console.print("├─ Build User UI Component [BLOCKED] (depends on: Build User API)")
    console.print("└─ Write Integration Tests [BLOCKED] (depends on: API + UI)")
    
    # Show available tasks
    console.print("\n[yellow]Checking available tasks...[/yellow]")
    available = team_lead.task_queue.get_available_tasks()
    console.print(f"[green]Available tasks: {len(available)}[/green]")
    for task in available:
        console.print(f"  • {task.title}")
    
    # Simulate autonomous assignment
    console.print("\n[yellow]Simulating autonomous task selection...[/yellow]")
    
    from team_agent import AutonomyEngine
    
    # Backend dev selects task
    backend_agent = team_lead.agent_sessions.get_agent(agent_ids[0])
    best_task = AutonomyEngine.select_best_task(backend_agent, available)
    
    if best_task:
        console.print(f"[cyan]{backend_agent.role} selected: {best_task.title}[/cyan]")
        score = AutonomyEngine.evaluate_task_fit(backend_agent, best_task)
        console.print(f"  Fit score: {score}")
        
        # Assign and complete (simulated)
        team_lead.assign_task_to_agent(best_task.task_id, agent_ids[0])
        team_lead.task_queue.complete_task(best_task.task_id, "API completed successfully")
        console.print(f"[green]✓ Task completed: {best_task.title}[/green]")
    
    # Now check what's available
    console.print("\n[yellow]After completing API task...[/yellow]")
    available = team_lead.task_queue.get_available_tasks()
    console.print(f"[green]Available tasks: {len(available)}[/green]")
    for task in available:
        console.print(f"  • {task.title} (dependencies met)")
    
    # Show final status
    console.print("\n[cyan]Final Status:[/cyan]")
    status = team_lead.get_team_status()
    console.print(f"  Total tasks: {status['total_tasks']}")
    console.print(f"  Task breakdown: {status['task_summary']}")
    
    # Cleanup
    team_lead.shutdown_team()
    console.print("\n[bold green]✓ Scenario 2 Complete![/bold green]\n")


def example_scenario_3_communication():
    """
    Scenario 3: Inter-Agent Communication
    Demonstrates messaging between agents
    """
    console.print("\n[bold cyan]═══ Scenario 3: Inter-Agent Communication ═══[/bold cyan]\n")
    
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        console.print("[red]Error: GEMINI_API_KEY not found[/red]")
        return
    
    # Initialize
    team_lead = TeamLeadOrchestrator(
        api_key=api_key,
        delegation_mode=True,
        planning_mode=False
    )
    
    # Spawn team
    team_config = [
        {"role": "Backend Developer", "specialization": ["python", "api"]},
        {"role": "Frontend Developer", "specialization": ["javascript"]},
        {"role": "DevOps Engineer", "specialization": ["docker", "deployment"]},
    ]
    agent_ids = team_lead.spawn_team(team_config)
    
    # Simulate message exchanges
    console.print("\n[yellow]Simulating agent communication...[/yellow]\n")
    
    from team_agent import Message
    import uuid
    
    # 1. Backend → Frontend: Direct message
    msg1 = Message(
        message_id=uuid.uuid4().hex,
        from_agent=agent_ids[0],
        to_agents=[agent_ids[1]],
        message_type=MessageType.INFO,
        subject="API Specification Ready",
        content="""
The User API is ready:
- Endpoint: /api/users
- Methods: GET, POST, PUT, DELETE
- Authentication: JWT required
- Rate limit: 100 req/min
        """.strip(),
        context={"api_version": "1.0"}
    )
    team_lead.message_bus.send(msg1)
    console.print(f"[cyan]📧 {agent_ids[0]} → {agent_ids[1]}[/cyan]")
    console.print(f"   Subject: {msg1.subject}")
    
    # 2. Frontend → Backend: Request
    msg2 = Message(
        message_id=uuid.uuid4().hex,
        from_agent=agent_ids[1],
        to_agents=[agent_ids[0]],
        message_type=MessageType.REQUEST,
        subject="Need API Example",
        content="Can you provide a sample API request/response for user creation?",
        context={"request_type": "documentation"}
    )
    team_lead.message_bus.send(msg2)
    console.print(f"\n[cyan]📧 {agent_ids[1]} → {agent_ids[0]}[/cyan]")
    console.print(f"   Subject: {msg2.subject}")
    
    # 3. Backend → Team: Broadcast
    msg3 = Message(
        message_id=uuid.uuid4().hex,
        from_agent=agent_ids[0],
        to_agents=["broadcast"],
        message_type=MessageType.ALERT,
        subject="Database Migration Required",
        content="Breaking change: User table schema updated. Run migrations before deploying!",
        context={"severity": "high"}
    )
    team_lead.message_bus.send(msg3)
    console.print(f"\n[yellow]📢 {agent_ids[0]} → ALL AGENTS[/yellow]")
    console.print(f"   Subject: {msg3.subject}")
    
    # 4. DevOps → Team Lead: Escalation
    msg4 = Message(
        message_id=uuid.uuid4().hex,
        from_agent=agent_ids[2],
        to_agents=["team_lead"],
        message_type=MessageType.REQUEST,
        subject="Deployment Approval Needed",
        content="All tests passing. Ready to deploy to production. Requesting approval.",
        context={"environment": "production"}
    )
    team_lead.message_bus.send(msg4)
    console.print(f"\n[purple]📧 {agent_ids[2]} → Team Lead[/purple]")
    console.print(f"   Subject: {msg4.subject}")
    
    # Show message counts
    console.print("\n[yellow]Message Summary:[/yellow]")
    for agent_id in agent_ids + ["team_lead"]:
        unread = team_lead.message_bus.get_unread_count(agent_id)
        console.print(f"  {agent_id}: {unread} unread messages")
    
    # Retrieve messages for one agent
    console.print(f"\n[cyan]Messages for {agent_ids[1]}:[/cyan]")
    messages = team_lead.message_bus.receive(agent_ids[1], mark_read=False)
    for msg in messages:
        console.print(f"  • From {msg.from_agent}: {msg.subject}")
    
    # Cleanup
    team_lead.shutdown_team()
    console.print("\n[bold green]✓ Scenario 3 Complete![/bold green]\n")


def example_scenario_4_planning_mode():
    """
    Scenario 4: Planning Mode Workflow
    Agent submits plan, gets feedback, revises
    """
    console.print("\n[bold cyan]═══ Scenario 4: Planning Mode ═══[/bold cyan]\n")
    
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        console.print("[red]Error: GEMINI_API_KEY not found[/red]")
        return
    
    # Initialize with planning mode
    console.print("[yellow]Initializing with Planning Mode enabled...[/yellow]")
    team_lead = TeamLeadOrchestrator(
        api_key=api_key,
        delegation_mode=True,
        planning_mode=True,
        always_reject_first_plan=True  # Force revision
    )
    
    # Spawn agent
    team_config = [
        {"role": "Backend Developer", "specialization": ["python", "api"]}
    ]
    agent_ids = team_lead.spawn_team(team_config)
    
    # Create task
    task_id = team_lead.create_task(
        title="Refactor Authentication Module",
        description="Refactor auth module to use JWT tokens instead of session cookies",
        required_skills=["python", "api"],
        priority=9
    )
    
    # Simulate plan submission
    console.print("\n[yellow]Agent creating execution plan...[/yellow]")
    
    from team_agent import Plan
    import uuid
    
    plan = Plan(
        plan_id=uuid.uuid4().hex,
        agent_id=agent_ids[0],
        task_id=task_id,
        research_findings="""
Current Implementation:
- Uses Flask sessions stored in cookies
- Session timeout: 24 hours
- No token refresh mechanism
        """.strip(),
        proposed_steps=[
            "1. Install PyJWT library",
            "2. Create JWT token generation function",
            "3. Create JWT validation middleware",
            "4. Update login endpoint to return JWT",
            "5. Update protected routes to validate JWT",
            "6. Remove session cookie code",
            "7. Add token refresh endpoint"
        ],
        files_to_modify=[
            "src/auth/login.py",
            "src/auth/middleware.py",
            "src/api/routes.py",
            "requirements.txt"
        ],
        risks=[
            "Breaking change for existing clients",
            "Need to handle token expiration gracefully",
            "Security: Token storage on client side"
        ],
        success_criteria=[
            "All tests pass",
            "Login returns JWT token",
            "Protected routes validate tokens",
            "Token refresh works"
        ],
        version=1
    )
    
    plan_id = team_lead.planning_manager.create_plan(plan)
    console.print(f"[cyan]📝 Plan submitted: {plan_id}[/cyan]")
    console.print(f"   Version: {plan.version}")
    console.print(f"   Steps: {len(plan.proposed_steps)}")
    console.print(f"   Files: {len(plan.files_to_modify)}")
    
    # Team Lead reviews (auto-rejects first version)
    console.print("\n[yellow]Team Lead reviewing plan...[/yellow]")
    review_result = team_lead.review_plan(plan_id)
    
    if not review_result["approved"]:
        console.print("[red]✗ Plan rejected[/red]")
        console.print(f"[dim]Feedback:\n{review_result.get('feedback')}[/dim]")
        
        # Agent revises
        console.print("\n[yellow]Agent revising plan...[/yellow]")
        plan.version = 2
        plan.proposed_steps.insert(0, "0. Review existing test coverage")
        plan.proposed_steps.append("8. Update API documentation")
        plan.success_criteria.append("Migration guide created")
        
        # Resubmit
        plan.plan_id = uuid.uuid4().hex
        plan_id = team_lead.planning_manager.create_plan(plan)
        console.print(f"[cyan]📝 Plan resubmitted: {plan_id}[/cyan]")
        console.print(f"   Version: {plan.version}")
        
        # Review again
        review_result = team_lead.review_plan(plan_id)
        
        if review_result["approved"]:
            console.print("[green]✓ Plan approved![/green]")
        else:
            console.print("[red]Plan still needs work[/red]")
    
    # Show pending plans
    pending = team_lead.planning_manager.get_pending_plans()
    console.print(f"\n[cyan]Pending plans: {len(pending)}[/cyan]")
    
    # Cleanup
    team_lead.shutdown_team()
    console.print("\n[bold green]✓ Scenario 4 Complete![/bold green]\n")


def run_all_scenarios():
    """Run all example scenarios"""
    console.print("\n[bold magenta]" + "="*60 + "[/bold magenta]")
    console.print("[bold magenta]        Team Agent System - Complete Examples[/bold magenta]")
    console.print("[bold magenta]" + "="*60 + "[/bold magenta]\n")
    
    scenarios = [
        ("Simple Task Execution", example_scenario_1_simple),
        ("Task Dependencies", example_scenario_2_dependencies),
        ("Inter-Agent Communication", example_scenario_3_communication),
        ("Planning Mode Workflow", example_scenario_4_planning_mode),
    ]
    
    for i, (name, func) in enumerate(scenarios, 1):
        console.print(f"\n[bold yellow]Running Scenario {i}/{len(scenarios)}: {name}[/bold yellow]")
        console.print("[dim]" + "-"*60 + "[/dim]")
        
        try:
            func()
            time.sleep(1)  # Pause between scenarios
        except Exception as e:
            console.print(f"\n[red]Error in scenario: {e}[/red]")
            import traceback
            traceback.print_exc()
    
    console.print("\n[bold magenta]" + "="*60 + "[/bold magenta]")
    console.print("[bold magenta]        All Scenarios Complete![/bold magenta]")
    console.print("[bold magenta]" + "="*60 + "[/bold magenta]\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
        
        scenarios = {
            "1": example_scenario_1_simple,
            "2": example_scenario_2_dependencies,
            "3": example_scenario_3_communication,
            "4": example_scenario_4_planning_mode,
            "all": run_all_scenarios
        }
        
        if scenario in scenarios:
            scenarios[scenario]()
        else:
            console.print(f"[red]Unknown scenario: {scenario}[/red]")
            console.print("[yellow]Available scenarios:[/yellow]")
            console.print("  1 - Simple Task Execution")
            console.print("  2 - Task Dependencies")
            console.print("  3 - Inter-Agent Communication")
            console.print("  4 - Planning Mode Workflow")
            console.print("  all - Run all scenarios")
    else:
        run_all_scenarios()