"""Deterministic Phase 2 agent outputs used without a local model."""

from sdlc.models import (
    AcceptanceCriterion,
    Actor,
    Backlog,
    Constraint,
    Defect,
    Epic,
    NormalizedRequirement,
    Story,
    Subtask,
    TestMapping,
)
from sdlc.models.common import Severity


def normalized_requirement(raw: str, title: str) -> NormalizedRequirement:
    return NormalizedRequirement(
        requirement_id="REQ-001",
        title=title,
        feature_intent=raw.strip(),
        raw_input=raw,
        actors=[
            Actor(
                name="Solution Architect",
                role="Architect and approval owner",
                goals=["Preserve control at scope, BRD, and code-plan gates"],
            )
        ],
        business_rules=[
            "Implementation generation requires an approved code plan.",
            "Every downstream artifact must reference its source artifacts.",
        ],
        constraints=[
            Constraint(
                constraint_id="CON-001",
                text="The PoC must operate without external LLM API keys.",
                category="technical",
            )
        ],
        non_functional_requirements=[
            "Workflow execution must be resumable at approval gates.",
            "Fallback use must be visible in the run manifest.",
        ],
        assumptions=[],
        dependencies=[],
        open_questions=[],
    )


def clarification(requirement: NormalizedRequirement, feedback: dict | None = None) -> dict:
    return {
        "requirement_id": requirement.requirement_id,
        "questions": [
            {
                "question_id": "Q-001",
                "question": "Is the deterministic offline path acceptable for this PoC?",
                "answer": "Yes; local services can be connected later.",
                "blocking": False,
            }
        ],
        "assumptions": [
            {
                "assumption_id": "ASM-001",
                "text": "One feature requirement is processed per run.",
                "status": "confirmed",
            }
        ],
        "revision_feedback": feedback,
    }


def brd_markdown(requirement: NormalizedRequirement, feedback: dict | None = None) -> str:
    revision = (
        f"\n## Revision Feedback\n\n{feedback.get('comment')}\n"
        if feedback and feedback.get("comment")
        else ""
    )
    return f"""# Business Requirements Document

## Feature

{requirement.title}

## Business Objective

{requirement.feature_intent}

## Scope

- Normalize one feature requirement.
- Preserve traceability through planning, code, tests, and QA handoff.
- Pause for architect decisions at three approval gates.

## Success Criteria

- Every agent produces a versioned artifact.
- Rejected gates route back to the owning agent.
- The workflow completes with local deterministic fallbacks.
{revision}
"""


def backlog(brd_id: str) -> Backlog:
    criterion = AcceptanceCriterion(
        criterion_id="AC-001",
        given="a valid feature requirement",
        when="the architect approves all workflow gates",
        then="a traceable QA handoff is generated",
        source_artifact_ids=[brd_id],
    )
    story = Story(
        story_id="US-001",
        title="Generate a traceable delivery package",
        narrative="As an architect, I want linked SDLC artifacts so that handoffs retain context.",
        acceptance_criteria=[criterion],
        story_points=5,
        subtasks=[
            Subtask(
                subtask_id="TASK-001",
                title="Run the checkpointed workflow",
                description="Execute and resume the agent graph through all approval gates.",
                source_artifact_ids=[brd_id],
            )
        ],
        source_artifact_ids=[brd_id],
    )
    return Backlog(
        backlog_id="BACKLOG-001",
        epics=[
            Epic(
                epic_id="EPIC-001",
                title="Agentic SDLC automation",
                objective="Create a controlled and traceable feature-delivery flow.",
                stories=[story],
                source_artifact_ids=[brd_id],
            )
        ],
        source_artifact_ids=[brd_id],
    )


def test_mapping(status: str = "planned") -> TestMapping:
    return TestMapping(
        test_case_id="TC-001",
        acceptance_criterion_ids=["AC-001"],
        test_name="test_traceable_handoff",
        test_type="workflow",
        status=status,
        source_artifact_ids=["AC-001"],
    )


def defect(test_result_id: str) -> Defect:
    return Defect(
        defect_id="DEF-001",
        title="Traceable handoff sanity failure",
        description="The simulated sanity path reported a failed acceptance criterion.",
        severity=Severity.HIGH,
        acceptance_criterion_ids=["AC-001"],
        test_result_id=test_result_id,
        source_artifact_ids=[test_result_id],
    )

