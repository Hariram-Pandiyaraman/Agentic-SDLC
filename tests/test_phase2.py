import pytest

from sdlc.graph.workflow import AGENT_NAMES
from sdlc.services.retry import execute_with_retry
from sdlc.services.workflow_runner import WorkflowRunner


def approve() -> dict:
    return {"status": "approved", "actor": "Test Architect", "comment": "Approved"}


def test_workflow_pauses_and_completes_all_eleven_agents(tmp_path) -> None:
    runner = WorkflowRunner(tmp_path / "artifacts")
    response = runner.start(
        "Create a traceable feature workflow.",
        title="Traceable workflow",
        run_id="RUN-PHASE2-001",
    )
    assert response["status"] == "waiting_for_approval"
    assert response["interrupts"][0]["value"]["gate"] == "scope"

    response = runner.resume("RUN-PHASE2-001", approve())
    assert response["interrupts"][0]["value"]["gate"] == "brd"

    response = runner.resume("RUN-PHASE2-001", approve())
    assert response["interrupts"][0]["value"]["gate"] == "code_plan"

    response = runner.resume("RUN-PHASE2-001", approve())
    assert response["status"] == "completed"

    executed_agents = {
        result["agent_name"] for result in response["state"]["agent_results"]
    }
    assert executed_agents == AGENT_NAMES
    assert response["state"]["artifact_ids"]["qa_handoff"] == ["QA-001"]
    manifest = runner.store.load_manifest("RUN-PHASE2-001")
    assert len(manifest.artifacts) >= 16


def test_scope_rejection_revises_clarification_and_pauses_again(tmp_path) -> None:
    runner = WorkflowRunner(tmp_path / "artifacts")
    response = runner.start(
        "Create a workflow.",
        run_id="RUN-PHASE2-002",
    )
    response = runner.resume(
        "RUN-PHASE2-002",
        {
            "status": "rejected",
            "actor": "Test Architect",
            "comment": "Clarify offline behavior.",
        },
    )
    assert response["status"] == "waiting_for_approval"
    assert response["interrupts"][0]["value"]["gate"] == "scope"
    clarification_artifacts = [
        artifact
        for artifact in runner.store.list_artifacts("RUN-PHASE2-002")
        if artifact.artifact_type == "clarification"
    ]
    assert len(clarification_artifacts) == 2


def test_failed_sanity_creates_linked_defect(tmp_path) -> None:
    runner = WorkflowRunner(tmp_path / "artifacts")
    response = runner.start(
        "Create a workflow.",
        run_id="RUN-PHASE2-003",
        simulate_test_failure=True,
    )
    for _ in range(3):
        response = runner.resume("RUN-PHASE2-003", approve())
    assert response["status"] == "completed"
    assert response["state"]["artifact_ids"]["defect"] == ["DEF-001"]
    qa = runner.store.read_artifact("RUN-PHASE2-003", "QA-001")
    assert "Open defects: 1" in qa


def test_bounded_retry_uses_fallback() -> None:
    attempts = 0

    def fail() -> str:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("model unavailable")

    outcome = execute_with_retry(fail, lambda _exc: "template", max_attempts=2)
    assert outcome.value == "template"
    assert outcome.attempts == 2
    assert outcome.fallback_used is True
    assert len(outcome.errors) == 2


def test_rejection_requires_comment() -> None:
    runner = WorkflowRunner("artifacts-test-not-created")
    with pytest.raises(ValueError, match="rejection"):
        runner.resume(
            "RUN-MISSING",
            {"status": "rejected", "actor": "Architect"},
        )

