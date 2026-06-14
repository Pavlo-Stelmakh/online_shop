from pathlib import Path


def test_start_script_runs_migrations_before_uvicorn():
    script_path = Path("scripts/start.sh")

    assert script_path.exists()

    script = script_path.read_text()
    assert "alembic upgrade head" in script
    assert "uvicorn main:app --host 0.0.0.0 --port" in script
    assert "${PORT:-8000}" in script
    assert script.index("alembic upgrade head") < script.index("uvicorn main:app")
