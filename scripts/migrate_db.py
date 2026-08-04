"""Upgrade the configured relational database to the latest Alembic revision."""

from sdlc.config import get_settings
from sdlc.persistence import Database


def main() -> None:
    settings = get_settings()
    database = Database(settings.resolved_database_url(), migrate=False)
    try:
        database.upgrade()
        print(f"Database schema is current ({database.engine.dialect.name}).")
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
