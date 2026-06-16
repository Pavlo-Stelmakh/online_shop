from decimal import Decimal

from models import Order, OrderItem
from tests.helpers import (
    TestingSessionLocal,
    cancel_order,
    client,
    create_test_category,
    create_test_customer,
    create_test_order,
    create_test_product,
    get_auth_headers,
)


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


def _get_product_stock(product_id: int) -> int:
    response = client.get(f"/products/{product_id}")

    assert response.status_code == 200

    return response.json()["stock"]


def _create_order_for_stock_restore(initial_stock: int = 10, quantity: int = 3):
    product = create_test_product(stock=initial_stock, price=100)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=quantity,
        headers=customer_headers,
    )

    return product, order


def _update_order_status(order_id: int, status: str):
    return client.put(
        f"/orders/{order_id}/status",
        params={"status": status},
        headers=get_auth_headers(role="admin"),
    )


def _get_order_status(order_id: int, headers=None) -> str:
    response = client.get(
        f"/orders/{order_id}",
        headers=headers or get_auth_headers(role="admin"),
    )

    assert response.status_code == 200

    return response.json()["status"]


def test_admin_can_update_new_order_to_paid():
    product, order = _create_order_for_stock_restore(initial_stock=10, quantity=1)

    response = _update_order_status(order["id"], "paid")

    assert response.status_code == 200
    assert response.json()["status"] == "paid"
    assert _get_product_stock(product["id"]) == 9


def test_admin_can_update_paid_order_to_shipped():
    product, order = _create_order_for_stock_restore(initial_stock=10, quantity=1)

    paid_response = _update_order_status(order["id"], "paid")
    shipped_response = _update_order_status(order["id"], "shipped")

    assert paid_response.status_code == 200
    assert shipped_response.status_code == 200
    assert shipped_response.json()["status"] == "shipped"
    assert _get_product_stock(product["id"]) == 9


def test_new_to_shipped_transition_is_rejected_and_status_is_unchanged():
    product, order = _create_order_for_stock_restore(initial_stock=10, quantity=1)

    response = _update_order_status(order["id"], "shipped")

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Cannot change order status from 'new' to 'shipped'"
    )
    assert _get_order_status(order["id"]) == "new"
    assert _get_product_stock(product["id"]) == 9


def test_paid_to_new_transition_is_rejected_and_status_is_unchanged():
    product, order = _create_order_for_stock_restore(initial_stock=10, quantity=1)

    paid_response = _update_order_status(order["id"], "paid")
    response = _update_order_status(order["id"], "new")

    assert paid_response.status_code == 200
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Cannot change order status from 'paid' to 'new'"
    )
    assert _get_order_status(order["id"]) == "paid"
    assert _get_product_stock(product["id"]) == 9


def test_shipped_terminal_transitions_are_rejected_and_status_is_unchanged():
    product, order = _create_order_for_stock_restore(initial_stock=10, quantity=1)

    assert _update_order_status(order["id"], "paid").status_code == 200
    assert _update_order_status(order["id"], "shipped").status_code == 200

    for status in ["new", "paid", "cancelled"]:
        response = _update_order_status(order["id"], status)

        assert response.status_code == 400
        assert _get_order_status(order["id"]) == "shipped"
        assert _get_product_stock(product["id"]) == 9


def test_cancelled_terminal_transitions_are_rejected_and_status_is_unchanged():
    product, order = _create_order_for_stock_restore(initial_stock=10, quantity=1)

    assert _update_order_status(order["id"], "cancelled").status_code == 200

    for status in ["new", "paid", "shipped"]:
        response = _update_order_status(order["id"], status)

        assert response.status_code == 400
        assert _get_order_status(order["id"]) == "cancelled"
        assert _get_product_stock(product["id"]) == 10


def test_same_status_update_is_rejected():
    product, order = _create_order_for_stock_restore(initial_stock=10, quantity=1)

    response = _update_order_status(order["id"], "new")

    assert response.status_code == 400
    assert response.json()["detail"] == "Order already has status 'new'"
    assert _get_order_status(order["id"]) == "new"
    assert _get_product_stock(product["id"]) == 9


