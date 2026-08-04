import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from api.main import create_app
from sdlc.config import Settings
from sdlc.models.artifacts import ArtifactRecord
from sdlc.persistence import Database, SqlAlchemyRepository
from sdlc.persistence.models import ApprovalRow, ArtifactRow, WorkflowSnapshotRow
from sdlc.services.workflow_runner import WorkflowRunner


REQUIRED_TABLES = {
    "runs", "artifacts", "artifact_versions", "artifact_sources", "approvals",
    "fallback_events", "workflow_snapshots", "workflow_writes", "lineage_nodes",
    "lineage_edges", "schema_metadata", "alembic_version",
}


def _database(tmp_path) -> Database:
    return Database(f"sqlite:///{(tmp_path / 'phase3.db').as_posix()}")


def _restart(root) -> WorkflowRunner:
    return WorkflowRunner(root)


def test_fresh_sqlite_database_migrates_and_enables_safety_pragmas(tmp_path) -> None:
    database = _database(tmp_path)
    assert REQUIRED_TABLES <= set(inspect(database.engine).get_table_names())
    with database.engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
        assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar() == 5000
        assert connection.exec_driver_sql("PRAGMA journal_mode").scalar().lower() == "wal"


def test_all_rejection_loops_and_happy_path_survive_runner_restart(tmp_path) -> None:
    root = tmp_path / "artifacts"
    runner = _restart(root)
    response = runner.start(
        "Create a restart-safe workflow with immutable approval history.",
        title="Durable workflow",
        run_id="RUN-PHASE3-RESTART",
    )
    revisions = {"scope": "clarification", "brd": "brd", "code_plan": "code_plan"}

    for gate, artifact_type in revisions.items():
        runner.database.dispose()
        runner = _restart(root)
        inspected = runner.inspect(response["run_id"])
        assert inspected["status"] == "waiting_for_approval"
        assert inspected["interrupts"][0]["value"]["gate"] == gate
        response = runner.resume(response["run_id"], {
            "status": "rejected", "actor": "Restart reviewer",
            "comment": f"Revise {gate} before approval",
        })
        assert response["status"] == "waiting_for_approval"
        revised = [
            (item.artifact_id, item.version) for item in runner.store.list_artifacts(response["run_id"])
            if item.artifact_type == artifact_type
        ]
        assert len(revised) == 2

        runner.database.dispose()
        runner = _restart(root)
        response = runner.resume(response["run_id"], {
            "status": "approved", "actor": "Restart reviewer", "comment": "Approved revision",
        })

    assert response["status"] == "completed"
    runner.database.dispose()
    final_runner = _restart(root)
    final = final_runner.inspect(response["run_id"])
    assert final["status"] == "completed"
    with final_runner.database.session() as session:
        assert len(session.scalars(select(ApprovalRow).where(ApprovalRow.run_id == response["run_id"])).all()) == 6
        assert session.scalar(select(WorkflowSnapshotRow).where(WorkflowSnapshotRow.run_id == response["run_id"]).limit(1)) is not None
    assert final_runner.repository.read_lineage(response["run_id"])["nodes"]


def test_dashboard_and_pending_approval_queries_are_database_backed(tmp_path) -> None:
    settings = Settings(
        use_ollama=False,
        artifact_root=tmp_path / "artifacts",
        database_url=f"sqlite:///{(tmp_path / 'api.db').as_posix()}",
        _env_file=None,
    )
    runner = WorkflowRunner(settings.artifact_root, settings=settings)
    client = TestClient(create_app(settings_override=settings, runner_override=runner))
    started = client.post("/api/v1/runs", json={
        "title": "Queryable durable run",
        "raw_requirement": "Persist this run so dashboard filters can find it after restart.",
    }).json()

    listed = client.get("/api/v1/runs", params={"query": "durable", "status": "waiting_for_approval"})
    assert listed.status_code == 200
    assert [item["run_id"] for item in listed.json()["runs"]] == [started["run_id"]]
    pending = client.get("/api/v1/approvals/pending").json()["runs"]
    assert [item["run_id"] for item in pending] == [started["run_id"]]
    health = client.get("/health").json()
    assert health["database"] == {"status": "ready", "dialect": "sqlite"}


def test_injected_artifact_write_failure_rolls_back_every_database_row(tmp_path, monkeypatch) -> None:
    database = _database(tmp_path)
    repository = SqlAlchemyRepository(database)
    repository.create_run("RUN-ROLLBACK", "Rollback", "Test atomic writes", False)
    payload = '{"nodes": {}, "relationships": []}'
    record = ArtifactRecord(
        artifact_id="LIN-001", artifact_type="lineage", version=1,
        run_id="RUN-ROLLBACK", producer_agent="Release Agent",
        checksum_sha256=hashlib.sha256(payload.encode()).hexdigest(),
        relative_path="lin-001.json", media_type="application/json",
    )

    def fail_projection(*_args, **_kwargs):
        raise RuntimeError("injected projection failure")

    monkeypatch.setattr(repository, "_replace_lineage", fail_projection)
    with pytest.raises(RuntimeError, match="injected"):
        repository.save_artifact(record, payload)
    with database.session() as session:
        assert session.scalars(select(ArtifactRow).where(ArtifactRow.run_id == "RUN-ROLLBACK")).all() == []
    assert repository.list_artifacts("RUN-ROLLBACK") == []
