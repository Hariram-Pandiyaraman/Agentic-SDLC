import hashlib

from fastapi.testclient import TestClient

from api.main import create_app
from app.ui import COLORS, COMPONENTS, STATE_TREATMENTS, WorkflowVisualState
from sdlc import __version__
from sdlc.config import Settings
from sdlc.services.workflow_runner import WorkflowRunner


def _client(tmp_path) -> TestClient:
    settings = Settings(use_ollama=False, artifact_root=tmp_path / "artifacts", _env_file=None)
    runner = WorkflowRunner(settings.artifact_root, settings=settings)
    return TestClient(create_app(settings_override=settings, runner_override=runner))


def _relative_luminance(color: str) -> float:
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def test_application_version_is_consistent(tmp_path) -> None:
    client = _client(tmp_path)
    assert __version__ == "0.2.1"
    assert client.get("/").json() == {
        "name": "SDLC Agentic Framework API",
        "version": __version__,
        "environment": "development",
        "docs": "/docs",
        "health": "/health",
        "runs": "/api/v1/runs",
    }
    assert client.get("/openapi.json").json()["info"]["version"] == __version__


def test_run_and_artifact_api_contracts(tmp_path) -> None:
    client = _client(tmp_path)
    response = client.post("/api/v1/runs", json={
        "title": "Regression contract",
        "raw_requirement": "Create a versioned and traceable delivery artifact.",
        "simulate_test_failure": False,
    })
    assert response.status_code == 201
    started = response.json()
    assert set(started) == {"run_id", "status", "interrupts", "state"}
    assert started["status"] == "waiting_for_approval"
    assert set(started["interrupts"][0]) == {"id", "value"}
    assert {"gate", "artifact_id"} <= set(started["interrupts"][0]["value"])

    inspected = client.get(f"/api/v1/runs/{started['run_id']}").json()
    assert set(inspected) == {"run_id", "status", "interrupts", "state", "next", "artifacts"}
    listed = client.get(f"/api/v1/runs/{started['run_id']}/artifacts").json()
    assert set(listed) == {"run_id", "artifacts"}
    assert listed["artifacts"]
    record = listed["artifacts"][0]
    assert set(record) == {
        "artifact_id", "artifact_type", "version", "run_id", "source_artifact_ids",
        "producer_agent", "created_at", "approval_status", "model_metadata",
        "confidence", "checksum_sha256", "relative_path", "media_type",
    }

    artifact = client.get(
        f"/api/v1/runs/{started['run_id']}/artifacts/{record['artifact_id']}"
        f"?version={record['version']}"
    )
    assert artifact.status_code == 200
    assert artifact.headers["x-artifact-id"] == record["artifact_id"]
    assert artifact.headers["x-artifact-version"] == str(record["version"])
    assert artifact.headers["content-type"].startswith(record["media_type"])
    assert hashlib.sha256(artifact.content).hexdigest() == record["checksum_sha256"]


def test_every_workflow_state_has_non_color_treatment() -> None:
    assert set(STATE_TREATMENTS) == set(WorkflowVisualState)
    for treatment in STATE_TREATMENTS.values():
        assert treatment.label and treatment.icon and treatment.guidance
        assert _contrast(treatment.foreground, treatment.background) >= 4.5


def test_foundation_text_contrast_and_component_contracts() -> None:
    assert _contrast(COLORS["text"], COLORS["canvas"]) >= 4.5
    assert _contrast(COLORS["text_muted"], COLORS["surface"]) >= 4.5
    assert _contrast(COLORS["surface"], COLORS["primary"]) >= 4.5
    assert _contrast(COLORS["surface"], COLORS["primary_hover"]) >= 4.5
    assert {
        "status_badge", "workflow_stepper", "metric_card", "empty_state",
        "approval_panel", "artifact_card", "feedback_banner", "skeleton",
    } == set(COMPONENTS)
    assert all(spec.required_content and spec.accessibility for spec in COMPONENTS.values())
