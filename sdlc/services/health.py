"""Non-blocking readiness checks for local PoC dependencies."""

import asyncio
from urllib.parse import urlparse

import httpx
from sqlalchemy import text

from sdlc.config import Settings


async def _check_ollama(base_url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            models = [model.get("name", "") for model in response.json().get("models", [])]
            return {"status": "ready", "models": models}
    except Exception as exc:
        return {"status": "unavailable", "detail": str(exc)}


async def _check_neo4j(uri: str) -> dict:
    parsed = urlparse(uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 7687
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=1.5)
        writer.close()
        await writer.wait_closed()
        return {"status": "reachable", "host": host, "port": port}
    except Exception as exc:
        return {"status": "unavailable", "host": host, "port": port, "detail": str(exc)}


async def collect_health(settings: Settings, database=None) -> dict:
    ollama, neo4j = await asyncio.gather(
        _check_ollama(settings.ollama_base_url),
        _check_neo4j(settings.neo4j_uri),
    )
    database_health = {"status": "not_configured"}
    if database is not None:
        try:
            with database.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            database_health = {"status": "ready", "dialect": database.engine.dialect.name}
        except Exception as exc:
            database_health = {
                "status": "unavailable",
                "dialect": database.engine.dialect.name,
                "detail": f"Database connection failed ({type(exc).__name__}).",
            }
    degraded = ollama["status"] != "ready" or neo4j["status"] != "reachable" or database_health["status"] == "unavailable"
    fallback_ready = settings.enable_template_fallbacks and settings.use_fixture_context
    return {
        "status": "degraded" if degraded else "ready",
        "api": {"status": "ready", "environment": settings.app_env},
        "ollama": ollama,
        "neo4j": neo4j,
        "database": database_health,
        "fallbacks": {
            "status": "ready" if fallback_ready else "partial",
            "template_generation": settings.enable_template_fallbacks,
            "fixture_context": settings.use_fixture_context,
        },
    }
