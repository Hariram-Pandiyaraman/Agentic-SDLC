from sdlc.config import Settings
from sdlc.models import (
    CriterionReview,
    GeneratedFile,
    ImplementationOutput,
    MarkdownOutput,
    ReviewOutput,
    TestMapping as MappingModel,
)
from sdlc.prompts import PROMPTS
from sdlc.services.generation import OllamaGenerationService
from sdlc.services.traceability import validate_acceptance_criterion_coverage
from sdlc.services.workflow_runner import WorkflowRunner


def enabled_settings() -> Settings:
    return Settings(use_ollama=True, _env_file=None)


def test_prompt_catalog_covers_all_generation_stages() -> None:
    assert {
        "intake",
        "context_ranking",
        "clarification",
        "brd",
        "stories",
        "planning",
        "code_plan",
        "implementation",
        "review",
        "sanity",
        "release",
    } <= set(PROMPTS)


def test_valid_ollama_structured_response() -> None:
    gateway = OllamaGenerationService(
        enabled_settings(),
        chat_callable=lambda _messages, _schema: '{"markdown":"# Generated BRD"}',
    )
    result = gateway.generate(
        "brd",
        MarkdownOutput,
        {"requirement_id": "REQ-001"},
        lambda: MarkdownOutput(markdown="# Fallback"),
    )
    assert result.value.markdown == "# Generated BRD"
    assert result.provider == "ollama"
    assert result.fallback_used is False
    assert result.attempts == 1


def test_invalid_response_is_repaired_once() -> None:
    responses = iter(
        [
            '{"wrong_field":"invalid"}',
            '{"markdown":"# Repaired BRD"}',
        ]
    )
    gateway = OllamaGenerationService(
        enabled_settings(),
        chat_callable=lambda _messages, _schema: next(responses),
    )
    result = gateway.generate(
        "brd",
        MarkdownOutput,
        {},
        lambda: MarkdownOutput(markdown="# Fallback"),
    )
    assert result.value.markdown == "# Repaired BRD"
    assert result.repair_used is True
    assert result.attempts == 2
    assert result.fallback_used is False


def test_connection_failure_uses_visible_fallback() -> None:
    def unavailable(_messages, _schema) -> str:
        raise ConnectionError("Ollama is offline")

    gateway = OllamaGenerationService(enabled_settings(), chat_callable=unavailable)
    result = gateway.generate(
        "brd",
        MarkdownOutput,
        {},
        lambda: MarkdownOutput(markdown="# Template BRD"),
    )
    assert result.value.markdown == "# Template BRD"
    assert result.provider == "deterministic_template"
    assert result.fallback_used is True
    assert "Ollama is offline" in result.errors[0]


def test_disabled_ollama_workflow_records_fallback_metadata(tmp_path) -> None:
    settings = Settings(use_ollama=False, _env_file=None)
    runner = WorkflowRunner(tmp_path / "artifacts", settings=settings)
    response = runner.start(
        "Create traceable delivery artifacts.",
        run_id="RUN-PHASE3-001",
    )
    assert response["status"] == "waiting_for_approval"
    manifest = runner.store.load_manifest("RUN-PHASE3-001")
    assert manifest.fallback_events
    requirement = manifest.artifacts[0]
    assert requirement.model_metadata["provider"] == "deterministic_template"
    assert requirement.model_metadata["fallback_used"] is True


def test_acceptance_criterion_traceability_is_complete() -> None:
    implementation = ImplementationOutput(
        files=[
            GeneratedFile(
                path="feature.py",
                acceptance_criterion_ids=["AC-001"],
                content="# Implements AC-001\ndef feature(): return True",
            )
        ]
    )
    tests = [
        MappingModel(
            test_case_id="TC-001",
            acceptance_criterion_ids=["AC-001"],
            test_name="test_feature",
            test_type="unit",
        )
    ]
    review = ReviewOutput(
        criterion_reviews=[
            CriterionReview(
                acceptance_criterion_id="AC-001",
                status="covered",
                finding="AC-001 is implemented and tested.",
            )
        ],
        verdict="approved_for_sanity",
    )
    gaps = validate_acceptance_criterion_coverage(
        {"AC-001"},
        implementation,
        tests,
        review,
        "# QA Handoff\n- Acceptance criterion: AC-001",
    )
    assert all(not values for values in gaps.values())
