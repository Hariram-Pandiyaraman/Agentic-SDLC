"""Local JSON and optional Neo4j lineage persistence."""

import json
import os
import time
from pathlib import Path
from uuid import uuid4

ALLOWED_RELATIONSHIPS = {
    "DERIVED_FROM",
    "CLARIFIED_BY",
    "APPROVED_BY",
    "DECOMPOSED_INTO",
    "SATISFIES",
    "IMPLEMENTED_BY",
    "VERIFIED_BY",
    "RESULTED_IN",
    "BLOCKED_BY",
    "PACKAGED_IN",
    "RELATED_TO",
}


class JsonLineageStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def upsert_node(self, artifact_id: str, artifact_type: str, properties: dict | None = None) -> None:
        graph = self._load()
        graph["nodes"][artifact_id] = {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            **(properties or {}),
        }
        self._save(graph)

    def add_relationship(
        self,
        source_id: str,
        relationship: str,
        target_id: str,
        properties: dict | None = None,
    ) -> None:
        if relationship not in ALLOWED_RELATIONSHIPS:
            raise ValueError(f"unsupported relationship: {relationship}")
        graph = self._load()
        if source_id not in graph["nodes"] or target_id not in graph["nodes"]:
            raise ValueError("both lineage nodes must exist before linking them")
        edge = {
            "source_id": source_id,
            "relationship": relationship,
            "target_id": target_id,
            "properties": properties or {},
        }
        if edge not in graph["relationships"]:
            graph["relationships"].append(edge)
        self._save(graph)

    def read(self) -> dict:
        return self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"nodes": {}, "relationships": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, graph: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(
            f".{self.path.name}.{uuid4().hex}.tmp"
        )
        temporary.write_text(json.dumps(graph, indent=2), encoding="utf-8")
        try:
            for attempt in range(5):
                try:
                    os.replace(temporary, self.path)
                    return
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.02 * (attempt + 1))
        finally:
            temporary.unlink(missing_ok=True)


class Neo4jLineageStore:
    def __init__(self, uri: str, username: str, password: str) -> None:
        from neo4j import GraphDatabase

        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self) -> None:
        self.driver.close()

    def upsert_node(self, artifact_id: str, artifact_type: str, properties: dict | None = None) -> None:
        self.driver.execute_query(
            """
            MERGE (artifact:Artifact {artifact_id: $artifact_id})
            SET artifact.artifact_type = $artifact_type,
                artifact += $properties
            """,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            properties=properties or {},
        )

    def add_relationship(
        self,
        source_id: str,
        relationship: str,
        target_id: str,
        properties: dict | None = None,
    ) -> None:
        if relationship not in ALLOWED_RELATIONSHIPS:
            raise ValueError(f"unsupported relationship: {relationship}")
        query = f"""
        MATCH (source:Artifact {{artifact_id: $source_id}})
        MATCH (target:Artifact {{artifact_id: $target_id}})
        MERGE (source)-[link:{relationship}]->(target)
        SET link += $properties
        """
        self.driver.execute_query(
            query,
            source_id=source_id,
            target_id=target_id,
            properties=properties or {},
        )
