import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

from models import Customer


REPO_ROOT = Path(__file__).resolve().parents[1]
CONSTRAINT_NAME = "fk_customers_user_id_users"


def test_customer_user_id_model_foreign_key_metadata():
    user_id_column = Customer.__table__.c.user_id

    assert user_id_column.nullable is True
    assert len(user_id_column.foreign_keys) == 1

    foreign_key = next(iter(user_id_column.foreign_keys))

    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.constraint.name == CONSTRAINT_NAME
    assert foreign_key.ondelete == "RESTRICT"


def test_alembic_upgrade_head_adds_customers_user_id_foreign_key_on_sqlite(tmp_path):
    database_path = tmp_path / "alembic_fk.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{database_path}"

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns("customers")
        user_id_column = next(column for column in columns if column["name"] == "user_id")
        assert user_id_column["nullable"] is True

        foreign_keys = inspector.get_foreign_keys("customers")
        matching_foreign_keys = [
            foreign_key
            for foreign_key in foreign_keys
            if foreign_key["constrained_columns"] == ["user_id"]
            and foreign_key["referred_table"] == "users"
            and foreign_key["referred_columns"] == ["id"]
        ]

        assert len(matching_foreign_keys) == 1

        inspected_foreign_key = matching_foreign_keys[0]
        assert inspected_foreign_key["name"] == CONSTRAINT_NAME
        assert inspected_foreign_key["options"].get("ondelete") == "RESTRICT"
    finally:
        engine.dispose()