def test_failed_transition_does_not_change_persisted_status():
    product, order = _create_order_for_stock_restore(initial_stock=10, quantity=2)

    paid_response = _update_order_status(order["id"], "paid")
    failed_response = _update_order_status(order["id"], "new")

    assert paid_response.status_code == 200
    assert failed_response.status_code == 400
    assert failed_response.json()["detail"] == (
        "Cannot change order status from 'paid' to 'new'"
    )
    assert _get_order_status(order["id"]) == "paid"
    assert _get_product_stock(product["id"]) == 8


def test_cancelling_new_order_restores_stock_once():
    product, order = _create_order_for_stock_restore(initial_stock=10, quantity=3)

    assert _get_product_stock(product["id"]) == 7

    response = _update_order_status(order["id"], "cancelled")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert _get_product_stock(product["id"]) == 10


def test_cancelling_paid_order_restores_stock_once():
    product, order = _create_order_for_stock_restore(initial_stock=10, quantity=3)

    paid_response = _update_order_status(order["id"], "paid")

    assert paid_response.status_code == 200
    assert paid_response.json()["status"] == "paid"
    assert _get_product_stock(product["id"]) == 7

    cancelled_response = _update_order_status(order["id"], "cancelled")

    assert cancelled_response.status_code == 200
    assert cancelled_response.json()["status"] == "cancelled"
    assert _get_product_stock(product["id"]) == 10


def test_cancelling_already_cancelled_order_returns_error_and_does_not_restore_stock_twice():
    product, order = _create_order_for_stock_restore(initial_stock=10, quantity=3)

    first_cancel_response = _update_order_status(order["id"], "cancelled")

    assert first_cancel_response.status_code == 200
    assert _get_product_stock(product["id"]) == 10

    second_cancel_response = _update_order_status(order["id"], "cancelled")

    assert second_cancel_response.status_code == 400
    assert second_cancel_response.json()["detail"] == (
        "Order already has status 'cancelled'"
    )
    assert _get_product_stock(product["id"]) == 10


def test_cancelling_shipped_order_returns_error_and_does_not_restore_stock():
    product, order = _create_order_for_stock_restore(initial_stock=10, quantity=3)

    paid_response = _update_order_status(order["id"], "paid")
    shipped_response = _update_order_status(order["id"], "shipped")

    assert paid_response.status_code == 200
    assert shipped_response.status_code == 200
    assert shipped_response.json()["status"] == "shipped"
    assert _get_product_stock(product["id"]) == 7

    cancelled_response = _update_order_status(order["id"], "cancelled")

    assert cancelled_response.status_code == 400
    assert cancelled_response.json()["detail"] == (
        "Cannot change order status from 'shipped' to 'cancelled'"
    )
    assert _get_product_stock(product["id"]) == 7


def test_invalid_transitions_from_cancelled_remain_blocked_and_stock_does_not_change():
    product, order = _create_order_for_stock_restore(initial_stock=10, quantity=3)

    cancelled_response = _update_order_status(order["id"], "cancelled")

    assert cancelled_response.status_code == 200
    assert _get_product_stock(product["id"]) == 10

    paid_response = _update_order_status(order["id"], "paid")

    assert paid_response.status_code == 400
    assert paid_response.json()["detail"] == (
        "Cannot change order status from 'cancelled' to 'paid'"
    )
    assert _get_product_stock(product["id"]) == 10


def test_stock_restore_uses_successful_status_transition_only():
    product, order = _create_order_for_stock_restore(initial_stock=10, quantity=3)

    with TestingSessionLocal() as db:
        db.query(Order).filter(Order.id == order["id"]).update(
            {Order.status: "cancelled"},
            synchronize_session=False,
        )
        db.commit()

    assert _get_product_stock(product["id"]) == 7

    response = _update_order_status(order["id"], "cancelled")

    assert response.status_code == 400
    assert response.json()["detail"] == "Order already has status 'cancelled'"
    assert _get_product_stock(product["id"]) == 7


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


def test_create_order_with_empty_items_returns_422():
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

    assert response.status_code == 422


def test_create_order_with_zero_quantity_returns_422():
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

    assert response.status_code == 422


def test_create_order_with_negative_quantity_returns_422():
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

    assert response.status_code == 422


def test_create_order_with_zero_product_id_returns_422():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {
                    "product_id": 0,
                    "quantity": 1
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 422


def test_create_order_with_zero_customer_id_returns_422():
    product = create_test_product(stock=10, price=100)

    customer_headers = get_auth_headers(role="customer")

    response = client.post(
        "/orders",
        json={
            "customer_id": 0,
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 1
                }
            ]
        },
        headers=customer_headers
    )

    assert response.status_code == 422


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


