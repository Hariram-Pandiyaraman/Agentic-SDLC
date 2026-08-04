"""Database engine, SQLite safety configuration, and migration entry point."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


class Database:
    def __init__(self, url: str, *, migrate: bool = True) -> None:
        self.url = url
        parsed = make_url(url)
        if parsed.drivername == "sqlite" and parsed.database not in {None, ":memory:"}:
            Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
        options = {"check_same_thread": False, "timeout": 5} if parsed.drivername == "sqlite" else {}
        self.engine: Engine = create_engine(url, future=True, pool_pre_ping=True, connect_args=options)
        if parsed.drivername == "sqlite":
            event.listen(self.engine, "connect", self._configure_sqlite)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False, class_=Session)
        if migrate:
            self.upgrade()

    @staticmethod
    def _configure_sqlite(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    def upgrade(self, revision: str = "head") -> None:
        root = Path(__file__).resolve().parents[2]
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", self.url.replace("%", "%%"))
        command.upgrade(config, revision)

    def session(self) -> Session:
        return self.session_factory()

    def dispose(self) -> None:
        self.engine.dispose()
