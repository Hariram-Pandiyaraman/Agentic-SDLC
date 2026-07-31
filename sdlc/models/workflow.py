"""LangGraph workflow state and execution contracts."""

from typing import Literal, NotRequired, TypedDict

from pydantic import Field, model_validator

from sdlc.models.common import ApprovalStatus, StrictModel, utc_now


class GateDecision(StrictModel):
    status: Literal["approved", "rejected"]
    actor: str = Field(min_length=1)
    comment: str | None = None

    @model_validator(mode="after")
    def require_rejection_comment(self) -> "GateDecision":
        if self.status == "rejected" and not self.comment:
            raise ValueError("a rejection must include a comment")
        return self


class AgentResult(StrictModel):
    agent_name: str
    status: Literal["completed", "completed_with_fallback", "failed"]
    summary: str
    output_artifact_ids: list[str] = Field(default_factory=list)
    attempts: int = Field(default=1, ge=1)
    fallback_used: bool = False
    completed_at: str = Field(default_factory=lambda: utc_now().isoformat())


class WorkflowState(TypedDict):
    run_id: str
    raw_requirement: str
    requirement_title: str
    simulate_test_failure: bool
    status: str
    current_node: str
    artifact_ids: dict[str, list[str]]
    agent_results: list[dict]
    approvals: list[dict]
    errors: list[dict]
    fallback_events: list[dict]
    normalized_requirement: NotRequired[dict]
    context_pack: NotRequired[dict]
    scope_approved: NotRequired[bool]
    brd_approved: NotRequired[bool]
    code_plan_approved: NotRequired[bool]
    gate_feedback: NotRequired[dict]
    backlog: NotRequired[dict]
    implementation: NotRequired[dict]
    review: NotRequired[dict]
    release_output: NotRequired[dict]
    test_results: NotRequired[list[dict]]
    defects: NotRequired[list[dict]]
