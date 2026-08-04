"""Start, inspect, and resume checkpointed workflow runs."""

from pathlib import Path

from langgraph.types import Command

from sdlc.config import Settings, get_settings
from sdlc.graph.workflow import build_workflow
from sdlc.models import GateDecision
from sdlc.services.artifact_store import ArtifactStore
from sdlc.services.generation import OllamaGenerationService
from sdlc.services.ids import new_run_id
from sdlc.persistence import Database, SqlAlchemyRepository
from sdlc.persistence.checkpoint import SqlAlchemyCheckpointSaver


class WorkflowRunner:
    def __init__(
        self,
        artifact_root: Path | str,
        *,
        settings: Settings | None = None,
        generator: OllamaGenerationService | None = None,
        database: Database | None = None,
    ) -> None:
        resolved_settings = settings or get_settings()
        if database is None:
            if resolved_settings.database_url:
                database_url = resolved_settings.database_url
            else:
                database_path = (Path(artifact_root).resolve().parent / "data" / "agentic-sdlc.db")
                database_url = f"sqlite:///{database_path.as_posix()}"
            database = Database(database_url)
        self.database = database
        self.repository = SqlAlchemyRepository(database)
        self.store = ArtifactStore(artifact_root, self.repository)
        self.checkpointer = SqlAlchemyCheckpointSaver(self.repository)
        self.generator = generator or OllamaGenerationService(resolved_settings)
        self.graph = build_workflow(
            self.store,
            self.checkpointer,
            self.generator,
        )

    def start(
        self,
        raw_requirement: str,
        *,
        title: str = "New feature",
        run_id: str | None = None,
        simulate_test_failure: bool = False,
    ) -> dict:
        resolved_run_id = run_id or new_run_id()
        self.store.create_run(
            resolved_run_id,
            title=title,
            raw_requirement=raw_requirement,
            simulate_test_failure=simulate_test_failure,
        )
        initial_state = {
            "run_id": resolved_run_id,
            "raw_requirement": raw_requirement,
            "requirement_title": title,
            "simulate_test_failure": simulate_test_failure,
            "status": "running",
            "current_node": "start",
            "artifact_ids": {},
            "agent_results": [],
            "approvals": [],
            "errors": [],
            "fallback_events": [],
        }
        result = self.graph.invoke(initial_state, config=self._config(resolved_run_id))
        response = self._response(resolved_run_id, result)
        self._sync_run(response)
        return response

    def resume(self, run_id: str, decision: GateDecision | dict) -> dict:
        validated = (
            decision
            if isinstance(decision, GateDecision)
            else GateDecision.model_validate(decision)
        )
        result = self.graph.invoke(
            Command(resume=validated.model_dump(mode="json")),
            config=self._config(run_id),
        )
        response = self._response(run_id, result)
        self._sync_run(response)
        return response

    def inspect(self, run_id: str) -> dict:
        self.store.load_manifest(run_id)
        snapshot = self.graph.get_state(self._config(run_id))
        interrupts = [
            {"id": item.id, "value": item.value}
            for task in snapshot.tasks
            for item in getattr(task, "interrupts", ())
        ]
        state = snapshot.values
        return {
            "run_id": run_id,
            "status": (
                "waiting_for_approval"
                if interrupts
                else state.get("status", "not_started")
            ),
            "interrupts": interrupts,
            "state": state,
            "next": list(snapshot.next),
            "artifacts": [
                artifact.model_dump(mode="json")
                for artifact in self.store.list_artifacts(run_id)
            ],
        }

    @staticmethod
    def _config(run_id: str) -> dict:
        return {"configurable": {"thread_id": run_id}}

    def _response(self, run_id: str, result: dict) -> dict:
        interrupts = result.get("__interrupt__", ())
        return {
            "run_id": run_id,
            "status": "waiting_for_approval" if interrupts else result.get("status"),
            "interrupts": [
                {
                    "id": item.id,
                    "value": item.value,
                }
                for item in interrupts
            ],
            "state": {key: value for key, value in result.items() if key != "__interrupt__"},
        }

    def _sync_run(self, response: dict) -> None:
        interrupt = next(iter(response.get("interrupts", [])), None)
        state = response.get("state", {})
        self.repository.update_run(
            response["run_id"],
            title=state.get("requirement_title", "New feature"),
            status=response.get("status", state.get("status", "running")),
            current_node=state.get("current_node", "start"),
            current_gate=interrupt["value"].get("gate") if interrupt else None,
        )
