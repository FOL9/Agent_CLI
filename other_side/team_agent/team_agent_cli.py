"""
Team Agent CLI - Interactive multi-agent orchestration interface
Integrates with SDX Agent for team-based collaborative coding
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

from team_agent import (
    TeamLeadOrchestrator,
    AgentStatus,
    TaskStatus,
    MessageType,
    Message,
    Plan
)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.text import Text
from rich import box
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich.live import Live

# Import from your existing SDX agent
try:
    from call_function import call_function
    from func.get_files_info import schema_get_files_info
    from func.get_file_content import schema_get_file_content
    from func.write_file import schema_write_file
    from func.run_python_file import schema_run_python_file
    from func.run_shell import schema_run_shell
except ImportError:
    print("Warning: SDX Agent functions not found. Running in standalone mode.")

console = Console()


class Theme:
    """Color theme matching SDX Agent"""
    ORANGE = "#FF8C42"
    DIM = "#6B7280"
    TEXT = "#F9FAFB"
    GREEN = "#10B981"
    RED = "#EF4444"
    YELLOW = "#F59E0B"
    CYAN = "#06B6D4"
    PURPLE = "#A78BFA"
    BLUE = "#3B82F6"


class TeamAgentCLI:
    """Interactive CLI for Team Agent system"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.team_lead: Optional[TeamLeadOrchestrator] = None
        self.active_agent_view: Optional[str] = None  # For Shift+Arrow navigation
        
    def show_welcome(self):
        """Display welcome screen"""
        console.clear()
        
        welcome_text = Text()
        welcome_text.append("🤖 ", style=f"bold {Theme.ORANGE}")
        welcome_text.append("Team Agent System\n", style=f"bold {Theme.TEXT}")
        welcome_text.append("\nMulti-agent collaborative orchestration\n", style=f"italic {Theme.DIM}")
        welcome_text.append("Persistent agents • Peer communication • Autonomous task selection\n", style=f"italic {Theme.DIM}")
        
        panel = Panel(
            welcome_text,
            border_style=Theme.ORANGE,
            box=box.DOUBLE,
            padding=(1, 2)
        )
        console.print(panel)
        console.print()
    
    def create_team_wizard(self) -> List[Dict]:
        """Interactive team creation wizard"""
        console.print(f"[bold {Theme.CYAN}]Team Creation Wizard[/bold {Theme.CYAN}]")
        console.print()
        
        num_agents = Prompt.ask(
            "How many agents do you want in the team?",
            default="4",
            show_default=True
        )
        
        try:
            num_agents = int(num_agents)
        except ValueError:
            num_agents = 4
        
        team_config = []
        
        # Predefined roles for quick setup
        default_roles = [
            {"role": "Backend Developer", "specialization": ["python", "api", "database"]},
            {"role": "Frontend Developer", "specialization": ["javascript", "react", "ui"]},
            {"role": "QA Engineer", "specialization": ["testing", "quality", "automation"]},
            {"role": "DevOps Engineer", "specialization": ["docker", "ci/cd", "deployment"]},
            {"role": "Security Analyst", "specialization": ["security", "penetration-testing", "audit"]},
            {"role": "Documentation Writer", "specialization": ["documentation", "technical-writing"]},
        ]
        
        for i in range(min(num_agents, len(default_roles))):
            team_config.append(default_roles[i])
        
        # If more agents requested, add generic agents
        for i in range(len(default_roles), num_agents):
            team_config.append({
                "role": f"Agent {i+1}",
                "specialization": ["general"]
            })
        
        # Show team composition
        console.print(f"\n[{Theme.GREEN}]Team Composition:[/{Theme.GREEN}]")
        for i, agent in enumerate(team_config, 1):
            console.print(f"  {i}. {agent['role']} - {', '.join(agent['specialization'])}")
        
        console.print()
        
        return team_config
    
    def create_task_wizard(self) -> Dict:
        """Interactive task creation wizard"""
        console.print(f"\n[bold {Theme.CYAN}]Create New Task[/bold {Theme.CYAN}]")
        
        title = Prompt.ask("Task title")
        description = Prompt.ask("Task description")
        
        priority = Prompt.ask("Priority (1-10)", default="5")
        try:
            priority = int(priority)
        except ValueError:
            priority = 5
        
        skills_input = Prompt.ask(
            "Required skills (comma-separated)",
            default=""
        )
        required_skills = [s.strip() for s in skills_input.split(",")] if skills_input else []
        
        return {
            "title": title,
            "description": description,
            "priority": priority,
            "required_skills": required_skills
        }
    
    def display_team_status(self):
        """Display comprehensive team status"""
        if not self.team_lead:
            console.print(f"[{Theme.RED}]No active team[/{Theme.RED}]")
            return
        
        status = self.team_lead.get_team_status()
        
        # Create status table
        table = Table(title="Team Status", box=box.ROUNDED, border_style=Theme.CYAN)
        table.add_column("Metric", style=Theme.TEXT)
        table.add_column("Value", style=Theme.GREEN)
        
        table.add_row("Active Agents", str(status['active_agents']))
        table.add_row("Idle Agents", str(status['idle_agents']))
        table.add_row("Total Tasks", str(status['total_tasks']))
        table.add_row("Pending Plans", str(status['pending_plans']))
        table.add_row("Delegation Mode", str(status['delegation_mode']))
        table.add_row("Planning Mode", str(status['planning_mode']))
        
        console.print(table)
        
        # Task summary
        if status['task_summary']:
            console.print(f"\n[{Theme.CYAN}]Task Summary:[/{Theme.CYAN}]")
            for task_status, count in status['task_summary'].items():
                console.print(f"  {task_status}: {count}")
    
    def display_task_tree(self):
        """Display tasks in dependency tree format"""
        if not self.team_lead:
            console.print(f"[{Theme.RED}]No active team[/{Theme.RED}]")
            return
        
        all_tasks = self.team_lead.task_queue.get_all_tasks()
        
        if not all_tasks:
            console.print(f"[{Theme.YELLOW}]No tasks created yet[/{Theme.YELLOW}]")
            return
        
        tree = Tree(f"[bold {Theme.CYAN}]Task Queue[/bold {Theme.CYAN}]")
        
        for task in all_tasks:
            # Status icon
            if task.status == TaskStatus.COMPLETED:
                icon = "✓"
                color = Theme.GREEN
            elif task.status == TaskStatus.IN_PROGRESS:
                icon = "⚙"
                color = Theme.YELLOW
            elif task.status == TaskStatus.FAILED:
                icon = "✗"
                color = Theme.RED
            else:
                icon = "○"
                color = Theme.TEXT
            
            # Build task label
            task_label = Text()
            task_label.append(f"{icon} ", style=color)
            task_label.append(task.title, style=f"bold {color}")
            task_label.append(f" [{task.status.value}]", style=f"italic {Theme.DIM}")
            
            if task.assigned_to:
                task_label.append(f" → {task.assigned_to}", style=Theme.CYAN)
            
            task_node = tree.add(task_label)
            
            # Add details
            task_node.add(f"ID: {task.task_id}")
            task_node.add(f"Priority: {task.priority}")
            if task.required_skills:
                task_node.add(f"Skills: {', '.join(task.required_skills)}")
            if task.dependencies:
                task_node.add(f"Dependencies: {', '.join(task.dependencies)}")
        
        console.print(tree)
    
    def display_agents(self):
        """Display all active agents"""
        if not self.team_lead:
            console.print(f"[{Theme.RED}]No active team[/{Theme.RED}]")
            return
        
        agents = self.team_lead.agent_sessions.get_active_agents()
        
        if not agents:
            console.print(f"[{Theme.YELLOW}]No active agents[/{Theme.YELLOW}]")
            return
        
        table = Table(title="Team Agents", box=box.ROUNDED, border_style=Theme.PURPLE)
        table.add_column("Agent ID", style=Theme.CYAN)
        table.add_column("Role", style=Theme.TEXT)
        table.add_column("Status", style=Theme.GREEN)
        table.add_column("Current Task", style=Theme.YELLOW)
        table.add_column("Completed", style=Theme.DIM)
        
        for agent in agents:
            status_icon = {
                AgentStatus.IDLE: "💤",
                AgentStatus.WORKING: "⚙",
                AgentStatus.PLANNING: "📝",
                AgentStatus.WAITING_APPROVAL: "⏳",
            }.get(agent.status, "•")
            
            table.add_row(
                agent.agent_id,
                agent.role,
                f"{status_icon} {agent.status.value}",
                agent.current_task or "-",
                str(len(agent.tasks_completed))
            )
        
        console.print(table)
    
    def display_messages(self, agent_id: str):
        """Display messages for specific agent"""
        if not self.team_lead:
            return
        
        messages = self.team_lead.message_bus.receive(agent_id, mark_read=False)
        
        if not messages:
            console.print(f"[{Theme.DIM}]No messages for {agent_id}[/{Theme.DIM}]")
            return
        
        console.print(f"\n[bold {Theme.CYAN}]Messages for {agent_id}[/bold {Theme.CYAN}]")
        
        for msg in messages[-10:]:  # Show last 10
            msg_text = Text()
            msg_text.append(f"From: {msg.from_agent} | ", style=Theme.DIM)
            msg_text.append(f"{msg.subject}\n", style=f"bold {Theme.TEXT}")
            msg_text.append(msg.content, style=Theme.TEXT)
            
            panel = Panel(
                msg_text,
                border_style=Theme.YELLOW if not msg.read else Theme.DIM,
                box=box.ROUNDED,
                padding=(0, 1)
            )
            console.print(panel)
    
    def main_menu(self):
        """Main interactive menu"""
        commands = {
            "1": "Initialize Team",
            "2": "Create Task",
            "3": "View Team Status",
            "4": "View Task Tree",
            "5": "View Agents",
            "6": "Assign Task (Manual)",
            "7": "View Messages",
            "8": "Shutdown Team",
            "9": "Help",
            "0": "Exit"
        }
        
        while True:
            console.print(f"\n[bold {Theme.ORANGE}]═══ Team Agent Menu ═══[/bold {Theme.ORANGE}]")
            
            for key, desc in commands.items():
                console.print(f"  [{Theme.CYAN}]{key}[/{Theme.CYAN}] - {desc}")
            
            choice = Prompt.ask("\nSelect option", choices=list(commands.keys()))
            
            if choice == "1":
                self.initialize_team()
            
            elif choice == "2":
                self.create_task()
            
            elif choice == "3":
                self.display_team_status()
            
            elif choice == "4":
                self.display_task_tree()
            
            elif choice == "5":
                self.display_agents()
            
            elif choice == "6":
                self.manual_assign_task()
            
            elif choice == "7":
                self.view_messages()
            
            elif choice == "8":
                if self.team_lead:
                    confirm = Confirm.ask("Are you sure you want to shutdown the team?")
                    if confirm:
                        self.team_lead.shutdown_team()
                        self.team_lead = None
                        console.print(f"[{Theme.GREEN}]Team shutdown complete[/{Theme.GREEN}]")
            
            elif choice == "9":
                self.show_help()
            
            elif choice == "0":
                console.print(f"[{Theme.CYAN}]Goodbye! 👋[/{Theme.CYAN}]")
                break
    
    def initialize_team(self):
        """Initialize team with wizard"""
        delegation_mode = Confirm.ask("Enable Delegation Mode? (Team Lead only coordinates)", default=True)
        planning_mode = Confirm.ask("Enable Planning Mode? (Agents must submit plans)", default=False)
        
        self.team_lead = TeamLeadOrchestrator(
            api_key=self.api_key,
            delegation_mode=delegation_mode,
            planning_mode=planning_mode,
            always_reject_first_plan=False
        )
        
        team_config = self.create_team_wizard()
        self.team_lead.spawn_team(team_config)
        
        console.print(f"\n[bold {Theme.GREEN}]✓ Team initialized successfully![/bold {Theme.GREEN}]")
    
    def create_task(self):
        """Create task with wizard"""
        if not self.team_lead:
            console.print(f"[{Theme.RED}]Please initialize team first[/{Theme.RED}]")
            return
        
        task_data = self.create_task_wizard()
        self.team_lead.create_task(**task_data)
        
        console.print(f"[{Theme.GREEN}]✓ Task created![/{Theme.GREEN}]")
    
    def manual_assign_task(self):
        """Manually assign task to agent"""
        if not self.team_lead:
            console.print(f"[{Theme.RED}]Please initialize team first[/{Theme.RED}]")
            return
        
        # Show available tasks
        available_tasks = self.team_lead.task_queue.get_available_tasks()
        
        if not available_tasks:
            console.print(f"[{Theme.YELLOW}]No available tasks to assign[/{Theme.YELLOW}]")
            return
        
        console.print(f"\n[{Theme.CYAN}]Available Tasks:[/{Theme.CYAN}]")
        for i, task in enumerate(available_tasks, 1):
            console.print(f"  {i}. {task.title} ({task.task_id})")
        
        task_choice = Prompt.ask("Select task number")
        try:
            task_idx = int(task_choice) - 1
            selected_task = available_tasks[task_idx]
        except (ValueError, IndexError):
            console.print(f"[{Theme.RED}]Invalid task selection[/{Theme.RED}]")
            return
        
        # Show available agents
        agents = self.team_lead.agent_sessions.get_idle_agents()
        
        if not agents:
            console.print(f"[{Theme.YELLOW}]No idle agents available[/{Theme.YELLOW}]")
            return
        
        console.print(f"\n[{Theme.CYAN}]Idle Agents:[/{Theme.CYAN}]")
        for i, agent in enumerate(agents, 1):
            console.print(f"  {i}. {agent.role} ({agent.agent_id})")
        
        agent_choice = Prompt.ask("Select agent number")
        try:
            agent_idx = int(agent_choice) - 1
            selected_agent = agents[agent_idx]
        except (ValueError, IndexError):
            console.print(f"[{Theme.RED}]Invalid agent selection[/{Theme.RED}]")
            return
        
        # Assign task
        success = self.team_lead.assign_task_to_agent(selected_task.task_id, selected_agent.agent_id)
        
        if success:
            console.print(f"[{Theme.GREEN}]✓ Task assigned successfully![/{Theme.GREEN}]")
        else:
            console.print(f"[{Theme.RED}]✗ Failed to assign task[/{Theme.RED}]")
    
    def view_messages(self):
        """View messages for specific agent"""
        if not self.team_lead:
            console.print(f"[{Theme.RED}]Please initialize team first[/{Theme.RED}]")
            return
        
        agents = self.team_lead.agent_sessions.get_active_agents()
        
        if not agents:
            console.print(f"[{Theme.YELLOW}]No active agents[/{Theme.YELLOW}]")
            return
        
        console.print(f"\n[{Theme.CYAN}]Select Agent:[/{Theme.CYAN}]")
        console.print("  0. Team Lead")
        for i, agent in enumerate(agents, 1):
            unread = self.team_lead.message_bus.get_unread_count(agent.agent_id)
            console.print(f"  {i}. {agent.role} ({agent.agent_id}) - {unread} unread")
        
        choice = Prompt.ask("Select agent number")
        try:
            if choice == "0":
                agent_id = "team_lead"
            else:
                idx = int(choice) - 1
                agent_id = agents[idx].agent_id
        except (ValueError, IndexError):
            console.print(f"[{Theme.RED}]Invalid selection[/{Theme.RED}]")
            return
        
        self.display_messages(agent_id)
    
    def show_help(self):
        """Show help information"""
        help_text = f"""
[bold {Theme.CYAN}]Team Agent System Help[/bold {Theme.CYAN}]

[bold]Workflow:[/bold]
1. Initialize Team - Create agents with roles
2. Create Tasks - Define work to be done
3. Assign Tasks - Manual or auto-assignment
4. Monitor Progress - View status and messages
5. Review Plans - If planning mode enabled
6. Shutdown Team - Clean termination

[bold]Key Features:[/bold]
• Persistent agents across multiple tasks
• Peer-to-peer agent communication
• Autonomous task selection
• Dependency management
• Planning mode with approval workflow
• Delegation mode for pure coordination

[bold]Agent Roles:[/bold]
Agents can be Backend Dev, Frontend Dev, QA Engineer,
DevOps, Security Analyst, Documentation Writer, etc.

[bold]Task Dependencies:[/bold]
Tasks can depend on other tasks. Agents won't start
dependent tasks until prerequisites are completed.
        """
        
        console.print(Panel(
            help_text,
            border_style=Theme.CYAN,
            box=box.ROUNDED,
            padding=(1, 2)
        ))
    
    def run(self):
        """Main entry point"""
        self.show_welcome()
        
        try:
            self.main_menu()
        except KeyboardInterrupt:
            console.print(f"\n[{Theme.YELLOW}]Interrupted. Goodbye! 👋[/{Theme.YELLOW}]")
        except Exception as e:
            console.print(f"\n[{Theme.RED}]Error: {str(e)}[/{Theme.RED}]")
            raise


def main():
    """Entry point"""
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print(f"[{Theme.RED}]Error: GEMINI_API_KEY not found in environment[/{Theme.RED}]")
        console.print("Please create a .env file with: GEMINI_API_KEY=your_api_key")
        sys.exit(1)
    
    cli = TeamAgentCLI(api_key)
    cli.run()


if __name__ == "__main__":
    main()