"""Repository interfaces and transactional SQLAlchemy implementation."""

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator, Protocol

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sdlc.models.artifacts import ArtifactRecord, RunManifest
from sdlc.models.common import ApprovalStatus
from sdlc.persistence.database import Database
from sdlc.persistence.models import (
    ApprovalRow,
    ArtifactRow,
    ArtifactSourceRow,
    ArtifactVersionRow,
    FallbackEventRow,
    LineageEdgeRow,
    LineageNodeRow,
    RunRow,
    WorkflowSnapshotRow,
    WorkflowWriteRow,
)


class RunRepository(Protocol):
    def create_run(self, run_id: str, title: str, raw_requirement: str, simulate_test_failure: bool) -> RunManifest: ...
    def list_runs(self, **filters: Any) -> list[dict]: ...
    def update_run(self, run_id: str, **values: Any) -> None: ...


class ArtifactRepository(Protocol):
    def save_artifact(self, record: ArtifactRecord, content: str) -> None: ...
    def list_artifacts(self, run_id: str) -> list[ArtifactRecord]: ...
    def read_artifact(self, run_id: str, artifact_id: str, version: int | None = None) -> str: ...


class ApprovalRepository(Protocol):
    def list_pending_approvals(self) -> list[dict]: ...


class FallbackRepository(Protocol):
    def record_fallback_event(self, run_id: str, event: dict) -> None: ...


class SnapshotRepository(Protocol):
    def put_snapshot(self, **values: Any) -> None: ...
    def get_snapshot(self, run_id: str, namespace: str, checkpoint_id: str | None = None) -> WorkflowSnapshotRow | None: ...


class LineageRepository(Protocol):
    def read_lineage(self, run_id: str) -> dict: ...


