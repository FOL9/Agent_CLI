#!/usr/bin/env python3
"""
Quick smoke test for the Team Agent system.
Run from the same directory as team_engine.py etc.

Usage:
  cd /path/to/your/project
  python test_teams.py
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

# ─── Make sure we can import our modules ───────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from team_engine import APIKeyPool
from orchestrator import Orchestrator, MemberConfig
from rich.console import Console

console = Console()


def on_output(agent_id: str, event_type: str, message: str):
    icons = {
        "lifecycle": "◈", "task": "◆", "mail": "✉",
        "plan": "📋", "spawn": "⚡", "error": "✗", "user_chat": "💬"
    }
    icon = icons.get(event_type, "·")
    console.print(f"[dim]{agent_id:>12}[/dim] [{event_type}] {icon} {message}")


def main():
    console.rule("[bold orange1]Teams Agent — Smoke Test[/bold orange1]")

    # 1. Load API keys
    pool = APIKeyPool(".env")
    console.print(f"[cyan]API keys available: {pool.count()}[/cyan]")

    if pool.count() == 0:
        console.print("[red]No API keys found. Check your .env[/red]")
        sys.exit(1)

    # 2. Create orchestrator
    orch = Orchestrator(
        api_key_pool=pool,
        tools=None,          # No tools for smoke test
        delegate_mode=True,
        plan_review_enabled=False,  # Auto-approve plans
        always_reject_first=False,
        on_output=on_output
    )

    # 3. Spawn a small team
    console.rule("Spawning team")
    orch.spawn_team([
        MemberConfig("Alice", "backend",  plan_mode=False, autonomy=True),
        MemberConfig("Bob",   "frontend", plan_mode=False, autonomy=True),
    ])
    time.sleep(1)

    # 4. Create tasks manually
    console.rule("Creating tasks")
    t1 = orch.task_list.create(
        "Design API schema",
        "Design the REST API schema for user authentication endpoints.",
        created_by="orchestrator"
    )
    t2 = orch.task_list.create(
        "Build frontend form",
        "Build a login form that calls the authentication API.",
        dependencies=[t1.id],
        created_by="orchestrator"
    )
    console.print(f"[green]Created task [{t1.id}]: {t1.title}[/green]")
    console.print(f"[green]Created task [{t2.id}]: {t2.title} (depends on {t1.id})[/green]")

    # 5. Assign + signal
    orch.assign_tasks_to_roles()

    # 6. Let team work for a bit
    console.rule("Team working (10s)...")
    time.sleep(10)

    # 7. Status
    console.rule("Final Status")
    summary = orch.task_list.summary()
    console.print(f"Tasks: {summary}")
    for info in orch.get_all_members_info():
        console.print(f"  {info['name']} ({info['role']}) — {info['status']} | key:...{info['api_key_tail']}")

    # 8. Direct chat with Alice
    console.rule("Direct chat with Alice")
    response = orch.chat_with_member("Alice", "What did you design for the API schema?")
    console.print(f"[cyan]Alice:[/cyan] {response[:300]}")

    # 9. Dismiss
    console.rule("Dismissing team")
    orch.dismiss_all()
    console.print("[green]✓ Test complete[/green]")


if __name__ == "__main__":
    main()