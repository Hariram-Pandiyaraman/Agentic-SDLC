"""Neo4j constraints and mock knowledge seeding."""

CONSTRAINTS = [
    """
    CREATE CONSTRAINT artifact_id_unique IF NOT EXISTS
    FOR (artifact:Artifact) REQUIRE artifact.artifact_id IS UNIQUE
    """,
    """
    CREATE INDEX artifact_type_index IF NOT EXISTS
    FOR (artifact:Artifact) ON (artifact.artifact_type)
    """,
]

SEED_ARTIFACTS = [
    {
        "artifact_id": "BRD-LEGACY-001",
        "artifact_type": "BRD",
        "title": "Approval workflow foundation",
        "summary": "Prior decision to make architect approval explicit and auditable.",
        "tags": ["approval", "workflow", "audit"],
    },
    {
        "artifact_id": "DEC-LEGACY-001",
        "artifact_type": "Decision",
        "title": "Local deterministic fallback",
        "summary": "Use versioned templates when the local model is unavailable.",
        "tags": ["ollama", "fallback", "local"],
    },
    {
        "artifact_id": "DEF-LEGACY-001",
        "artifact_type": "Defect",
        "title": "Acceptance criteria lost at QA handoff",
        "summary": "Release handoff omitted links between tests and acceptance criteria.",
        "tags": ["traceability", "testing", "qa"],
    },
]


def initialize_neo4j(uri: str, username: str, password: str) -> int:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(uri, auth=(username, password))
    try:
        driver.verify_connectivity()
        for statement in CONSTRAINTS:
            driver.execute_query(statement)
        driver.execute_query(
            """
            UNWIND $artifacts AS item
            MERGE (artifact:Artifact {artifact_id: item.artifact_id})
            SET artifact += item
            """,
            artifacts=SEED_ARTIFACTS,
        )
        return len(SEED_ARTIFACTS)
    finally:
        driver.close()
