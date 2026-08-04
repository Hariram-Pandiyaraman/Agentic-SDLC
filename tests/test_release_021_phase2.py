from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from sdlc.config import Settings
from sdlc.services.workflow_runner import WorkflowRunner


SOURCE = Path("frontend/src/main.jsx").read_text(encoding="utf-8")
STYLES = Path("frontend/src/styles.css").read_text(encoding="utf-8")


def _client(tmp_path) -> TestClient:
    settings = Settings(use_ollama=False, artifact_root=tmp_path / "artifacts", _env_file=None)
    runner = WorkflowRunner(settings.artifact_root, settings=settings)
    return TestClient(create_app(settings_override=settings, runner_override=runner))


def test_approval_resume_rejects_a_stale_or_wrong_artifact_version(tmp_path) -> None:
    client = _client(tmp_path)
    started = client.post("/api/v1/runs", json={
        "title": "Version-safe approval",
        "raw_requirement": "Create an approval that cannot accidentally target a stale artifact.",
    }).json()
    run_id = started["run_id"]
    artifact_id = started["interrupts"][0]["value"]["artifact_id"]
    target = next(
        item for item in client.get(f"/api/v1/runs/{run_id}/artifacts").json()["artifacts"]
        if item["artifact_id"] == artifact_id
    )

    stale = client.post(f"/api/v1/runs/{run_id}/resume", json={
        "status": "approved",
        "actor": "Phase 2 reviewer",
        "comment": "Approve the visible version",
        "artifact_id": artifact_id,
        "artifact_version": target["version"] + 1,
    })
    assert stale.status_code == 422
    assert "latest version" in stale.json()["detail"]
    assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "waiting_for_approval"

    accepted = client.post(f"/api/v1/runs/{run_id}/resume", json={
        "status": "approved",
        "actor": "Phase 2 reviewer",
        "comment": "Approved exact target",
        "artifact_id": artifact_id,
        "artifact_version": target["version"],
    })
    assert accepted.status_code == 200


def test_run_workspace_exposes_stage_timing_next_action_and_step_states() -> None:
    for label in ("Current stage", "Elapsed", "Last updated", "Fallbacks", "Next action"):
        assert label in SOURCE
    for state in ("Complete · fallback", "Blocked · approval", "Failed", "Active now", "Pending"):
        assert state in SOURCE
    assert 'role="progressbar"' in SOURCE
    assert 'aria-current={current ? "step" : undefined}' in SOURCE


def test_approval_workspace_repeats_and_submits_the_exact_target() -> None:
    assert "Decision target:" in SOURCE
    assert "Version context" in SOURCE
    assert "Decision history" in SOURCE
    assert "Submitting for" in SOURCE
    assert "artifact_id: target.artifact_id" in SOURCE
    assert "artifact_version: target.version" in SOURCE
    assert 'status === "rejected" && !comment.trim()' in SOURCE
    assert ".approval-review { display: grid" in STYLES


def test_artifact_experience_supports_filters_versions_and_readable_views() -> None:
    for label in ("Artifact type", "Producer", "Version history", "Formatted", "Raw"):
        assert label in SOURCE
    for artifact_type in (
        "brd", "backlog", "sprint_plan", "code_plan", "test_case",
        "test_result", "defect", "release", "qa_handoff",
    ):
        assert f'"{artifact_type}"' in SOURCE
    assert "function MarkdownContent" in SOURCE
    assert "function StructuredValue" in SOURCE
    assert "Metadata and source links" in SOURCE
    assert "Download version" in SOURCE


def test_lineage_has_grouping_zoom_details_and_accessible_list_fallback() -> None:
    for label in ("Map zoom", "Zoom out", "Zoom in", "Selected node", "Connections"):
        assert label in SOURCE
    assert 'view === "list"' in SOURCE
    assert 'className="lineage-table"' in SOURCE
    assert 'aria-pressed={selected}' in SOURCE
    assert ".lineage-groups" in STYLES

