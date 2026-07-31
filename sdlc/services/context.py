"""Context retrieval through fixtures or Neo4j."""

import re
from pathlib import Path
from typing import Protocol

from sdlc.models.domain import ContextItem, ContextPack, NormalizedRequirement
from sdlc.services.ids import next_artifact_id


class ContextProvider(Protocol):
    def retrieve(self, requirement: NormalizedRequirement, limit: int = 5) -> ContextPack: ...


class FixtureContextProvider:
    def __init__(self, fixture_path: Path | str | None = None) -> None:
        default_path = Path(__file__).resolve().parents[1] / "fixtures" / "context.json"
        self.fixture_path = Path(fixture_path or default_path)

    def retrieve(self, requirement: NormalizedRequirement, limit: int = 5) -> ContextPack:
        raw = self.fixture_path.read_text(encoding="utf-8")
        candidates = ContextPack.model_validate_json(raw).items
        terms = self._terms(f"{requirement.title} {requirement.feature_intent}")
        ranked: list[ContextItem] = []
        for candidate in candidates:
            haystack = self._terms(
                f"{candidate.title} {candidate.summary} {' '.join(candidate.tags)}"
            )
            overlap = len(terms & haystack)
            score = min(1.0, 0.2 + overlap / max(len(terms), 1))
            ranked.append(candidate.model_copy(update={"relevance_score": round(score, 3)}))
        ranked.sort(key=lambda item: item.relevance_score, reverse=True)
        return ContextPack(
            context_pack_id=next_artifact_id("context_pack", []),
            requirement_id=requirement.requirement_id,
            source_artifact_ids=[requirement.requirement_id],
            query_terms=sorted(terms),
            items=ranked[:limit],
            provider="fixture",
        )

    @staticmethod
    def _terms(value: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9]+", value.lower())
            if len(token) > 2
        }


class Neo4jContextProvider:
    QUERY = """
    MATCH (artifact)
    WHERE any(tag IN coalesce(artifact.tags, [])
              WHERE toLower(tag) IN $terms)
       OR any(term IN $terms
              WHERE toLower(coalesce(artifact.title, '')) CONTAINS term
                 OR toLower(coalesce(artifact.summary, '')) CONTAINS term)
    RETURN artifact.artifact_id AS artifact_id,
           coalesce(artifact.artifact_type, head(labels(artifact))) AS artifact_type,
           artifact.title AS title,
           artifact.summary AS summary,
           coalesce(artifact.tags, []) AS tags,
           0.8 AS relevance_score,
           'RELATED_TO' AS relationship
    LIMIT $limit
    """

    def __init__(self, uri: str, username: str, password: str) -> None:
        from neo4j import GraphDatabase

        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self) -> None:
        self.driver.close()

    def retrieve(self, requirement: NormalizedRequirement, limit: int = 5) -> ContextPack:
        terms = sorted(FixtureContextProvider._terms(
            f"{requirement.title} {requirement.feature_intent}"
        ))
        records, _, _ = self.driver.execute_query(
            self.QUERY,
            terms=terms,
            limit=limit,
            routing_="r",
        )
        items = [ContextItem.model_validate(record.data()) for record in records]
        return ContextPack(
            context_pack_id=next_artifact_id("context_pack", []),
            requirement_id=requirement.requirement_id,
            source_artifact_ids=[requirement.requirement_id],
            query_terms=terms,
            items=items,
            provider="neo4j",
        )
