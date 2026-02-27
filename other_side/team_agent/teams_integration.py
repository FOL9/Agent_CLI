"""
SDX Agent + Teams Integration
Drop-in patch for the existing SDX Agent run_interactive() loop.

HOW TO INTEGRATE:
─────────────────
In your existing main.py / SDXAgent class, add these lines:

1. At the top of the file:
   from teams_cli import TeamsCLI

2. In SDXAgent.__init__():
   self.teams = TeamsCLI(env_path=".env", tools=self.get_tools())

3. In run_interactive(), BEFORE the existing command handler check:
   # ── Teams intercept ──────────────────────────────────────────
   if user_input.lower().startswith("/team"):
       response = self.teams.handle(user_input)
       if response:
           self.ui.console.print(response)
       continue
   # ────────────────────────────────────────────────────────────

That's it. The Teams system will run alongside your existing agent.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STANDALONE USAGE (test without SDX Agent):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  python teams_cli.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE SESSION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  team → /team spawn fullstack
  ✓ Team spawned (4 members):
    Architect  architect  key:...Gza4
    Backend    backend    key:...jjtc
    Frontend   frontend   key:...lUI  
    QA         qa         key:...WFlU

  team → build me a REST API for user authentication

  [Orchestrator creates tasks, distributes to Backend/QA, members execute]

  team → /team status
  [Shows live member status + task board]

  team → /team chat Backend "what's your current approach to JWT?"
  [Backend responds directly]

  team → /team mail
  [Shows all inter-agent messages]

  team → /team dismiss all
  ✓ All team members dismissed
"""

# ─────────────────────────────────────────────────────────────────────────────
# EXACT PATCH to apply in main.py run_interactive()
# ─────────────────────────────────────────────────────────────────────────────

PATCH_FOR_SDXAGENT = '''
# Add to SDXAgent.__init__() after self.command_handler = ...:
from teams_cli import TeamsCLI
self.teams = TeamsCLI(env_path=".env", tools=self.get_tools())

# Add to run_interactive() BEFORE the command_handler.is_command() check:
# ─── Teams intercept ───────────────────────────────────────────────────────
if user_input.lower().startswith("/team"):
    self.ui.separator()
    response = self.teams.handle(user_input)
    if response:
        self.ui.console.print(response)
    self.ui.separator()
    continue
# ───────────────────────────────────────────────────────────────────────────
'''


# ─────────────────────────────────────────────────────────────────────────────
# Standalone entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    from teams_cli import TeamsCLI
    cli = TeamsCLI(env_path=".env")
    cli.run_standalone()