"""Portable SQLAlchemy 2.x relational model."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class RunRow(Base):
    __tablename__ = "runs"
    run_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    raw_requirement: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), index=True)
    current_node: Mapped[str] = mapped_column(String(100), default="start")
    current_gate: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    simulate_test_failure: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    artifacts: Mapped[list["ArtifactRow"]] = relationship(cascade="all, delete-orphan", back_populates="run")
    __table_args__ = (CheckConstraint("status <> ''", name="ck_runs_status_nonempty"),)


class ArtifactRow(Base):
    __tablename__ = "artifacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id", ondelete="CASCADE"), index=True)
    artifact_id: Mapped[str] = mapped_column(String(100))
    artifact_type: Mapped[str] = mapped_column(String(60), index=True)
    run: Mapped[RunRow] = relationship(back_populates="artifacts")
    versions: Mapped[list["ArtifactVersionRow"]] = relationship(cascade="all, delete-orphan", back_populates="artifact")
    __table_args__ = (UniqueConstraint("run_id", "artifact_id", name="uq_artifact_run_id"),)


class ArtifactVersionRow(Base):
    __tablename__ = "artifact_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artifact_pk: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    producer_agent: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    approval_status: Mapped[str] = mapped_column(String(30))
    model_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    relative_path: Mapped[str] = mapped_column(String(300))
    media_type: Mapped[str] = mapped_column(String(100))
    artifact: Mapped[ArtifactRow] = relationship(back_populates="versions")
    __table_args__ = (
        UniqueConstraint("artifact_pk", "version", name="uq_artifact_version"),
        CheckConstraint("version > 0", name="ck_artifact_version_positive"),
    )


class ArtifactSourceRow(Base):
    __tablename__ = "artifact_sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_version_id: Mapped[int] = mapped_column(ForeignKey("artifact_versions.id", ondelete="CASCADE"), index=True)
    source_artifact_pk: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="RESTRICT"), index=True)
    __table_args__ = (UniqueConstraint("target_version_id", "source_artifact_pk", name="uq_artifact_source"),)


class ApprovalRow(Base):
    __tablename__ = "approvals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    approval_id: Mapped[str] = mapped_column(String(100))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id", ondelete="CASCADE"), index=True)
    gate: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(30))
    artifact_version_id: Mapped[int] = mapped_column(ForeignKey("artifact_versions.id", ondelete="RESTRICT"))
    actor: Mapped[str] = mapped_column(String(200))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (UniqueConstraint("run_id", "approval_id", name="uq_approval_run_id"),)


class FallbackEventRow(Base):
    __tablename__ = "fallback_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (UniqueConstraint("run_id", "sequence", name="uq_fallback_sequence"),)


class WorkflowSnapshotRow(Base):
    __tablename__ = "workflow_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id", ondelete="CASCADE"), index=True)
    checkpoint_ns: Mapped[str] = mapped_column(String(200), default="")
    checkpoint_id: Mapped[str] = mapped_column(String(100))
    parent_checkpoint_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer)
    checkpoint_type: Mapped[str] = mapped_column(String(30))
    checkpoint_blob: Mapped[bytes] = mapped_column(LargeBinary)
    metadata_type: Mapped[str] = mapped_column(String(30))
    metadata_blob: Mapped[bytes] = mapped_column(LargeBinary)
    writes_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    writes_blob: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (
        UniqueConstraint("run_id", "checkpoint_ns", "checkpoint_id", name="uq_workflow_checkpoint"),
        UniqueConstraint("run_id", "checkpoint_ns", "sequence", name="uq_workflow_sequence"),
    )


class WorkflowWriteRow(Base):
    __tablename__ = "workflow_writes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id", ondelete="CASCADE"), index=True)
    checkpoint_ns: Mapped[str] = mapped_column(String(200), default="")
    checkpoint_id: Mapped[str] = mapped_column(String(100), index=True)
    task_id: Mapped[str] = mapped_column(String(100))
    write_index: Mapped[int] = mapped_column(Integer)
    channel: Mapped[str] = mapped_column(String(200))
    value_type: Mapped[str] = mapped_column(String(30))
    value_blob: Mapped[bytes] = mapped_column(LargeBinary)
    task_path: Mapped[str] = mapped_column(String(500), default="")
    __table_args__ = (
        UniqueConstraint("run_id", "checkpoint_ns", "checkpoint_id", "task_id", "write_index", name="uq_workflow_write"),
    )


class LineageNodeRow(Base):
    __tablename__ = "lineage_nodes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id", ondelete="CASCADE"), index=True)
    artifact_id: Mapped[str] = mapped_column(String(100))
    artifact_type: Mapped[str] = mapped_column(String(60))
    version: Mapped[int] = mapped_column(Integer, default=1)
    properties_json: Mapped[str] = mapped_column(Text, default="{}")
    __table_args__ = (UniqueConstraint("run_id", "artifact_id", name="uq_lineage_node"),)


class LineageEdgeRow(Base):
    __tablename__ = "lineage_edges"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id", ondelete="CASCADE"), index=True)
    source_node_id: Mapped[int] = mapped_column(ForeignKey("lineage_nodes.id", ondelete="CASCADE"))
    relationship: Mapped[str] = mapped_column(String(50))
    target_node_id: Mapped[int] = mapped_column(ForeignKey("lineage_nodes.id", ondelete="CASCADE"))
    properties_json: Mapped[str] = mapped_column(Text, default="{}")
    __table_args__ = (UniqueConstraint("run_id", "source_node_id", "relationship", "target_node_id", name="uq_lineage_edge"),)


class SchemaMetadataRow(Base):
    __tablename__ = "schema_metadata"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


Index("ix_runs_dashboard", RunRow.status, RunRow.updated_at)
