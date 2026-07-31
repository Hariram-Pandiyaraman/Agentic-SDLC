"""Structured outputs produced by the Phase 3 generation gateway."""

from typing import Literal

from pydantic import Field

from sdlc.models.common import StrictModel


class ClarificationOutput(StrictModel):
    requirement_id: str
    questions: list[dict]
    assumptions: list[dict]
    revision_feedback: dict | None = None


class MarkdownOutput(StrictModel):
    markdown: str = Field(min_length=1)


class SprintPlanOutput(MarkdownOutput):
    critical_path: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class ContextRankingOutput(StrictModel):
    ordered_artifact_ids: list[str]
    rationale: dict[str, str] = Field(default_factory=dict)


class GeneratedFile(StrictModel):
    path: str
    acceptance_criterion_ids: list[str] = Field(min_length=1)
    content: str = Field(min_length=1)


class ImplementationOutput(StrictModel):
    files: list[GeneratedFile] = Field(min_length=1)


class CriterionReview(StrictModel):
    acceptance_criterion_id: str
    status: Literal["covered", "partial", "missing"]
    finding: str
    severity: Literal["info", "low", "medium", "high", "critical"] = "info"


class ReviewOutput(StrictModel):
    criterion_reviews: list[CriterionReview] = Field(min_length=1)
    verdict: Literal["approved_for_sanity", "changes_required"]


class SanityOutput(StrictModel):
    acceptance_criterion_ids: list[str] = Field(min_length=1)
    status: Literal["passed", "failed"]
    summary: str


class ReleaseOutput(StrictModel):
    release_notes_markdown: str = Field(min_length=1)
    qa_handoff_markdown: str = Field(min_length=1)
    open_risks: list[str] = Field(default_factory=list)
