import json

import pytest

from sdlc.models import NormalizedRequirement
from sdlc.services.artifact_store import ArtifactStore
from sdlc.services.context import FixtureContextProvider
from sdlc.services.ids import next_artifact_id
from sdlc.services.lineage import JsonLineageStore


@pytest.fixture
def requirement() -> NormalizedRequirement:
    payload = json.loads(
        open("tests/fixtures/sample_requirement.json", encoding="utf-8").read()
    )
    return NormalizedRequirement.model_validate(payload)


def test_sample_normalized_requirement_validates(requirement: NormalizedRequirement) -> None:
    assert requirement.requirement_id == "REQ-001"
    assert requirement.actors[0].role == "Approver"


def test_stable_artifact_id_sequence() -> None:
    assert next_artifact_id("requirement", []) == "REQ-001"
    assert next_artifact_id("requirement", ["REQ-001", "REQ-003"]) == "REQ-004"


def test_artifact_is_saved_listed_and_linked(tmp_path, requirement) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    store.create_run("RUN-TEST-001")

    requirement_record = store.save_artifact(
        "RUN-TEST-001",
        "requirement",
        requirement,
        "Intake Agent",
    )
    context_record = store.save_artifact(
        "RUN-TEST-001",
        "context_pack",
        {"items": []},
        "Context Agent",
        source_artifact_ids=[requirement_record.artifact_id],
    )

    artifacts = store.list_artifacts("RUN-TEST-001")
    assert [item.artifact_id for item in artifacts] == ["REQ-001", "CTX-001"]
    assert context_record.source_artifact_ids == ["REQ-001"]
    assert json.loads(store.read_artifact("RUN-TEST-001", "REQ-001"))[
        "requirement_id"
    ] == "REQ-001"


def test_artifact_rejects_unknown_source(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    store.create_run("RUN-TEST-002")
    with pytest.raises(ValueError, match="source artifacts"):
        store.save_artifact(
            "RUN-TEST-002",
            "brd",
            "# BRD",
            "BRD Agent",
            source_artifact_ids=["REQ-404"],
        )


def test_artifact_revision_increments_only_its_own_version(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    store.create_run("RUN-TEST-003")
    first = store.save_artifact(
        "RUN-TEST-003", "brd", "# BRD v1", "BRD Agent", artifact_id="BRD-001"
    )
    other = store.save_artifact(
        "RUN-TEST-003", "brd", "# Another BRD", "BRD Agent", artifact_id="BRD-002"
    )
    revision = store.save_artifact(
        "RUN-TEST-003", "brd", "# BRD v2", "BRD Agent", artifact_id="BRD-001"
    )

    assert first.version == 1
    assert other.version == 1
    assert revision.version == 2
    assert store.read_artifact("RUN-TEST-003", "BRD-001") == "# BRD v2"


def test_fixture_context_retrieval(requirement) -> None:
    result = FixtureContextProvider().retrieve(requirement)
    assert result.provider == "fixture"
    assert result.requirement_id == "REQ-001"
    assert result.items
    assert result.items[0].relevance_score >= result.items[-1].relevance_score


def test_json_lineage_store(tmp_path) -> None:
    store = JsonLineageStore(tmp_path / "lineage.json")
    store.upsert_node("REQ-001", "Requirement", {"title": "Feature"})
    store.upsert_node("BRD-001", "BRD")
    store.add_relationship("REQ-001", "DERIVED_FROM", "BRD-001")

    graph = store.read()
    assert len(graph["nodes"]) == 2
    assert graph["relationships"][0]["relationship"] == "DERIVED_FROM"
