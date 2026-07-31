"""Validated SDLC domain contracts."""

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from sdlc.models.common import (
    ApprovalStatus,
    Confidence,
    Severity,
    StrictModel,
    TraceableModel,
    utc_now,
)


class Actor(StrictModel):
    name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    goals: list[str] = Field(default_factory=list)


class Assumption(TraceableModel):
    assumption_id: str
    text: str = Field(min_length=1)
    status: Literal["proposed", "confirmed", "rejected"] = "proposed"


class Constraint(TraceableModel):
    constraint_id: str
    text: str = Field(min_length=1)
    category: Literal["business", "technical", "security", "compliance", "schedule", "other"]


class Dependency(TraceableModel):
    dependency_id: str
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    status: Literal["known", "unconfirmed", "blocked", "resolved"] = "known"


class OpenQuestion(TraceableModel):
    question_id: str
    question: str = Field(min_length=1)
    blocking: bool = False
    answer: str | None = None


class NormalizedRequirement(StrictModel):
    requirement_id: str
    title: str = Field(min_length=1)
    feature_intent: str = Field(min_length=1)
    raw_input: str = Field(min_length=1)
    actors: list[Actor] = Field(min_length=1)
    business_rules: list[str] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    dependencies: list[Dependency] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ContextItem(StrictModel):
    artifact_id: str
    artifact_type: str
    title: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    relevance_score: float = Field(ge=0, le=1)
    relationship: str = "RELATED_TO"
    metadata: dict = Field(default_factory=dict)


class ContextPack(TraceableModel):
    context_pack_id: str
    requirement_id: str
    query_terms: list[str]
    items: list[ContextItem]
    provider: Literal["fixture", "neo4j"]
    retrieved_at: datetime = Field(default_factory=utc_now)


class BRDSectionMetadata(StrictModel):
    section_name: str
    confidence: Confidence
    source_artifact_ids: list[str] = Field(default_factory=list)
    open_issues: list[str] = Field(default_factory=list)


class BRDMetadata(TraceableModel):
    brd_id: str
    version: int = Field(default=1, ge=1)
    title: str
    sections: list[BRDSectionMetadata]
    approval_status: ApprovalStatus = ApprovalStatus.PENDING


class AcceptanceCriterion(TraceableModel):
    criterion_id: str
    given: str = Field(min_length=1)
    when: str = Field(min_length=1)
    then: str = Field(min_length=1)


class Subtask(TraceableModel):
    subtask_id: str
    title: str
    description: str


class Story(TraceableModel):
    story_id: str
    title: str
    narrative: str
    acceptance_criteria: list[AcceptanceCriterion] = Field(min_length=1)
    story_points: int = Field(ge=1, le=21)
    dependencies: list[str] = Field(default_factory=list)
    subtasks: list[Subtask] = Field(default_factory=list)


class Epic(TraceableModel):
    epic_id: str
    title: str
    objective: str
    stories: list[Story] = Field(min_length=1)


class Backlog(TraceableModel):
    backlog_id: str
    epics: list[Epic] = Field(min_length=1)


class TestMapping(TraceableModel):
    test_case_id: str
    acceptance_criterion_ids: list[str] = Field(min_length=1)
    test_name: str
    test_type: Literal["unit", "integration", "contract", "workflow", "sanity"]
    status: Literal["planned", "passed", "failed", "skipped"] = "planned"


class Defect(TraceableModel):
    defect_id: str
    title: str
    description: str
    severity: Severity
    status: Literal["open", "in_progress", "resolved", "closed"] = "open"
    acceptance_criterion_ids: list[str] = Field(min_length=1)
    test_result_id: str


class ApprovalRecord(StrictModel):
    approval_id: str
    gate: Literal["scope", "brd", "code_plan"]
    status: ApprovalStatus
    artifact_id: str
    actor: str
    comment: str | None = None
    decided_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def require_comment_for_rejection(self) -> "ApprovalRecord":
        if self.status == ApprovalStatus.REJECTED and not self.comment:
            raise ValueError("a rejection must include a comment")
        return self

