"""Filesystem artifact persistence with an authoritative per-run manifest."""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from sdlc.models.artifacts import ArtifactRecord, RunManifest
from sdlc.models.common import ApprovalStatus, utc_now
from sdlc.services.ids import new_run_id, next_artifact_id, validate_safe_id


class ArtifactStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def create_run(self, run_id: str | None = None) -> RunManifest:
        resolved_run_id = validate_safe_id(run_id or new_run_id(), "run_id")
        run_dir = self._run_dir(resolved_run_id)
        run_dir.mkdir(parents=True, exist_ok=False)
        manifest = RunManifest(run_id=resolved_run_id)
        self._write_manifest(manifest)
        return manifest

    def load_manifest(self, run_id: str) -> RunManifest:
        path = self._manifest_path(run_id)
        if not path.exists():
            raise FileNotFoundError(f"run manifest not found: {run_id}")
        return RunManifest.model_validate_json(path.read_text(encoding="utf-8"))

    def list_artifacts(self, run_id: str) -> list[ArtifactRecord]:
        return self.load_manifest(run_id).artifacts

    def get_artifact(
        self,
        run_id: str,
        artifact_id: str,
        version: int | None = None,
    ) -> ArtifactRecord:
        return self._find_artifact(run_id, artifact_id, version)

    def run_directory(self, run_id: str) -> Path:
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            raise FileNotFoundError(f"run not found: {run_id}")
        return run_dir

    def record_fallback_event(self, run_id: str, event: dict[str, Any]) -> None:
        manifest = self.load_manifest(run_id)
        manifest.fallback_events.append(event)
        manifest.updated_at = utc_now()
        self._write_manifest(manifest)

    def read_artifact(
        self,
        run_id: str,
        artifact_id: str,
        version: int | None = None,
    ) -> str:
        record = self._find_artifact(run_id, artifact_id, version)
        return (self._run_dir(run_id) / record.relative_path).read_text(encoding="utf-8")

    def save_artifact(
        self,
        run_id: str,
        artifact_type: str,
        content: BaseModel | dict | list | str,
        producer_agent: str,
        *,
        source_artifact_ids: list[str] | None = None,
        artifact_id: str | None = None,
        approval_status: ApprovalStatus = ApprovalStatus.NOT_REQUIRED,
        model_metadata: dict | None = None,
        confidence: float | None = None,
    ) -> ArtifactRecord:
        manifest = self.load_manifest(run_id)
        existing_ids = [item.artifact_id for item in manifest.artifacts]
        resolved_id = validate_safe_id(
            artifact_id or next_artifact_id(artifact_type, existing_ids),
            "artifact_id",
        )

        sources = source_artifact_ids or []
        missing_sources = [source for source in sources if source not in existing_ids]
        if missing_sources:
            raise ValueError(f"source artifacts are not present in the run: {missing_sources}")

        payload, extension, media_type = self._serialize(content)
        version = (
            max(
                (
                    record.version
                    for record in manifest.artifacts
                    if record.artifact_id == resolved_id
                ),
                default=0,
            )
            + 1
        )
        version_suffix = "" if version == 1 else f"-v{version}"
        relative_path = f"{resolved_id.lower()}{version_suffix}.{extension}"
        record = ArtifactRecord(
            artifact_id=resolved_id,
            artifact_type=artifact_type,
            version=version,
            run_id=run_id,
            source_artifact_ids=sources,
            producer_agent=producer_agent,
            approval_status=approval_status,
            model_metadata=model_metadata or {},
            confidence=confidence,
            checksum_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            relative_path=relative_path,
            media_type=media_type,
        )

        self._atomic_write(self._run_dir(run_id) / relative_path, payload)
        manifest.artifacts.append(record)
        manifest.updated_at = utc_now()
        self._write_manifest(manifest)
        return record

    def _find_artifact(
        self,
        run_id: str,
        artifact_id: str,
        version: int | None = None,
    ) -> ArtifactRecord:
        matches = [
            record
            for record in self.load_manifest(run_id).artifacts
            if record.artifact_id == artifact_id
            and (version is None or record.version == version)
        ]
        if matches:
            return max(matches, key=lambda record: record.version)
        version_text = f" version {version}" if version is not None else ""
        raise FileNotFoundError(f"artifact not found: {artifact_id}{version_text}")

    def _run_dir(self, run_id: str) -> Path:
        validate_safe_id(run_id, "run_id")
        return self.root / run_id

    def _manifest_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "manifest.json"

    def _write_manifest(self, manifest: RunManifest) -> None:
        self._atomic_write(
            self._manifest_path(manifest.run_id),
            manifest.model_dump_json(indent=2),
        )

    @staticmethod
    def _serialize(content: BaseModel | dict | list | str) -> tuple[str, str, str]:
        if isinstance(content, BaseModel):
            return content.model_dump_json(indent=2), "json", "application/json"
        if isinstance(content, (dict, list)):
            return json.dumps(content, indent=2, default=str), "json", "application/json"
        return content, "md", "text/markdown"

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        temporary.write_text(content, encoding="utf-8")
        try:
            for attempt in range(8):
                try:
                    os.replace(temporary, path)
                    return
                except PermissionError:
                    if attempt == 7:
                        raise
                    time.sleep(0.05 * (attempt + 1))
        finally:
            temporary.unlink(missing_ok=True)
