"""Run the full deterministic workflow and approve each gate automatically."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sdlc.config import Settings
from sdlc.services.handoff_validation import validate_run_handoff
from sdlc.services.workflow_runner import WorkflowRunner


def run_demo(
    requirement_path: Path,
    artifact_root: Path,
    *,
    simulate_failure: bool = False,
) -> tuple[dict, dict]:
    requirement = requirement_path.read_text(encoding="utf-8")
    settings = Settings(
        artifact_root=artifact_root,
        use_fixture_context=True,
        enable_template_fallbacks=True,
        _env_file=None,
    )
    runner = WorkflowRunner(artifact_root, settings=settings)
    response = runner.start(
        requirement,
        title="Approval-Controlled QA Handoff Export",
        simulate_test_failure=simulate_failure,
    )
    while response["status"] == "waiting_for_approval":
        gate = response["interrupts"][0]["value"]["gate"]
        print(f"Approving {gate} gate...")
        response = runner.resume(
            response["run_id"],
            {
                "status": "approved",
                "actor": "Demo Architect",
                "comment": "Approved by automated offline demo.",
            },
        )
    report = validate_run_handoff(runner.store, response["run_id"])
    return response, report.model_dump(mode="json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--requirement",
        type=Path,
        default=Path("examples/sample_requirement.md"),
    )
    parser.add_argument("--artifact-root", type=Path, default=Path("artifacts"))
    parser.add_argument("--simulate-failure", action="store_true")
    args = parser.parse_args()

    response, report = run_demo(
        args.requirement,
        args.artifact_root,
        simulate_failure=args.simulate_failure,
    )
    print(f"Run: {response['run_id']}")
    print(f"Status: {response['status']}")
    print(f"QA handoff: {response['state']['artifact_ids']['qa_handoff'][-1]}")
    print(f"Handoff ready: {report['ready']}")
    if report["findings"]:
        print("Findings:")
        for finding in report["findings"]:
            print(f"- {finding}")
    return 0 if response["status"] == "completed" and report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
