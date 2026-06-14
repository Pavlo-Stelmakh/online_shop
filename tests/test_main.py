import importlib
from pathlib import Path
from decimal import Decimal

from database import Base
from tests.helpers import (
    build_isolated_stats_response,
    client,
    create_test_customer,
    create_test_order,
    create_test_product,
    get_auth_headers,
    main_module,
)


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


def test_non_admin_cannot_get_stats_summary():
    customer_headers = get_auth_headers(role="customer")

    response = client.get(
        "/stats/summary",
        headers=customer_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_stats_summary_api_returns_numeric_total_revenue():
    product = create_test_product(stock=10, price=19.9)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers,
    )

    admin_headers = get_auth_headers(role="admin")
    status_response = client.put(
        f"/orders/{order['id']}/status",
        params={"status": "paid"},
        headers=admin_headers,
    )

    assert status_response.status_code == 200

    response = client.get(
        "/stats/summary",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert isinstance(response.json()["total_revenue"], (int, float))
    assert not isinstance(response.json()["total_revenue"], str)


def test_start_script_runs_migrations_before_uvicorn():
    script_path = Path("scripts/start.sh")

    assert script_path.exists()

    script = script_path.read_text()
    assert "alembic upgrade head" in script
    assert "uvicorn main:app --host 0.0.0.0 --port" in script
    assert "${PORT:-8000}" in script
    assert script.index("alembic upgrade head") < script.index("uvicorn main:app")


def test_stats_revenue_includes_paid_orders():
    response = build_isolated_stats_response({"paid": ["12.34"]})

    assert response["total_revenue"] == Decimal("12.34")


def test_stats_revenue_includes_shipped_orders():
    response = build_isolated_stats_response({"shipped": ["23.45"]})

    assert response["total_revenue"] == Decimal("23.45")


def test_stats_revenue_excludes_new_orders():
    response = build_isolated_stats_response({"new": ["99.99"]})

    assert response["total_revenue"] == Decimal("0.00")


def test_stats_revenue_excludes_cancelled_orders():
    response = build_isolated_stats_response({"cancelled": ["99.99"]})

    assert response["total_revenue"] == Decimal("0.00")


def test_stats_revenue_sums_fractional_orders_exactly():
    response = build_isolated_stats_response(
        {
            "paid": ["0.10", "0.20"],
            "shipped": ["19.99"],
        }
    )

    assert response["total_revenue"] == Decimal("20.29")
    assert str(response["total_revenue"]) == "20.29"


def test_stats_revenue_is_zero_for_empty_orders():
    response = build_isolated_stats_response({})

    assert response["total_revenue"] == Decimal("0.00")


