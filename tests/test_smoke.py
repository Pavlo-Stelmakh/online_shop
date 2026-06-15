import importlib

from sqlalchemy.exc import SQLAlchemyError

from database import Base, get_db
from tests.helpers import app, client, main_module, override_get_db


def test_importing_app_does_not_create_database_tables(monkeypatch):
    def fail_create_all(*args, **kwargs):
        raise AssertionError("Application import must not create database tables")

    monkeypatch.setattr(Base.metadata, "create_all", fail_create_all)

    reloaded_main = importlib.reload(main_module)

    assert reloaded_main.app is not None


def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Online Shop API is running",
        "docs": "/docs",
        "health": "/health"
    }


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_check():
    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok"
    }


def test_database_health_check_failure_does_not_expose_database_url(monkeypatch):
    secret_database_url = "postgresql://user:password@example.com/online_shop"
    monkeypatch.setenv("DATABASE_URL", secret_database_url)

    class UnavailableDatabase:
        def execute(self, statement):
            raise SQLAlchemyError(secret_database_url)

    def override_unavailable_db():
        yield UnavailableDatabase()

    app.dependency_overrides[get_db] = override_unavailable_db

    try:
        response = client.get("/health/db")
    finally:
        app.dependency_overrides[get_db] = override_get_db

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "database": "unavailable"
    }
    assert secret_database_url not in response.text
    assert "password" not in response.text


def test_version_uses_unknown_fallbacks(monkeypatch):
    for env_var in (
        "APP_VERSION",
        "RENDER_GIT_COMMIT",
        "COMMIT_SHA",
        "APP_ENV",
        "ENVIRONMENT",
        "RENDER_ENVIRONMENT",
    ):
        monkeypatch.delenv(env_var, raising=False)

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "app": "online_shop",
        "version": "unknown",
        "commit": "unknown",
        "environment": "unknown"
    }


def test_version_uses_environment_variables(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc123")
    monkeypatch.setenv("COMMIT_SHA", "fallback456")
    monkeypatch.setenv("APP_ENV", "production")

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "app": "online_shop",
        "version": "1.2.3",
        "commit": "abc123",
        "environment": "production"
    }
