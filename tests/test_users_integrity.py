import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from models import User


REPO_ROOT = Path(__file__).resolve().parents[1]
ROLE_CONSTRAINT_NAME = "ck_users_role_admin_customer"


def test_user_core_auth_fields_are_not_nullable_in_model_metadata():
    assert User.__table__.c.username.nullable is False
    assert User.__table__.c.email.nullable is False
    assert User.__table__.c.hashed_password.nullable is False
    assert User.__table__.c.role.nullable is False


def test_user_role_check_constraint_exists_in_model_metadata():
    matching_constraints = [
        constraint
        for constraint in User.__table__.constraints
        if isinstance(constraint, CheckConstraint)
        and constraint.name == ROLE_CONSTRAINT_NAME
    ]

    assert len(matching_constraints) == 1
    assert "role IN ('admin', 'customer')" in str(matching_constraints[0].sqltext)


def test_alembic_upgrade_head_enforces_users_required_fields_and_role_on_sqlite(
    tmp_path,
):
    database_path = tmp_path / "users_integrity.db"
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
        columns = {column["name"]: column for column in inspector.get_columns("users")}

        assert columns["username"]["nullable"] is False
        assert columns["email"]["nullable"] is False
        assert columns["hashed_password"]["nullable"] is False
        assert columns["role"]["nullable"] is False

        check_constraints = inspector.get_check_constraints("users")
        matching_constraints = [
            constraint
            for constraint in check_constraints
            if constraint["name"] == ROLE_CONSTRAINT_NAME
        ]
        assert len(matching_constraints) == 1
        assert "role IN ('admin', 'customer')" in matching_constraints[0]["sqltext"]

        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO users (username, email, hashed_password, role)
                    VALUES ('valid_user', 'valid@example.com', 'hash', 'customer')
                    """
                )
            )

            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        """
                        INSERT INTO users (username, email, hashed_password, role)
                        VALUES ('bad_role_user', 'bad-role@example.com', 'hash', 'manager')
                        """
                    )
                )

            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        """
                        INSERT INTO users (username, email, hashed_password, role)
                        VALUES (NULL, 'missing-username@example.com', 'hash', 'customer')
                        """
                    )
                )
    finally:
        engine.dispose()