class SqlAlchemyRepository:
    """One vendor-neutral repository boundary with short, atomic transactions."""

    def __init__(self, database: Database) -> None:
        self.database = database

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        session = self.database.session()
        try:
            with session.begin():
                yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_run(
        self,
        run_id: str,
        title: str = "New feature",
        raw_requirement: str = "",
        simulate_test_failure: bool = False,
    ) -> RunManifest:
        now = datetime.now(timezone.utc)
        try:
            with self.transaction() as session:
                session.add(RunRow(
                    run_id=run_id, title=title, raw_requirement=raw_requirement,
                    status="not_started", current_node="start",
                    simulate_test_failure=simulate_test_failure,
                    created_at=now, updated_at=now,
                ))
        except IntegrityError as exc:
            raise FileExistsError(f"run already exists: {run_id}") from exc
        return RunManifest(run_id=run_id, created_at=now, updated_at=now)

    def update_run(self, run_id: str, **values: Any) -> None:
        with self.transaction() as session:
            row = session.get(RunRow, run_id)
            if row is None:
                raise FileNotFoundError(f"run not found: {run_id}")
            for key in ("title", "status", "current_node", "current_gate"):
                if key in values:
                    setattr(row, key, values[key])
            row.updated_at = datetime.now(timezone.utc)

    def load_manifest(self, run_id: str) -> RunManifest:
        with self.database.session() as session:
            run = session.get(RunRow, run_id)
            if run is None:
                raise FileNotFoundError(f"run manifest not found: {run_id}")
            artifacts = self._artifact_records(session, run_id)
            events = session.scalars(
                select(FallbackEventRow).where(FallbackEventRow.run_id == run_id).order_by(FallbackEventRow.sequence)
            ).all()
            return RunManifest(
                run_id=run_id, created_at=run.created_at, updated_at=run.updated_at,
                artifacts=artifacts,
                fallback_events=[json.loads(item.event_json) for item in events],
            )

    def list_artifacts(self, run_id: str) -> list[ArtifactRecord]:
        return self.load_manifest(run_id).artifacts

    def get_artifact(self, run_id: str, artifact_id: str, version: int | None = None) -> ArtifactRecord:
        matches = [
            item for item in self.list_artifacts(run_id)
            if item.artifact_id == artifact_id and (version is None or item.version == version)
        ]
        if not matches:
            suffix = f" version {version}" if version is not None else ""
            raise FileNotFoundError(f"artifact not found: {artifact_id}{suffix}")
        return max(matches, key=lambda item: item.version)

    def save_artifact(self, record: ArtifactRecord, content: str) -> None:
        with self.transaction() as session:
            run = session.get(RunRow, record.run_id)
            if run is None:
                raise FileNotFoundError(f"run not found: {record.run_id}")
            artifact = session.scalar(select(ArtifactRow).where(
                ArtifactRow.run_id == record.run_id,
                ArtifactRow.artifact_id == record.artifact_id,
            ))
            if artifact is None:
                artifact = ArtifactRow(run_id=record.run_id, artifact_id=record.artifact_id, artifact_type=record.artifact_type)
                session.add(artifact)
                session.flush()
            latest = session.scalar(select(func.max(ArtifactVersionRow.version)).where(ArtifactVersionRow.artifact_pk == artifact.id)) or 0
            if record.version != latest + 1:
                raise ValueError(f"artifact version must be {latest + 1}, got {record.version}")
            sources = session.scalars(select(ArtifactRow).where(
                ArtifactRow.run_id == record.run_id,
                ArtifactRow.artifact_id.in_(record.source_artifact_ids or ["__none__"]),
            )).all()
            found = {item.artifact_id for item in sources}
            missing = [item for item in record.source_artifact_ids if item not in found]
            if missing:
                raise ValueError(f"source artifacts are not present in the run: {missing}")
            version = ArtifactVersionRow(
                artifact_pk=artifact.id, version=record.version, content=content,
                producer_agent=record.producer_agent, created_at=record.created_at,
                approval_status=str(record.approval_status.value),
                model_metadata_json=json.dumps(record.model_metadata, default=str),
                confidence=record.confidence, checksum_sha256=record.checksum_sha256,
                relative_path=record.relative_path, media_type=record.media_type,
            )
            session.add(version)
            session.flush()
            session.add_all(ArtifactSourceRow(target_version_id=version.id, source_artifact_pk=item.id) for item in sources)
            if record.artifact_type == "approval":
                self._add_approval(session, record.run_id, record.artifact_id, content)
            if record.artifact_type == "lineage":
                self._replace_lineage(session, record.run_id, json.loads(content))
            run.updated_at = datetime.now(timezone.utc)

    def read_artifact(self, run_id: str, artifact_id: str, version: int | None = None) -> str:
        with self.database.session() as session:
            query = select(ArtifactVersionRow.content).join(ArtifactRow).where(
                ArtifactRow.run_id == run_id, ArtifactRow.artifact_id == artifact_id,
            )
            if version is not None:
                query = query.where(ArtifactVersionRow.version == version)
            else:
                query = query.order_by(ArtifactVersionRow.version.desc())
            content = session.scalar(query.limit(1))
            if content is None:
                raise FileNotFoundError(f"artifact not found: {artifact_id}")
            return content

    def record_fallback_event(self, run_id: str, event: dict[str, Any]) -> None:
        with self.transaction() as session:
            run = session.get(RunRow, run_id)
            if run is None:
                raise FileNotFoundError(f"run not found: {run_id}")
            sequence = (session.scalar(select(func.max(FallbackEventRow.sequence)).where(FallbackEventRow.run_id == run_id)) or 0) + 1
            session.add(FallbackEventRow(run_id=run_id, sequence=sequence, event_json=json.dumps(event, default=str)))
            run.updated_at = datetime.now(timezone.utc)

    def list_runs(
        self,
        *,
        query: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        with self.database.session() as session:
            statement = select(RunRow).order_by(RunRow.updated_at.desc()).limit(limit)
            if query:
                pattern = f"%{query.lower()}%"
                statement = statement.where(func.lower(RunRow.title).like(pattern) | func.lower(RunRow.run_id).like(pattern))
            if status:
                statement = statement.where(RunRow.status == status)
            if date_from:
                statement = statement.where(RunRow.updated_at >= date_from)
            if date_to:
                statement = statement.where(RunRow.updated_at <= date_to)
            rows = session.scalars(statement).all()
            result = []
            for row in rows:
                fallback_count = session.scalar(select(func.count()).select_from(FallbackEventRow).where(FallbackEventRow.run_id == row.run_id)) or 0
                artifact_count = session.scalar(select(func.count()).select_from(ArtifactVersionRow).join(ArtifactRow).where(ArtifactRow.run_id == row.run_id)) or 0
                result.append({
                    "run_id": row.run_id, "title": row.title, "status": row.status,
                    "current_node": row.current_node, "current_gate": row.current_gate,
                    "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat(),
                    "fallback_count": fallback_count, "artifact_count": artifact_count,
                })
            return result

    def list_pending_approvals(self) -> list[dict]:
        return [item for item in self.list_runs(status="waiting_for_approval")]

    def read_lineage(self, run_id: str) -> dict:
        with self.database.session() as session:
            nodes = session.scalars(select(LineageNodeRow).where(LineageNodeRow.run_id == run_id)).all()
            edges = session.scalars(select(LineageEdgeRow).where(LineageEdgeRow.run_id == run_id)).all()
            by_pk = {item.id: item.artifact_id for item in nodes}
            return {
                "nodes": {item.artifact_id: {"artifact_id": item.artifact_id, "artifact_type": item.artifact_type, "version": item.version, **json.loads(item.properties_json)} for item in nodes},
                "relationships": [{"source_id": by_pk[item.source_node_id], "relationship": item.relationship, "target_id": by_pk[item.target_node_id], "properties": json.loads(item.properties_json)} for item in edges],
            }

    def _artifact_records(self, session: Session, run_id: str) -> list[ArtifactRecord]:
        rows = session.execute(select(ArtifactVersionRow, ArtifactRow).join(ArtifactRow).where(ArtifactRow.run_id == run_id).order_by(ArtifactVersionRow.id)).all()
        result = []
        for version, artifact in rows:
            source_ids = session.scalars(select(ArtifactRow.artifact_id).join(ArtifactSourceRow, ArtifactSourceRow.source_artifact_pk == ArtifactRow.id).where(ArtifactSourceRow.target_version_id == version.id)).all()
            result.append(ArtifactRecord(
                artifact_id=artifact.artifact_id, artifact_type=artifact.artifact_type,
                version=version.version, run_id=run_id, source_artifact_ids=list(source_ids),
                producer_agent=version.producer_agent, created_at=version.created_at,
                approval_status=ApprovalStatus(version.approval_status),
                model_metadata=json.loads(version.model_metadata_json), confidence=version.confidence,
                checksum_sha256=version.checksum_sha256, relative_path=version.relative_path,
                media_type=version.media_type,
            ))
        return result

    @staticmethod
    def _add_approval(session: Session, run_id: str, approval_id: str, content: str) -> None:
        data = json.loads(content)
        target = session.scalar(select(ArtifactVersionRow).join(ArtifactRow).where(
            ArtifactRow.run_id == run_id, ArtifactRow.artifact_id == data["artifact_id"]
        ).order_by(ArtifactVersionRow.version.desc()).limit(1))
        if target is None:
            raise ValueError("approval target artifact version is missing")
        session.add(ApprovalRow(
            approval_id=approval_id, run_id=run_id, gate=data["gate"], status=data["status"],
            artifact_version_id=target.id, actor=data["actor"], comment=data.get("comment"),
            decided_at=datetime.fromisoformat(data["decided_at"].replace("Z", "+00:00")),
        ))

    @staticmethod
    def _replace_lineage(session: Session, run_id: str, graph: dict) -> None:
        session.query(LineageEdgeRow).filter_by(run_id=run_id).delete()
        session.query(LineageNodeRow).filter_by(run_id=run_id).delete()
        session.flush()
        nodes: dict[str, LineageNodeRow] = {}
        for artifact_id, data in graph.get("nodes", {}).items():
            node = LineageNodeRow(
                run_id=run_id, artifact_id=artifact_id,
                artifact_type=data.get("artifact_type", "artifact"), version=data.get("version", 1),
                properties_json=json.dumps({key: value for key, value in data.items() if key not in {"artifact_id", "artifact_type", "version"}}, default=str),
            )
            session.add(node)
            nodes[artifact_id] = node
        session.flush()
        for edge in graph.get("relationships", []):
            session.add(LineageEdgeRow(
                run_id=run_id, source_node_id=nodes[edge["source_id"]].id,
                relationship=edge["relationship"], target_node_id=nodes[edge["target_id"]].id,
                properties_json=json.dumps(edge.get("properties", {}), default=str),
            ))

    # Checkpoint operations are intentionally low-level for the LangGraph adapter.
    def put_snapshot(self, **values: Any) -> None:
        with self.transaction() as session:
            existing = session.scalar(select(WorkflowSnapshotRow).where(
                WorkflowSnapshotRow.run_id == values["run_id"],
                WorkflowSnapshotRow.checkpoint_ns == values["checkpoint_ns"],
                WorkflowSnapshotRow.checkpoint_id == values["checkpoint_id"],
            ))
            if existing:
                for key, value in values.items():
                    if key not in {"run_id", "checkpoint_ns", "checkpoint_id", "sequence"}:
                        setattr(existing, key, value)
            else:
                session.add(WorkflowSnapshotRow(**values))

    def next_snapshot_sequence(self, run_id: str, namespace: str) -> int:
        with self.database.session() as session:
            return (session.scalar(select(func.max(WorkflowSnapshotRow.sequence)).where(
                WorkflowSnapshotRow.run_id == run_id,
                WorkflowSnapshotRow.checkpoint_ns == namespace,
            )) or 0) + 1

    def get_snapshot(self, run_id: str, namespace: str, checkpoint_id: str | None = None) -> WorkflowSnapshotRow | None:
        with self.database.session() as session:
            statement = select(WorkflowSnapshotRow).where(
                WorkflowSnapshotRow.run_id == run_id,
                WorkflowSnapshotRow.checkpoint_ns == namespace,
            )
            if checkpoint_id:
                statement = statement.where(WorkflowSnapshotRow.checkpoint_id == checkpoint_id)
            else:
                statement = statement.order_by(WorkflowSnapshotRow.sequence.desc())
            row = session.scalar(statement.limit(1))
            if row is not None:
                session.expunge(row)
            return row

    def list_snapshots(self, run_id: str | None = None, namespace: str | None = None) -> list[WorkflowSnapshotRow]:
        with self.database.session() as session:
            statement = select(WorkflowSnapshotRow).order_by(WorkflowSnapshotRow.sequence.desc())
            if run_id is not None:
                statement = statement.where(WorkflowSnapshotRow.run_id == run_id)
            if namespace is not None:
                statement = statement.where(WorkflowSnapshotRow.checkpoint_ns == namespace)
            rows = list(session.scalars(statement).all())
            for row in rows:
                session.expunge(row)
            return rows

    def delete_snapshots(self, run_id: str) -> None:
        with self.transaction() as session:
            session.query(WorkflowWriteRow).filter_by(run_id=run_id).delete()
            session.query(WorkflowSnapshotRow).filter_by(run_id=run_id).delete()

    def put_checkpoint_writes(self, rows: list[dict[str, Any]]) -> None:
        with self.transaction() as session:
            for values in rows:
                existing = session.scalar(select(WorkflowWriteRow).where(
                    WorkflowWriteRow.run_id == values["run_id"],
                    WorkflowWriteRow.checkpoint_ns == values["checkpoint_ns"],
                    WorkflowWriteRow.checkpoint_id == values["checkpoint_id"],
                    WorkflowWriteRow.task_id == values["task_id"],
                    WorkflowWriteRow.write_index == values["write_index"],
                ))
                if existing is None or values["write_index"] < 0:
                    if existing is not None:
                        session.delete(existing)
                        session.flush()
                    session.add(WorkflowWriteRow(**values))

    def get_checkpoint_writes(self, run_id: str, namespace: str, checkpoint_id: str) -> list[WorkflowWriteRow]:
        with self.database.session() as session:
            rows = list(session.scalars(select(WorkflowWriteRow).where(
                WorkflowWriteRow.run_id == run_id,
                WorkflowWriteRow.checkpoint_ns == namespace,
                WorkflowWriteRow.checkpoint_id == checkpoint_id,
            ).order_by(WorkflowWriteRow.id)).all())
            for row in rows:
                session.expunge(row)
            return rows
