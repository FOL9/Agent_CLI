# ============================================================
# agent.py — Master Task AI Agent using Google Gemini
# ============================================================

import os
import json
import time
import logging
from typing import List, Dict, Any, Callable

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from google import genai
from google.genai import types

# ============================================================
# 1. Setup
# ============================================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash"

client = genai.Client(api_key=GEMINI_API_KEY)

# ============================================================
# 2. Task Schemas
# ============================================================

class TaskPlan(BaseModel):
    tasks: List[str]

class TaskResult(BaseModel):
    task: str
    output: Any
    duration_ms: int

# ============================================================
# 3. Sub Tasks (Executors)
# ============================================================

def analyze_code(context: Dict[str, Any]) -> Any:
    return {
        "summary": "Codebase structure analyzed",
        "files": context.get("files", [])
    }

def security_audit(context: Dict[str, Any]) -> Any:
    return {
        "issues_found": 2,
        "severity": "medium",
        "notes": "Missing rate limiting"
    }

def performance_review(context: Dict[str, Any]) -> Any:
    return {
        "bottlenecks": ["DB queries"],
        "suggestions": ["Add caching", "Optimize indexes"]
    }

# ============================================================
# 4. Task Registry
# ============================================================

TASK_REGISTRY: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    "analyze_code": analyze_code,
    "security_audit": security_audit,
    "performance_review": performance_review,
}

# ============================================================
# 5. Gemini Planner (STRICT JSON)
# ============================================================

PLANNER_SYSTEM_PROMPT = """
You are an AI task planner.

Rules:
- You MUST return valid JSON only.
- Do NOT explain.
- Do NOT add extra fields.

Available tasks:
- analyze_code
- security_audit
- performance_review

Return format:
{
  "tasks": ["task_name_1", "task_name_2"]
}
"""

def gemini_plan(user_request: str, retries: int = 3) -> TaskPlan:
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text=PLANNER_SYSTEM_PROMPT),
                            types.Part(text=f"User request: {user_request}")
                        ]
                    )
                ]
            )

            raw = response.text.strip()
            plan = TaskPlan.model_validate_json(raw)
            return plan

        except (ValidationError, json.JSONDecodeError) as e:
            logging.warning(f"Planner parse failed (attempt {attempt+1})")
            time.sleep(0.5)

    raise RuntimeError("Gemini planner failed after retries")

# ============================================================
# 6. Master Task Executor
# ============================================================

def master_task_executor(
    plan: TaskPlan,
    context: Dict[str, Any]
) -> List[TaskResult]:

    results: List[TaskResult] = []

    for task_name in plan.tasks:
        task_fn = TASK_REGISTRY.get(task_name)

        if not task_fn:
            logging.warning(f"Unknown task skipped: {task_name}")
            continue

        start = time.time()
        output = task_fn(context)
        duration = int((time.time() - start) * 1000)

        results.append(
            TaskResult(
                task=task_name,
                output=output,
                duration_ms=duration
            )
        )

    return results

# ============================================================
# 7. Public Runner (Agent Interface)
# ============================================================

def run_agent(user_request: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logging.info("Planning tasks with Gemini...")
    plan = gemini_plan(user_request)

    logging.info(f"Tasks selected: {plan.tasks}")
    results = master_task_executor(plan, context)

    return {
        "request": user_request,
        "executed_tasks": [r.task for r in results],
        "results": [r.model_dump() for r in results]
    }

# ============================================================
# 8. Example Usage
# ============================================================

if __name__ == "__main__":
    context = {
        "project": "FastAPI Backend",
        "files": ["main.py", "auth.py", "users.py"]
    }

    response = run_agent(
        user_request="Analyze the code and check security and performance",
        context=context
    )

    print(json.dumps(response, indent=2))
