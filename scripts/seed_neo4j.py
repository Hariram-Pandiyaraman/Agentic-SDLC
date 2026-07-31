"""Create Neo4j constraints and load mock context when a server is available."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sdlc.config import get_settings
from sdlc.services.neo4j_schema import initialize_neo4j


def main() -> None:
    settings = get_settings()
    try:
        seeded = initialize_neo4j(
            settings.neo4j_uri,
            settings.neo4j_username,
            settings.neo4j_password,
        )
    except Exception as exc:
        raise SystemExit(
            "Neo4j is unavailable. Keep USE_FIXTURE_CONTEXT=true or start Neo4j "
            f"and retry. Details: {type(exc).__name__}: {exc}"
        ) from exc
    print(f"Neo4j initialized; {seeded} mock artifacts seeded.")


if __name__ == "__main__":
    main()
