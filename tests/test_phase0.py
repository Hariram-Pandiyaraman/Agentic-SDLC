from fastapi.testclient import TestClient

from api.main import app
from sdlc.config import Settings


def test_default_configuration_enables_safe_fallbacks() -> None:
    settings = Settings()
    assert settings.allow_git_mutations is False
    assert settings.use_fixture_context is True
    assert settings.enable_template_fallbacks is True


def test_root_endpoint() -> None:
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json()["health"] == "/health"


def test_health_endpoint_remains_available_when_dependencies_are_down(
    monkeypatch,
) -> None:
    async def unavailable_ollama(_base_url: str) -> dict:
        return {"status": "unavailable", "detail": "test fixture"}

    async def unavailable_neo4j(_uri: str) -> dict:
        return {"status": "unavailable", "detail": "test fixture"}

    monkeypatch.setattr("sdlc.services.health._check_ollama", unavailable_ollama)
    monkeypatch.setattr("sdlc.services.health._check_neo4j", unavailable_neo4j)
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["api"]["status"] == "ready"
