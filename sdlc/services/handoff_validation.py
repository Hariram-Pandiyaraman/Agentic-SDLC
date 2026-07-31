"""Validate that a completed run is qualified for QA handoff."""

import json

from sdlc.models import HandoffValidationReport
from sdlc.services.artifact_store import ArtifactStore

REQUIRED_ARTIFACT_TYPES = {
    "requirement",
    "context_pack",
    "clarification",
    "brd",
    "backlog",
    "sprint_plan",
    "code_plan",
    "code",
    "test_case",
    "git_plan",
    "review",
    "test_result",
    "release",
    "qa_handoff",
    "lineage",
}


def validate_run_handoff(
    store: ArtifactStore,
    run_id: str,
    *,
    acceptance_criterion_ids: set[str] | None = None,
) -> HandoffValidationReport:
    required_criteria = acceptance_criterion_ids or {"AC-001"}
    artifacts = store.list_artifacts(run_id)
    artifact_types = {artifact.artifact_type for artifact in artifacts}
    missing_types = sorted(REQUIRED_ARTIFACT_TYPES - artifact_types)
    unlinked = sorted(
        {
            artifact.artifact_id
            for artifact in artifacts
            if artifact.artifact_type != "requirement"
            and not artifact.source_artifact_ids
        }
    )

    code = _latest_text(store, run_id, artifacts, "code")
    test_case = _latest_text(store, run_id, artifacts, "test_case")
    review = _latest_text(store, run_id, artifacts, "review")
    qa_handoff = _latest_text(store, run_id, artifacts, "qa_handoff")
    coverage_sources = {
        "implementation": code,
        "tests": test_case,
        "review": review,
        "handoff": qa_handoff,
    }
    criterion_gaps = {
        source: sorted(
            criterion_id
            for criterion_id in required_criteria
            if criterion_id not in content
        )
        for source, content in coverage_sources.items()
    }

    failed_test_requires_defect = False
    test_result_text = _latest_text(store, run_id, artifacts, "test_result")
    if test_result_text:
        try:
            failed = json.loads(test_result_text).get("status") == "failed"
        except json.JSONDecodeError:
            failed = '"status": "failed"' in test_result_text
        failed_test_requires_defect = failed and "defect" not in artifact_types

    findings: list[str] = []
    if missing_types:
        findings.append("Required artifact types are missing.")
    if unlinked:
        findings.append("One or more derived artifacts lack source links.")
    if any(criterion_gaps.values()):
        findings.append("Acceptance-criterion coverage is incomplete.")
    if failed_test_requires_defect:
        findings.append("A failed test result has no linked defect.")

    return HandoffValidationReport(
        run_id=run_id,
        ready=not findings,
        missing_artifact_types=missing_types,
        unlinked_artifacts=unlinked,
        acceptance_criterion_gaps=criterion_gaps,
        failed_test_requires_defect=failed_test_requires_defect,
        findings=findings,
    )


def _latest_text(
    store: ArtifactStore,
    run_id: str,
    artifacts: list,
    artifact_type: str,
) -> str:
    matches = [item for item in artifacts if item.artifact_type == artifact_type]
    if not matches:
        return ""
    latest = max(matches, key=lambda item: (item.created_at, item.version))
    return store.read_artifact(run_id, latest.artifact_id, latest.version)

