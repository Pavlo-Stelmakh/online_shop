import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from models import Customer


REPO_ROOT = Path(__file__).resolve().parents[1]
FOREIGN_KEY_CONSTRAINT_NAME = "fk_customers_user_id_users"
CUSTOMER_CHECK_CONSTRAINTS = {
    "ck_customers_name_not_empty": "trim(name) <> ''",
    "ck_customers_email_not_empty": "trim(email) <> ''",
    "ck_customers_phone_not_empty": "trim(phone) <> ''",
}


def test_customer_required_fields_model_metadata():
    assert Customer.__table__.c.user_id.nullable is False
    assert Customer.__table__.c.name.nullable is False
    assert Customer.__table__.c.email.nullable is False
    assert Customer.__table__.c.phone.nullable is False


def test_customer_check_constraints_exist_in_model_metadata():
    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in Customer.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    for constraint_name, constraint_sql in CUSTOMER_CHECK_CONSTRAINTS.items():
        assert check_constraints[constraint_name] == constraint_sql


def test_customer_user_id_model_foreign_key_metadata():
    user_id_column = Customer.__table__.c.user_id

    assert user_id_column.nullable is False
    assert len(user_id_column.foreign_keys) == 1

    foreign_key = next(iter(user_id_column.foreign_keys))

    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.constraint.name == FOREIGN_KEY_CONSTRAINT_NAME
    assert foreign_key.ondelete == "RESTRICT"


def test_alembic_upgrade_head_enforces_customer_required_fields_on_sqlite(tmp_path):
    database_path = tmp_path / "alembic_customer_required_fields.db"
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
        columns = {column["name"]: column for column in inspector.get_columns("customers")}

        assert columns["user_id"]["nullable"] is False
        assert columns["name"]["nullable"] is False
        assert columns["email"]["nullable"] is False
        assert columns["phone"]["nullable"] is False

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
        assert inspected_foreign_key["name"] == FOREIGN_KEY_CONSTRAINT_NAME
        assert inspected_foreign_key["options"].get("ondelete") == "RESTRICT"

        check_constraints = {
            constraint["name"]: constraint["sqltext"]
            for constraint in inspector.get_check_constraints("customers")
        }
        for constraint_name, constraint_sql in CUSTOMER_CHECK_CONSTRAINTS.items():
            assert constraint_name in check_constraints
            assert constraint_sql in check_constraints[constraint_name]

        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO users (username, email, hashed_password, role)
                    VALUES ('customer_user', 'customer-user@example.com', 'hash', 'customer')
                    """
                )
            )
            user_id = connection.execute(
                text("SELECT id FROM users WHERE username = 'customer_user'")
            ).scalar_one()
            connection.execute(
                text(
                    """
                    INSERT INTO customers (user_id, name, email, phone)
                    VALUES (:user_id, 'Valid Customer', 'valid-customer@example.com', '+10000000000')
                    """
                ),
                {"user_id": user_id},
            )

        invalid_statements = [
            """
            INSERT INTO customers (user_id, name, email, phone)
            VALUES (NULL, 'Missing User', 'missing-user@example.com', '+10000000001')
            """,
            f"""
            INSERT INTO customers (user_id, name, email, phone)
            VALUES ({user_id}, NULL, 'missing-name@example.com', '+10000000002')
            """,
            f"""
            INSERT INTO customers (user_id, name, email, phone)
            VALUES ({user_id}, '', 'empty-name@example.com', '+10000000003')
            """,
            f"""
            INSERT INTO customers (user_id, name, email, phone)
            VALUES ({user_id}, '   ', 'blank-name@example.com', '+10000000004')
            """,
            f"""
            INSERT INTO customers (user_id, name, email, phone)
            VALUES ({user_id}, 'Missing Email', NULL, '+10000000005')
            """,
            f"""
            INSERT INTO customers (user_id, name, email, phone)
            VALUES ({user_id}, 'Empty Email', '', '+10000000006')
            """,
            f"""
            INSERT INTO customers (user_id, name, email, phone)
            VALUES ({user_id}, 'Blank Email', '   ', '+10000000007')
            """,
            f"""
            INSERT INTO customers (user_id, name, email, phone)
            VALUES ({user_id}, 'Missing Phone', 'missing-phone@example.com', NULL)
            """,
            f"""
            INSERT INTO customers (user_id, name, email, phone)
            VALUES ({user_id}, 'Empty Phone', 'empty-phone@example.com', '')
            """,
            f"""
            INSERT INTO customers (user_id, name, email, phone)
            VALUES ({user_id}, 'Blank Phone', 'blank-phone@example.com', '   ')
            """,
        ]
        for statement in invalid_statements:
            with pytest.raises(IntegrityError):
                with engine.begin() as connection:
                    connection.execute(text(statement))
    finally:
        engine.dispose()
