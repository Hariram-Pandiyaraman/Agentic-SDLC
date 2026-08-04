from pathlib import Path

from scripts.run_demo import run_demo
from sdlc.prompts import PROMPTS
from sdlc.services.generation import GenerationResult
from sdlc.services.workflow_runner import WorkflowRunner


class RecordingContractGenerator:
    def __init__(self) -> None:
        self.tasks: list[str] = []

    def generate(self, task, response_model, variables, fallback):
        self.tasks.append(task)
        value = fallback()
        assert isinstance(value, response_model)
        return GenerationResult(
            value=value,
            provider="contract_mock",
            model="mock-structured-model",
            prompt_task=task,
            prompt_version=PROMPTS[task].version,
            attempts=1,
            repair_used=False,
            fallback_used=False,
            latency_ms=1,
            errors=(),
        )


def approve_all(runner: WorkflowRunner, response: dict) -> dict:
    while response["status"] == "waiting_for_approval":
        response = runner.resume(
            response["run_id"],
            {
                "status": "approved",
                "actor": "Contract Test Architect",
                "comment": "Approved",
            },
        )
    return response


def test_all_agent_generation_contracts_are_exercised(tmp_path) -> None:
    generator = RecordingContractGenerator()
    runner = WorkflowRunner(tmp_path / "artifacts", generator=generator)
    response = approve_all(
        runner,
        runner.start(
            "Create a complete traceable delivery package.",
            run_id="RUN-PHASE5-001",
        ),
    )
    assert response["status"] == "completed"
    assert set(generator.tasks) == set(PROMPTS)
    generated_records = [
        item
        for item in runner.store.list_artifacts("RUN-PHASE5-001")
        if item.model_metadata
    ]
    assert generated_records
    assert {
        item.model_metadata["provider"] for item in generated_records
    } == {"contract_mock"}


def test_seeded_demo_qualifies_passing_and_failed_sanity_runs(tmp_path) -> None:
    requirement = Path("examples/sample_requirement.md")
    passing, passing_report = run_demo(
        requirement,
        tmp_path / "passing",
    )
    failed, failed_report = run_demo(
        requirement,
        tmp_path / "failed",
        simulate_failure=True,
    )

    assert passing["status"] == "completed"
    assert passing_report["ready"] is True
    assert failed["status"] == "completed"
    assert failed_report["ready"] is True
    assert failed["state"]["artifact_ids"]["defect"] == ["DEF-001"]
    assert "Open defects: 1" in Path(
        tmp_path / "failed" / failed["run_id"] / "qa-001.md"
    ).read_text(encoding="utf-8")


def test_react_console_contract_is_present() -> None:
    source = Path("frontend/src/main.jsx").read_text(encoding="utf-8")
    styles = Path("frontend/src/styles.css").read_text(encoding="utf-8")
    package = Path("frontend/package.json").read_text(encoding="utf-8")
    assert "function NewRun()" in source
    assert "function ApprovalModal" in source
    assert "function Traceability" in source
    assert "backdrop-filter" in styles
    assert '"react"' in package
