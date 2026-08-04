"""FastAPI entry point for the SDLC Agentic Framework."""

import io
import json
import zipfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse

from api.schemas import CreateRunRequest, ResumeRunRequest
from sdlc import __version__
from sdlc.config import Settings, get_settings
from sdlc.services.health import collect_health
from sdlc.services.workflow_runner import WorkflowRunner


def create_app(
    *,
    settings_override: Settings | None = None,
    runner_override: WorkflowRunner | None = None,
) -> FastAPI:
    settings = settings_override or get_settings()
    runner = runner_override or WorkflowRunner(
        settings.artifact_root,
        settings=settings,
    )
    application = FastAPI(
        title="SDLC Agentic Framework API",
        description="Local API for the agentic SDLC proof of concept.",
        version=__version__,
    )
    application.state.settings = settings
    application.state.runner = runner

    @application.get("/")
    async def root() -> dict[str, str]:
        return {
            "name": application.title,
            "version": __version__,
            "environment": settings.app_env,
            "docs": "/docs",
            "health": "/health",
            "runs": "/api/v1/runs",
        }

    @application.get("/health")
    async def health() -> dict:
        return await collect_health(settings)

    @application.post("/api/v1/runs", status_code=201)
    def create_run(request: CreateRunRequest) -> dict:
        try:
            return runner.start(
                request.raw_requirement,
                title=request.title,
                simulate_test_failure=request.simulate_test_failure,
            )
        except (ValueError, FileExistsError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.get("/api/v1/runs/{run_id}")
    def get_run(run_id: str) -> dict:
        try:
            return runner.inspect(run_id)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @application.post("/api/v1/runs/{run_id}/resume")
    def resume_run(run_id: str, request: ResumeRunRequest) -> dict:
        try:
            runner.store.load_manifest(run_id)
            if request.artifact_id is not None:
                current = runner.inspect(run_id)
                interrupt = next(iter(current["interrupts"]), None)
                expected_id = interrupt and interrupt["value"].get("artifact_id")
                if request.artifact_id != expected_id:
                    raise ValueError(
                        f"approval target changed; expected {expected_id or 'no pending artifact'}"
                    )
                latest = runner.store.get_artifact(run_id, request.artifact_id)
                if request.artifact_version != latest.version:
                    raise ValueError(
                        f"approval target changed; latest version is {latest.version}"
                    )
            decision = request.model_dump(exclude={"artifact_id", "artifact_version"})
            return runner.resume(run_id, decision)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @application.get("/api/v1/runs/{run_id}/artifacts")
    def list_artifacts(run_id: str) -> dict:
        try:
            artifacts = runner.store.list_artifacts(run_id)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "run_id": run_id,
            "artifacts": [
                artifact.model_dump(mode="json") for artifact in artifacts
            ],
        }

    @application.get("/api/v1/runs/{run_id}/artifacts/{artifact_id}")
    def get_artifact(
        run_id: str,
        artifact_id: str,
        version: int | None = None,
    ) -> Response:
        try:
            record = runner.store.get_artifact(run_id, artifact_id, version)
            content = runner.store.read_artifact(run_id, artifact_id, version)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return Response(
            content=content,
            media_type=record.media_type,
            headers={
                "X-Artifact-Id": record.artifact_id,
                "X-Artifact-Version": str(record.version),
            },
        )

    @application.get("/api/v1/runs/{run_id}/lineage")
    def get_lineage(run_id: str) -> dict:
        try:
            records = [
                item
                for item in runner.store.list_artifacts(run_id)
                if item.artifact_type == "lineage"
            ]
            if not records:
                raise FileNotFoundError("lineage is available after workflow completion")
            return json.loads(runner.store.read_artifact(run_id, records[-1].artifact_id))
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @application.get("/api/v1/runs/{run_id}/export")
    def export_run(run_id: str) -> StreamingResponse:
        try:
            run_dir = runner.store.run_directory(run_id)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        archive = _build_archive(run_dir)
        return StreamingResponse(
            archive,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{run_id}.zip"'
            },
        )

    return application


def _build_archive(run_dir: Path) -> io.BytesIO:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(run_dir.rglob("*")):
            if path.is_file() and not path.name.endswith(".tmp"):
                archive.write(path, arcname=path.relative_to(run_dir))
    buffer.seek(0)
    return buffer


app = create_app()
