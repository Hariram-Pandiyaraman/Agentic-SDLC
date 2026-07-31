"""Artifact manifest contracts."""

from datetime import datetime

from pydantic import Field

from sdlc.models.common import ApprovalStatus, StrictModel, utc_now


class ArtifactRecord(StrictModel):
    artifact_id: str
    artifact_type: str
    version: int = Field(default=1, ge=1)
    run_id: str
    source_artifact_ids: list[str] = Field(default_factory=list)
    producer_agent: str
    created_at: datetime = Field(default_factory=utc_now)
    approval_status: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    model_metadata: dict = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0, le=1)
    checksum_sha256: str
    relative_path: str
    media_type: str


class RunManifest(StrictModel):
    run_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    fallback_events: list[dict] = Field(default_factory=list)

