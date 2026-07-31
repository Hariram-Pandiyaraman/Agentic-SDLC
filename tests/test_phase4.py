import io
import zipfile

from fastapi.testclient import TestClient

from api.main import create_app
from sdlc.config import Settings
from sdlc.services.workflow_runner import WorkflowRunner


def client_for(tmp_path) -> TestClient:
    settings = Settings(
        use_ollama=False,
        artifact_root=tmp_path / "artifacts",
        _env_file=None,
    )
    runner = WorkflowRunner(settings.artifact_root, settings=settings)
    return TestClient(
        create_app(settings_override=settings, runner_override=runner)
    )


def start_run(client: TestClient, simulate_failure: bool = False) -> dict:
    response = client.post(
        "/api/v1/runs",
        json={
            "title": "Phase 4 feature",
            "raw_requirement": "Create a complete traceable feature delivery workflow.",
            "simulate_test_failure": simulate_failure,
        },
    )
    assert response.status_code == 201
    return response.json()


def approve(client: TestClient, run_id: str) -> dict:
    response = client.post(
        f"/api/v1/runs/{run_id}/resume",
        json={
            "status": "approved",
            "actor": "API Test Architect",
            "comment": "Approved",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_complete_api_flow_artifacts_lineage_and_export(tmp_path) -> None:
    client = client_for(tmp_path)
    started = start_run(client)
    run_id = started["run_id"]
    assert started["interrupts"][0]["value"]["gate"] == "scope"

    status = client.get(f"/api/v1/runs/{run_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "waiting_for_approval"

    assert approve(client, run_id)["interrupts"][0]["value"]["gate"] == "brd"
    assert approve(client, run_id)["interrupts"][0]["value"]["gate"] == "code_plan"
    completed = approve(client, run_id)
    assert completed["status"] == "completed"

    artifacts = client.get(f"/api/v1/runs/{run_id}/artifacts")
    assert artifacts.status_code == 200
    artifact_types = {
        item["artifact_type"] for item in artifacts.json()["artifacts"]
    }
    assert {"requirement", "brd", "code", "qa_handoff", "lineage"} <= artifact_types

    qa = client.get(f"/api/v1/runs/{run_id}/artifacts/QA-001")
    assert qa.status_code == 200
    assert "AC-001" in qa.text

    lineage = client.get(f"/api/v1/runs/{run_id}/lineage")
    assert lineage.status_code == 200
    assert "REQ-001" in lineage.json()["nodes"]

    exported = client.get(f"/api/v1/runs/{run_id}/export")
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        names = set(archive.namelist())
    assert "manifest.json" in names
    assert "qa-001.md" in names


def test_brd_rejection_creates_retrievable_version(tmp_path) -> None:
    client = client_for(tmp_path)
    run_id = start_run(client)["run_id"]
    approve(client, run_id)

    rejected = client.post(
        f"/api/v1/runs/{run_id}/resume",
        json={
            "status": "rejected",
            "actor": "API Test Architect",
            "comment": "Clarify the success criteria.",
        },
    )
    assert rejected.status_code == 200
    assert rejected.json()["interrupts"][0]["value"]["gate"] == "brd"

    artifacts = client.get(f"/api/v1/runs/{run_id}/artifacts").json()["artifacts"]
    brd_versions = [
        item["version"] for item in artifacts if item["artifact_id"] == "BRD-001"
    ]
    assert brd_versions == [1, 2]
    first = client.get(
        f"/api/v1/runs/{run_id}/artifacts/BRD-001?version=1"
    )
    second = client.get(
        f"/api/v1/runs/{run_id}/artifacts/BRD-001?version=2"
    )
    assert first.status_code == second.status_code == 200
    assert "Revision Feedback" not in first.text
    assert "Clarify the success criteria." in second.text


def test_api_validation_and_unknown_run(tmp_path) -> None:
    client = client_for(tmp_path)
    invalid = client.post(
        "/api/v1/runs",
        json={"title": "Short", "raw_requirement": "tiny"},
    )
    assert invalid.status_code == 422
    assert client.get("/api/v1/runs/RUN-MISSING").status_code == 404