def test_non_admin_cannot_get_orders_by_status():
    customer_headers = get_auth_headers(role="customer")

    response = client.get(
        "/orders/by-status",
        params={"status": "new"},
        headers=customer_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


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




def test_create_order_with_not_enough_stock_keeps_stock_unchanged():
    product = create_test_product(stock=1, price=100)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {"product_id": product["id"], "quantity": 2},
            ],
        },
        headers=customer_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == f"Not enough stock for product {product['name']}"

    product_response = client.get(f"/products/{product['id']}")

    assert product_response.status_code == 200
    assert product_response.json()["stock"] == 1


def test_invalid_multi_item_order_with_insufficient_stock_rolls_back_all_stock_changes():
    product_1 = create_test_product(stock=10, price=100)
    product_2 = create_test_product(stock=1, price=200)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {"product_id": product_1["id"], "quantity": 2},
                {"product_id": product_2["id"], "quantity": 2},
            ],
        },
        headers=customer_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == f"Not enough stock for product {product_2['name']}"

    product_1_response = client.get(f"/products/{product_1['id']}")
    product_2_response = client.get(f"/products/{product_2['id']}")

    assert product_1_response.status_code == 200
    assert product_2_response.status_code == 200
    assert product_1_response.json()["stock"] == 10
    assert product_2_response.json()["stock"] == 1


def test_create_order_with_duplicate_product_does_not_mutate_stock():
    product = create_test_product(stock=10, price=100)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {"product_id": product["id"], "quantity": 2},
                {"product_id": product["id"], "quantity": 3},
            ],
        },
        headers=customer_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Duplicate product in order items"

    product_response = client.get(f"/products/{product['id']}")

    assert product_response.status_code == 200
    assert product_response.json()["stock"] == 10


def test_create_order_atomic_update_path_is_rollback_safe_for_later_item_failure():
    product_1 = create_test_product(stock=5, price=10)
    product_2 = create_test_product(stock=5, price=20)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    response = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [
                {"product_id": product_2["id"], "quantity": 2},
                {"product_id": product_1["id"], "quantity": 6},
            ],
        },
        headers=customer_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == f"Not enough stock for product {product_1['name']}"

    product_1_response = client.get(f"/products/{product_1['id']}")
    product_2_response = client.get(f"/products/{product_2['id']}")

    assert product_1_response.status_code == 200
    assert product_2_response.status_code == 200
    assert product_1_response.json()["stock"] == 5
    assert product_2_response.json()["stock"] == 5


def test_order_returns_exact_money_amount_strings_for_trailing_zero_unit_price():
    product = create_test_product(stock=10, price=19.90)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=3,
        headers=customer_headers,
    )

    assert order["items"][0]["unit_price"] == 19.9
    assert order["items"][0]["unit_price_amount"] == "19.90"
    assert order["total_price"] == 59.7
    assert order["total_price_amount"] == "59.70"


def test_order_returns_exact_total_amount_string_for_fractional_total():
    product = create_test_product(stock=10, price=0.10)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)

    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=3,
        headers=customer_headers,
    )

    assert order["total_price"] == 0.3
    assert order["total_price_amount"] == "0.30"


def test_order_response_status_openapi_schema_documents_allowed_enum():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    status_schema = response.json()["components"]["schemas"]["OrderResponse"]["properties"]["status"]

    assert status_schema["type"] == "string"
    assert status_schema["enum"] == ["new", "paid", "shipped", "cancelled"]


def test_get_orders_by_status_invalid_status_is_rejected():
    admin_headers = get_auth_headers(role="admin")

    response = client.get(
        "/orders/by-status",
        params={"status": "invalid"},
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_update_order_status_invalid_status_is_rejected():
    product = create_test_product(stock=10, price=100)
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    order = create_test_order(
        product_id=product["id"],
        customer_id=customer["id"],
        quantity=1,
        headers=customer_headers,
    )
    admin_headers = get_auth_headers(role="admin")

    response = client.put(
        f"/orders/{order['id']}/status",
        params={"status": "invalid"},
        headers=admin_headers,
    )

    assert response.status_code == 422
