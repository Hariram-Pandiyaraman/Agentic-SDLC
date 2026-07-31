"""Versioned prompt catalog for all Phase 3 generative tasks."""

from dataclasses import dataclass
from typing import Any

SYSTEM_PROMPT = """You are a specialist agent in a controlled SDLC workflow.
Return only JSON that matches the supplied JSON Schema.
Never invent source IDs or acceptance-criterion IDs.
Preserve every provided traceability ID exactly.
State uncertainty explicitly instead of fabricating facts.
Do not emit shell commands that execute generated code or mutate remote systems.
The output must be concise, deterministic, and suitable for audit.
"""


@dataclass(frozen=True)
class PromptTemplate:
    task: str
    version: str
    instruction: str

    def render(self, variables: dict[str, Any]) -> str:
        return (
            f"Task: {self.task}\nPrompt version: {self.version}\n"
            f"{self.instruction}\n\nInput:\n{variables}"
        )


PROMPTS = {
    "intake": PromptTemplate(
        "intake",
        "1.0",
        "Normalize the raw requirement into actors, rules, constraints, assumptions, "
        "dependencies, non-functional requirements, and open questions.",
    ),
    "context_ranking": PromptTemplate(
        "context_ranking",
        "1.0",
        "Rank only the supplied context artifact IDs by relevance to the requirement.",
    ),
    "clarification": PromptTemplate(
        "clarification",
        "1.0",
        "Produce targeted clarification questions and explicit assumptions. Incorporate "
        "revision feedback when present.",
    ),
    "brd": PromptTemplate(
        "brd",
        "1.0",
        "Create a concise BRD in Markdown with objective, scope, rules, constraints, "
        "success criteria, assumptions, and unresolved issues.",
    ),
    "stories": PromptTemplate(
        "stories",
        "1.0",
        "Decompose the approved BRD into epics, stories, subtasks, estimates, and "
        "Given-When-Then acceptance criteria while preserving all supplied IDs.",
    ),
    "planning": PromptTemplate(
        "planning",
        "1.0",
        "Create a sprint plan with sequence, critical path, risks, and handoff readiness.",
    ),
    "code_plan": PromptTemplate(
        "code_plan",
        "1.0",
        "Create an implementation plan mapped explicitly to every acceptance criterion.",
    ),
    "implementation": PromptTemplate(
        "implementation",
        "1.0",
        "Generate a safe implementation stub. Include acceptance-criterion IDs in file "
        "metadata and code comments. Do not execute anything.",
    ),
    "review": PromptTemplate(
        "review",
        "1.0",
        "Review each acceptance criterion against the implementation and tests. Return "
        "one criterion review per supplied criterion, including gaps and severity.",
    ),
    "sanity": PromptTemplate(
        "sanity",
        "1.0",
        "Summarize the supplied deterministic test evidence without changing its status.",
    ),
    "release": PromptTemplate(
        "release",
        "1.0",
        "Create release notes and a QA handoff. Include every requirement, BRD, code, "
        "test, defect, and acceptance-criterion ID supplied in the input.",
    ),
}


def render_prompt(task: str, variables: dict[str, Any]) -> tuple[str, str]:
    if task not in PROMPTS:
        raise ValueError(f"unknown generation task: {task}")
    template = PROMPTS[task]
    return template.render(variables), template.version

