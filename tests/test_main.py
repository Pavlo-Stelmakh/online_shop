import importlib
from pathlib import Path
import time
from decimal import Decimal

from database import Base
from models import Customer, Order, OrderItem
from tests.helpers import (
    TestingSessionLocal,
    build_isolated_stats_response,
    cancel_order,
    client,
    create_test_category,
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

def test_create_customer():
    headers = get_auth_headers(role="customer")

    response = client.post(
        "/customers",
        json={
            "name": f"Test Customer {time.time()}",
            "email": f"customer_{time.time()}@example.com",
            "phone": "+380501112233"
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert "user_id" in data
    assert "name" in data
    assert "email" in data

def test_create_order_and_reduce_stock():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=2,
        headers=customer_headers
    )

    assert "id" in order
    assert order["customer_id"] == customer["id"]
    assert order["total_price"] == 200
    assert order["items"][0]["unit_price"] == 100

    product_response = client.get(f"/products/{product['id']}")

    assert product_response.status_code == 200

    updated_product = product_response.json()

    assert updated_product["stock"] == 8


def test_order_item_unit_price_is_snapshot_when_product_price_changes():
    product = create_test_product(stock=10, price=12.5)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=3,
        headers=customer_headers,
    )

    assert order["total_price"] == 37.5
    assert order["items"][0]["unit_price"] == 12.5

    admin_headers = get_auth_headers(role="admin")
    update_response = client.put(
        f"/products/{product['id']}",
        json={
            "name": product["name"],
            "price": 99.99,
            "description": product["description"],
            "stock": 7,
            "low_stock_threshold": product["low_stock_threshold"],
            "category_id": product["category_id"],
        },
        headers=admin_headers,
    )

    assert update_response.status_code == 200

    order_response = client.get(f"/orders/{order['id']}", headers=customer_headers)

    assert order_response.status_code == 200
    persisted_order = order_response.json()
    assert persisted_order["total_price"] == 37.5
    assert persisted_order["items"][0]["unit_price"] == 12.5
    assert persisted_order["items"][0]["product"]["price"] == 99.99

def test_cancel_order_returns_stock():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=3,
        headers=customer_headers
    )

    product_after_order_response = client.get(f"/products/{product['id']}")

    assert product_after_order_response.status_code == 200
    assert product_after_order_response.json()["stock"] == 7

    cancelled_order = cancel_order(order["id"])

    assert cancelled_order["status"] == "cancelled"

    product_after_cancel_response = client.get(f"/products/{product['id']}")

    assert product_after_cancel_response.status_code == 200
    assert product_after_cancel_response.json()["stock"] == 10


def test_admin_cannot_delete_customer_who_has_orders():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    response = client.delete(
        f"/customers/{customer['id']}",
        headers=admin_headers
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Customer cannot be deleted because they have orders"
    )

    db = TestingSessionLocal()

    try:
        customer_exists = db.query(Customer).filter(
            Customer.id == customer["id"]
        ).first() is not None
        order_exists = db.query(Order).filter(
            Order.id == order["id"]
        ).first() is not None
    finally:
        db.close()

    assert customer_exists
    assert order_exists


def test_admin_can_delete_customer_with_no_orders():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    admin_headers = get_auth_headers(role="admin")

    response = client.delete(
        f"/customers/{customer['id']}",
        headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Customer deleted successfully"

    db = TestingSessionLocal()

    try:
        customer_exists = db.query(Customer).filter(
            Customer.id == customer["id"]
        ).first() is not None
    finally:
        db.close()

    assert not customer_exists


def test_admin_cannot_physically_delete_order_with_order_items():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    response = client.delete(
        f"/orders/{order['id']}",
        headers=admin_headers
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Order cannot be deleted because it has order items"
    )

    db = TestingSessionLocal()

    try:
        order_exists = db.query(Order).filter(
            Order.id == order["id"]
        ).first() is not None
        order_item_exists = db.query(OrderItem).filter(
            OrderItem.order_id == order["id"]
        ).first() is not None
    finally:
        db.close()

    assert order_exists
    assert order_item_exists

def test_create_order_requires_auth():
    product = create_test_product()
    customer = create_test_customer()

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 1
                }
            ]
        }
    )

    assert response.status_code == 401

def test_customer_can_create_order():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["customer_id"] == customer["id"]
    assert data["total_price"] == 200
    assert data["status"] == "new"

