import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from models import Category


REPO_ROOT = Path(__file__).resolve().parents[1]
CATEGORY_NAME_CONSTRAINT_NAME = "ck_categories_name_not_empty"
CATEGORY_NAME_CONSTRAINT_SQL = "trim(name) <> ''"


def test_category_name_is_not_nullable_in_model_metadata():
    assert Category.__table__.c.name.nullable is False


def test_category_name_check_constraint_exists_in_model_metadata():
    matching_constraints = [
        constraint
        for constraint in Category.__table__.constraints
        if isinstance(constraint, CheckConstraint)
        and constraint.name == CATEGORY_NAME_CONSTRAINT_NAME
    ]

    assert len(matching_constraints) == 1
    assert CATEGORY_NAME_CONSTRAINT_SQL == str(matching_constraints[0].sqltext)


def test_alembic_upgrade_head_enforces_category_name_on_sqlite(tmp_path):
    database_path = tmp_path / "categories_integrity.db"
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
        columns = {column["name"]: column for column in inspector.get_columns("categories")}

        assert columns["name"]["nullable"] is False

        check_constraints = {
            constraint["name"]: constraint["sqltext"]
            for constraint in inspector.get_check_constraints("categories")
        }
        assert CATEGORY_NAME_CONSTRAINT_NAME in check_constraints
        assert CATEGORY_NAME_CONSTRAINT_SQL in check_constraints[
            CATEGORY_NAME_CONSTRAINT_NAME
        ]

        with engine.begin() as connection:
            connection.execute(text("INSERT INTO categories (name) VALUES ('Valid')"))

        invalid_statements = [
            "INSERT INTO categories (name) VALUES (NULL)",
            "INSERT INTO categories (name) VALUES ('')",
            "INSERT INTO categories (name) VALUES ('   ')",
        ]
        for statement in invalid_statements:
            with pytest.raises(IntegrityError):
                with engine.begin() as connection:
                    connection.execute(text(statement))
    finally:
        engine.dispose()
