import importlib

from database import Base
from tests.helpers import client, main_module


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
