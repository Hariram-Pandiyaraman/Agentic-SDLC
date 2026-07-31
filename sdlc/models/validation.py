"""Final run-readiness validation contracts."""

from pydantic import Field

from sdlc.models.common import StrictModel


class HandoffValidationReport(StrictModel):
    run_id: str
    ready: bool
    missing_artifact_types: list[str] = Field(default_factory=list)
    unlinked_artifacts: list[str] = Field(default_factory=list)
    acceptance_criterion_gaps: dict[str, list[str]] = Field(default_factory=dict)
    failed_test_requires_defect: bool = False
    findings: list[str] = Field(default_factory=list)

