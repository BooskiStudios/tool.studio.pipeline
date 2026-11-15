"""The text sent to the model for each kind of agent call: planning, a step, and the final deliverable."""

import json
import re
from dataclasses import dataclass
from typing import Any

from booski_core.modules.agents.models import Agent, AgentRun

MAX_EARLIER_OUTPUT_CHARS = 2_000

HOUSE_RULES = (
    "You cannot change studio records, run tools or touch files: you can only plan, review and draft. "
    "Never claim to have done anything else. People will review your work and decide what to apply.",
    "Use the studio knowledge provided. When you rely on it, cite the item's [number]. If something isn't "
    "in the knowledge and you aren't sure of it, say so rather than guessing.",
)


def system_prompt(agent: Agent, workspace_name: str) -> str:
    lines = [
        f"You are {agent.name}, an AI agent working for the game studio {workspace_name}.",
        agent.guidance,
    ]
    if agent.responsibilities:
        lines += ["", "Your responsibilities:", *[f"- {r}" for r in agent.responsibilities]]
    rules = [*agent.must_not, *HOUSE_RULES]
    lines += ["", "You must not, and you must always:", *[f"- {r}" for r in rules]]
    return "\n".join(line for line in lines if line is not None)


def _notes(run: AgentRun) -> str:
    if not run.notes:
        return ""
    items = "\n".join(f"- {note['text']}" for note in run.notes)
    return f"\nInstructions from people (follow these; newest last):\n{items}\n"


def _knowledge(context: str) -> str:
    return (
        f"\nStudio knowledge:\n{context}\n" if context else "\nStudio knowledge: (nothing relevant found)\n"
    )


def planning_prompt(run: AgentRun, agent: Agent, colleagues: dict[str, Agent], context: str) -> str:
    team = "\n".join(f'- "{key}": {a.name}, {a.description}' for key, a in colleagues.items())
    delegate = (
        f'You may hand a step to one of these colleagues by setting "agent" to their key:\n{team}\n'
        if colleagues
        else ""
    )
    return (
        f"Goal: {run.goal}\n{_notes(run)}{_knowledge(context)}\n"
        f"Make a short plan of at most {agent.max_steps} steps to reach the goal. {delegate}"
        f'Use "{agent.key}" for steps you do yourself. The last step should produce the deliverable.\n'
        "Reply with JSON only, in this shape: "
        '{"steps": [{"title": "...", "instruction": "...", "agent": "..."}]}'
    )


def step_prompt(run: AgentRun, step: dict[str, Any], context: str) -> str:
    plan = "\n".join(f"{s['n']}. {s['title']} ({s['status']})" for s in run.plan)
    earlier = "\n\n".join(
        f"[Step {s['n']}: {s['title']}]\n{_clip(s.get('output', ''))}"
        for s in run.plan
        if s["status"] == "completed" and s["n"] < step["n"]
    )
    earlier_block = f"\nResults of earlier steps:\n{earlier}\n" if earlier else ""
    return (
        f"Goal: {run.goal}\n\nPlan:\n{plan}\n{earlier_block}{_notes(run)}{_knowledge(context)}\n"
        f"Do step {step['n']} now: {step['title']}\n{step['instruction']}\n\n"
        "Reply with the result of this step only."
    )


def final_prompt(run: AgentRun) -> str:
    results = "\n\n".join(f"[Step {s['n']}: {s['title']}]\n{s.get('output', '')}" for s in run.plan)
    return (
        f"Goal: {run.goal}\n{_notes(run)}\nResults of the plan's steps:\n{results}\n\n"
        "Combine these into the final deliverable for the goal, in Markdown, for people to review. "
        "Keep the useful detail, remove repetition, and end with a short list of open questions or risks."
    )


def _clip(text: str) -> str:
    return (
        text if len(text) <= MAX_EARLIER_OUTPUT_CHARS else text[:MAX_EARLIER_OUTPUT_CHARS] + "\n[…shortened]"
    )


@dataclass(frozen=True)
class PlannedStep:
    title: str
    instruction: str
    agent: str


def parse_plan(text: str, *, own_key: str, allowed: set[str], max_steps: int) -> list[PlannedStep]:
    """Reads the model's JSON plan. Unknown delegates fall back to the agent itself; a reply that isn't a
    usable plan becomes a single step, so a run never fails just because the plan was badly formatted."""
    steps: list[PlannedStep] = []
    match = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        data = {}
    raw = data.get("steps") if isinstance(data, dict) else None
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()[:200]
        instruction = str(item.get("instruction", "")).strip()[:4_000]
        if not title and not instruction:
            continue
        agent = str(item.get("agent", own_key)).strip()
        steps.append(
            PlannedStep(
                title or instruction[:80], instruction or title, agent if agent in allowed else own_key
            )
        )
    if not steps:
        steps = [PlannedStep("Do the work", "Achieve the goal and produce the deliverable.", own_key)]
    return steps[:max_steps]
