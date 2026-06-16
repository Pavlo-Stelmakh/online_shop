import time

from models import Customer, Order
from tests.helpers import (
    TestingSessionLocal,
    client,
    create_test_customer,
    create_test_order,
    create_test_product,
    get_auth_headers,
)


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




def test_create_customer_rejects_blank_or_whitespace_fields():
    for field, value in [
        ("name", ""),
        ("name", "   "),
        ("email", ""),
        ("email", "   "),
        ("phone", ""),
        ("phone", "   "),
    ]:
        headers = get_auth_headers(role="customer")
        payload = {
            "name": f"Validation Customer {time.time()}",
            "email": f"validation_customer_{time.time()}@example.com",
            "phone": "+380501112233"
        }
        payload[field] = value

        response = client.post(
            "/customers",
            json=payload,
            headers=headers
        )

        assert response.status_code == 422


def test_create_customer_rejects_invalid_email():
    headers = get_auth_headers(role="customer")

    response = client.post(
        "/customers",
        json={
            "name": "Invalid Email Customer",
            "email": "not-an-email",
            "phone": "+380501112233"
        },
        headers=headers
    )

    assert response.status_code == 422


def test_create_customer_trims_valid_fields():
    headers = get_auth_headers(role="customer")
    email = f"trim_customer_{time.time()}@example.com"

    response = client.post(
        "/customers",
        json={
            "name": "  Trimmed Customer  ",
            "email": f"  {email}  ",
            "phone": "  +380501112233  "
        },
        headers=headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Trimmed Customer"
    assert response.json()["email"] == email
    assert response.json()["phone"] == "+380501112233"


def test_update_customer_rejects_blank_or_whitespace_fields():
    for field, value in [
        ("name", ""),
        ("name", "   "),
        ("email", ""),
        ("email", "   "),
        ("phone", ""),
        ("phone", "   "),
    ]:
        customer_headers = get_auth_headers(role="customer")
        customer = create_test_customer(headers=customer_headers)
        payload = {
            "name": "Updated Customer",
            "email": f"updated_customer_{time.time()}@example.com",
            "phone": "+380501112266"
        }
        payload[field] = value

        response = client.put(
            f"/customers/{customer['id']}",
            json=payload,
            headers=customer_headers
        )

        assert response.status_code == 422


def test_update_customer_trims_valid_fields():
    customer_headers = get_auth_headers(role="customer")
    customer = create_test_customer(headers=customer_headers)
    email = f"trim_update_{time.time()}@example.com"

    response = client.put(
        f"/customers/{customer['id']}",
        json={
            "name": "  Updated Trim Customer  ",
            "email": f"  {email}  ",
            "phone": "  +380501112266  "
        },
        headers=customer_headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Trim Customer"
    assert response.json()["email"] == email
    assert response.json()["phone"] == "+380501112266"