def test_customer_cannot_get_all_orders():
    headers = get_auth_headers(role="customer")

    response = client.get(
        "/orders",
        headers=headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"

def test_admin_can_get_all_orders():
    headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        headers=headers
    )

    assert response.status_code == 200

    body = response.json()

    assert "total" in body
    assert "skip" in body
    assert "limit" in body
    assert "items" in body
    assert isinstance(body["items"], list)


def test_customer_cannot_update_order_status():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    response = client.put(
        f"/orders/{order['id']}/status",
        params={
            "status": "paid"
        },
        headers=customer_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_can_update_order_status():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    response = client.put(
        f"/orders/{order['id']}/status",
        params={
            "status": "paid"
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "paid"


def test_customer_cannot_create_order_for_another_customer():
    product = create_test_product(stock=10, price=100)

    customer_1_headers = get_auth_headers(role="customer")
    customer_1 = create_test_customer(headers=customer_1_headers)

    customer_2_headers = get_auth_headers(role="customer")
    customer_2 = create_test_customer(headers=customer_2_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer_2["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 1
                }
            ]
        },
        headers=customer_1_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You can create orders only for your own customer profile"
    )

def test_customer_can_get_own_profile():
    headers = get_auth_headers(role="customer")

    customer = create_test_customer(headers=headers)

    response = client.get(
        "/customers/me",
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == customer["id"]
    assert data["user_id"] == customer["user_id"]
    assert data["email"] == customer["email"]


def test_customer_me_without_profile_returns_404():
    headers = get_auth_headers(role="customer")

    response = client.get(
        "/customers/me",
        headers=headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer profile not found"

def test_customer_me_requires_auth():
    response = client.get("/customers/me")

    assert response.status_code == 401


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_customer_can_get_own_orders():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=2,
        headers=customer_headers
    )

    response = client.get(
        "/orders/my",
        headers=customer_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    order_ids = [item["id"] for item in data]

    assert order["id"] in order_ids

    for item in data:
        assert item["customer_id"] == customer["id"]


def test_customer_cannot_get_other_customer_orders_in_my_orders():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=200)

    customer_1_headers = get_auth_headers(role="customer")
    customer_1 = create_test_customer(headers=customer_1_headers)

    customer_2_headers = get_auth_headers(role="customer")
    customer_2 = create_test_customer(headers=customer_2_headers)

    order_1 = create_test_order(
        product_id=product_1["id"],
        customer_id=customer_1["id"],
        quantity=1,
        headers=customer_1_headers
    )

    order_2 = create_test_order(
        product_id=product_2["id"],
        customer_id=customer_2["id"],
        quantity=1,
        headers=customer_2_headers
    )

    response = client.get(
        "/orders/my",
        headers=customer_1_headers
    )

    assert response.status_code == 200

    data = response.json()

    order_ids = [item["id"] for item in data]

    assert order_1["id"] in order_ids
    assert order_2["id"] not in order_ids

    for item in data:
        assert item["customer_id"] == customer_1["id"]


def test_my_orders_requires_auth():
    response = client.get("/orders/my")

    assert response.status_code == 401


def test_my_orders_without_customer_profile_returns_404():
    headers = get_auth_headers(role="customer")

    response = client.get(
        "/orders/my",
        headers=headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer profile not found"


def test_customer_can_get_own_order_by_id():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    response = client.get(
        f"/orders/{order['id']}",
        headers=customer_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == order["id"]
    assert data["customer_id"] == customer["id"]


def test_customer_cannot_get_other_customer_order_by_id():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=200)

    customer_1_headers = get_auth_headers(role="customer")
    customer_1 = create_test_customer(headers=customer_1_headers)

    customer_2_headers = get_auth_headers(role="customer")
    customer_2 = create_test_customer(headers=customer_2_headers)

    create_test_order(
        product_id=product_1["id"],
        customer_id=customer_1["id"],
        quantity=1,
        headers=customer_1_headers
    )

    order_2 = create_test_order(
        product_id=product_2["id"],
        customer_id=customer_2["id"],
        quantity=1,
        headers=customer_2_headers
    )

    response = client.get(
        f"/orders/{order_2['id']}",
        headers=customer_1_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


def test_admin_can_get_any_order_by_id():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        f"/orders/{order['id']}",
        headers=admin_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == order["id"]


def test_get_order_by_id_requires_auth():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    response = client.get(f"/orders/{order['id']}")

    assert response.status_code == 401


def test_admin_can_filter_orders_by_status():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=200)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order_1 = create_test_order(
        product_id=product_1["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    order_2 = create_test_order(
        product_id=product_2["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    paid_response = client.put(
        f"/orders/{order_2['id']}/status",
        params={
            "status": "paid"
        },
        headers=admin_headers
    )

    assert paid_response.status_code == 200

    response = client.get(
        "/orders",
        params={
            "status": "new"
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    order_ids = [order["id"] for order in data]

    assert order_1["id"] in order_ids
    assert order_2["id"] not in order_ids

    for order in data:
        assert order["status"] == "new"


def test_admin_can_filter_paid_orders():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    paid_response = client.put(
        f"/orders/{order['id']}/status",
        params={
            "status": "paid"
        },
        headers=admin_headers
    )

    assert paid_response.status_code == 200

    response = client.get(
        "/orders",
        params={
            "status": "paid"
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    order_ids = [item["id"] for item in data]

    assert order["id"] in order_ids

    for item in data:
        assert item["status"] == "paid"


def test_get_orders_invalid_status_returns_400():
    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "status": "wrong_status"
        },
        headers=admin_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid order status"


def test_customer_cannot_get_all_orders_with_status_filter():
    customer_headers = get_auth_headers(role="customer")

    response = client.get(
        "/orders",
        params={
            "status": "new"
        },
        headers=customer_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_can_filter_orders_by_customer_id():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=200)

    customer_1_headers = get_auth_headers(role="customer")
    customer_1 = create_test_customer(headers=customer_1_headers)

    customer_2_headers = get_auth_headers(role="customer")
    customer_2 = create_test_customer(headers=customer_2_headers)

    order_1 = create_test_order(
        product_id=product_1["id"],
        customer_id=customer_1["id"],
        quantity=1,
        headers=customer_1_headers
    )

    order_2 = create_test_order(
        product_id=product_2["id"],
        customer_id=customer_2["id"],
        quantity=1,
        headers=customer_2_headers
    )

    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "customer_id": customer_1["id"]
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    order_ids = [order["id"] for order in data]

    assert order_1["id"] in order_ids
    assert order_2["id"] not in order_ids

    for order in data:
        assert order["customer_id"] == customer_1["id"]


def test_admin_can_filter_orders_by_status_and_customer_id():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=200)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order_1 = create_test_order(
        product_id=product_1["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    order_2 = create_test_order(
        product_id=product_2["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    paid_response = client.put(
        f"/orders/{order_2['id']}/status",
        params={
            "status": "paid"
        },
        headers=admin_headers
    )

    assert paid_response.status_code == 200

    response = client.get(
        "/orders",
        params={
            "customer_id": customer["id"],
            "status": "new"
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    order_ids = [order["id"] for order in data]

    assert order_1["id"] in order_ids
    assert order_2["id"] not in order_ids

    for order in data:
        assert order["customer_id"] == customer["id"]
        assert order["status"] == "new"


def test_admin_filter_orders_by_unknown_customer_id_returns_empty_list():
    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "customer_id": 999999
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()

    assert body["items"] == []
    assert body["total"] == 0


def test_customer_cannot_filter_orders_by_customer_id():
    customer_headers = get_auth_headers(role="customer")

    response = client.get(
        "/orders",
        params={
            "customer_id": 1
        },
        headers=customer_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_can_filter_orders_by_date_from():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    today = order["created_at"][:10]

    response = client.get(
        "/orders",
        params={
            "date_from": today
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    order_ids = [item["id"] for item in data]

    assert order["id"] in order_ids


def test_admin_can_filter_orders_by_date_to():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    today = order["created_at"][:10]

    response = client.get(
        "/orders",
        params={
            "date_to": today
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    order_ids = [item["id"] for item in data]

    assert order["id"] in order_ids


def test_admin_can_filter_orders_by_status_customer_and_date_range():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    today = order["created_at"][:10]

    response = client.get(
        "/orders",
        params={
            "status": "new",
            "customer_id": customer["id"],
            "date_from": today,
            "date_to": today
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    order_ids = [item["id"] for item in data]

    assert order["id"] in order_ids

    for item in data:
        assert item["status"] == "new"
        assert item["customer_id"] == customer["id"]
        assert item["created_at"][:10] == today


def test_get_orders_invalid_date_format_returns_422():
    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "date_from": "wrong-date"
        },
        headers=admin_headers
    )

    assert response.status_code == 422


def test_admin_can_get_orders_with_pagination():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=200)
    product_3 = create_test_product(stock=10, price=300)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    create_test_order(
        product_id=product_1["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    create_test_order(
        product_id=product_2["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    create_test_order(
        product_id=product_3["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "skip": 0,
            "limit": 2
        },
        headers=admin_headers
    )

    assert response.status_code == 200

    body = response.json()
    data = body["items"]

    assert body["skip"] == 0
    assert body["limit"] == 2
    assert isinstance(data, list)
    assert len(data) <= 2


def test_admin_can_filter_orders_by_status_with_pagination():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=200)
    product_3 = create_test_product(stock=10, price=300)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order_1 = create_test_order(
        product_id=product_1["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    order_2 = create_test_order(
        product_id=product_2["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    order_3 = create_test_order(
        product_id=product_3["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    admin_headers = get_auth_headers(role="admin")

    paid_response = client.put(
        f"/orders/{order_3['id']}/status",
        params={
            "status": "paid"
        },
        headers=admin_headers
    )

    assert paid_response.status_code == 200

    response = client.get(
        "/orders",
        params={
            "status": "new",
            "skip": 0,
            "limit": 2
        },
        headers=admin_headers
    )

    assert response.status_code == 200
    
    body = response.json()
    data = body["items"]

    assert body["skip"] == 0
    assert body["limit"] == 2
    assert isinstance(data, list)
    assert len(data) <= 2

    for order in data:
        assert order["status"] == "new"

    order_ids = [order["id"] for order in data]

    assert order_3["id"] not in order_ids


def test_get_orders_invalid_negative_skip_returns_422():
    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "skip": -1,
            "limit": 10
        },
        headers=admin_headers
    )

    assert response.status_code == 422


def test_get_orders_invalid_limit_zero_returns_422():
    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "skip": 0,
            "limit": 0
        },
        headers=admin_headers
    )

    assert response.status_code == 422


def test_get_orders_invalid_limit_too_large_returns_422():
    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders",
        params={
            "skip": 0,
            "limit": 101
        },
        headers=admin_headers
    )

    assert response.status_code == 422


def test_create_order_with_empty_items_returns_400():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": []
        },
        headers=customer_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Order must contain at least one item"


def test_create_order_with_zero_quantity_returns_400():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 0
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid quantity"


def test_create_order_with_negative_quantity_returns_400():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": -1
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid quantity"


def test_create_order_with_unknown_product_returns_404():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": 999999,
                    "quantity": 1
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product with id 999999 not found"


def test_create_order_with_not_enough_stock_returns_400():
    product = create_test_product(stock=1, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == f"Not enough stock for product {product['name']}"


def test_invalid_multi_item_order_does_not_reduce_stock():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2
                },
                {
                    "product_id": 999999,
                    "quantity": 1
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product with id 999999 not found"

    product_response = client.get(f"/products/{product['id']}")

    assert product_response.status_code == 200
    assert product_response.json()["stock"] == 10


def test_invalid_multi_item_order_does_not_create_order():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    admin_headers = get_auth_headers(role="admin")

    before_response = client.get(
        "/orders",
        params={
            "customer_id": customer["id"]
        },
        headers=admin_headers
    )

    assert before_response.status_code == 200

    before_total = before_response.json()["total"]

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2
                },
                {
                    "product_id": 999999,
                    "quantity": 1
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product with id 999999 not found"

    after_response = client.get(
        "/orders",
        params={
            "customer_id": customer["id"]
        },
        headers=admin_headers
    )

    assert after_response.status_code == 200

    after_total = after_response.json()["total"]

    assert after_total == before_total


def test_valid_multi_item_order_calculates_total_price_correctly():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=250)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product_1["id"],
                    "quantity": 2
                },
                {
                    "product_id": product_2["id"],
                    "quantity": 3
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_price"] == 950


def test_valid_multi_item_order_reduces_stock_for_all_products():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=10, price=250)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product_1["id"],
                    "quantity": 2
                },
                {
                    "product_id": product_2["id"],
                    "quantity": 3
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 200

    product_1_response = client.get(f"/products/{product_1['id']}")
    product_2_response = client.get(f"/products/{product_2['id']}")

    assert product_1_response.status_code == 200
    assert product_2_response.status_code == 200

    assert product_1_response.json()["stock"] == 8
    assert product_2_response.json()["stock"] == 7


def test_create_order_with_duplicate_product_returns_400():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2
                },
                {
                    "product_id": product["id"],
                    "quantity": 3
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Duplicate product in order items"


def test_anonymous_cannot_read_customer_profile():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.get(f"/customers/{customer['id']}")

    assert response.status_code == 401


def test_anonymous_cannot_update_customer_profile():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.put(
        f"/customers/{customer['id']}",
        json={
            "name": "Anonymous Update",
            "email": f"anonymous_update_{time.time()}@example.com",
            "phone": "+380501112244"
        }
    )

    assert response.status_code == 401


def test_anonymous_cannot_delete_customer():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.delete(f"/customers/{customer['id']}")

    assert response.status_code == 401


def test_customer_cannot_read_other_customer_profile():
    customer_1_headers = get_auth_headers(role="customer")
    create_test_customer(headers=customer_1_headers)

    customer_2_headers = get_auth_headers(role="customer")
    customer_2 = create_test_customer(headers=customer_2_headers)

    response = client.get(
        f"/customers/{customer_2['id']}",
        headers=customer_1_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


def test_customer_cannot_update_other_customer_profile():
    customer_1_headers = get_auth_headers(role="customer")
    create_test_customer(headers=customer_1_headers)

    customer_2_headers = get_auth_headers(role="customer")
    customer_2 = create_test_customer(headers=customer_2_headers)

    response = client.put(
        f"/customers/{customer_2['id']}",
        json={
            "name": "Unauthorized Update",
            "email": f"unauthorized_update_{time.time()}@example.com",
            "phone": "+380501112255"
        },
        headers=customer_1_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


def test_admin_can_read_customer_profiles_by_id():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        f"/customers/{customer['id']}",
        headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["id"] == customer["id"]


def test_admin_can_update_customer_profiles_by_id():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    admin_headers = get_auth_headers(role="admin")
    updated_email = f"admin_update_{time.time()}@example.com"

    response = client.put(
        f"/customers/{customer['id']}",
        json={
            "name": "Admin Updated Customer",
            "email": updated_email,
            "phone": "+380501112266"
        },
        headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Admin Updated Customer"
    assert response.json()["email"] == updated_email


def test_non_admin_cannot_get_orders_by_status():
    customer_headers = get_auth_headers(role="customer")

    response = client.get(
        "/orders/by-status",
        params={"status": "new"},
        headers=customer_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


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


def test_customer_orders_route_is_registered_and_admin_only():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers
    )

    anonymous_response = client.get(f"/customers/{customer['id']}/orders")

    assert anonymous_response.status_code == 401

    customer_response = client.get(
        f"/customers/{customer['id']}/orders",
        headers=customer_headers
    )

    assert customer_response.status_code == 403
    assert customer_response.json()["detail"] == "Admin access required"

    admin_headers = get_auth_headers(role="admin")

    admin_response = client.get(
        f"/customers/{customer['id']}/orders",
        headers=admin_headers
    )

    assert admin_response.status_code == 200

    data = admin_response.json()
    order_ids = [item["id"] for item in data]

    assert order["id"] in order_ids


def test_start_script_runs_migrations_before_uvicorn():
    script_path = Path("scripts/start.sh")

    assert script_path.exists()

    script = script_path.read_text()
    assert "alembic upgrade head" in script
    assert "uvicorn main:app --host 0.0.0.0 --port" in script
    assert "${PORT:-8000}" in script
    assert script.index("alembic upgrade head") < script.index("uvicorn main:app")


def test_create_order_decimal_total_for_19_99_times_3():
    product = create_test_product(stock=10, price=19.99)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=3,
        headers=customer_headers,
    )

    assert order["total_price"] == 59.97
    assert order["items"][0]["unit_price"] == 19.99


def test_create_order_decimal_total_for_0_10_times_3_has_no_float_artifact():
    product = create_test_product(stock=10, price=0.10)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=3,
        headers=customer_headers,
    )

    assert order["total_price"] == 0.30
    assert str(order["total_price"]) == "0.3"


def test_create_order_multi_item_total_is_exact():
    product_1 = create_test_product(stock=10, price=0.10)
    product_2 = create_test_product(stock=10, price=19.99)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {"product_id": product_1["id"], "quantity": 3},
                {"product_id": product_2["id"], "quantity": 2},
            ],
        },
        headers=customer_headers,
    )

    assert response.status_code == 200
    order = response.json()
    assert order["total_price"] == 40.28
    assert [item["unit_price"] for item in order["items"]] == [0.10, 19.99]


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
