import time

from tests.helpers import (
    client,
    create_test_category,
    get_auth_headers,
)


def test_create_category():
    headers = get_auth_headers()

    response = client.post(
        "/categories",
        json={
            "name": f"Test Category {time.time()}"
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["name"].startswith("Test Category")


def test_create_category_requires_auth():
    response = client.post(
        "/categories",
        json={
            "name": f"Protected Category {time.time()}"
        }
    )

    assert response.status_code == 401


def test_create_category_with_auth():
    headers = get_auth_headers()

    response = client.post(
        "/categories",
        json={
            "name": f"Auth Category {time.time()}"
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["name"].startswith("Auth Category")


def test_customer_cannot_create_category():
    headers = get_auth_headers(role="customer")

    response = client.post(
        "/categories",
        json={
            "name": f"Customer Forbidden Category {time.time()}"
        },
        headers=headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_can_create_category():
    headers = get_auth_headers(role="admin")

    response = client.post(
        "/categories",
        json={
            "name": f"Admin Allowed Category {time.time()}"
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["name"].startswith("Admin Allowed Category")


def test_admin_can_update_category():
    admin_headers = get_auth_headers(role="admin")
    category = create_test_category()

    response = client.put(
        f"/categories/{category['id']}",
        json={
            "name": f"Updated Category {time.time()}"
        },
        headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["id"] == category["id"]
    assert response.json()["name"].startswith("Updated Category")


def test_update_category_not_found_returns_404():
    admin_headers = get_auth_headers(role="admin")

    response = client.put(
        "/categories/999999",
        json={
            "name": "Updated Category"
        },
        headers=admin_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


def test_update_category_with_duplicate_name_returns_400():
    admin_headers = get_auth_headers(role="admin")

    category_1 = create_test_category()
    category_2 = create_test_category()

    response = client.put(
        f"/categories/{category_2['id']}",
        json={
            "name": category_1["name"]
        },
        headers=admin_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Category already exists"


def test_update_category_with_empty_name_returns_422():
    admin_headers = get_auth_headers(role="admin")
    category = create_test_category()

    response = client.put(
        f"/categories/{category['id']}",
        json={
            "name": ""
        },
        headers=admin_headers
    )

    assert response.status_code == 422

def test_admin_can_delete_empty_category():
    admin_headers = get_auth_headers(role="admin")
    category = create_test_category()

    response = client.delete(
        f"/categories/{category['id']}",
        headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Category deleted successfully"


def test_delete_category_not_found_returns_404():
    admin_headers = get_auth_headers(role="admin")

    response = client.delete(
        "/categories/999999",
        headers=admin_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


def test_cannot_delete_category_with_products():
    admin_headers = get_auth_headers(role="admin")
    category = create_test_category()

    product_response = client.post(
        "/products",
        json={
            "name": f"Product In Category {time.time()}",
            "price": 100,
            "description": "Product linked to category",
            "image_url": None,
            "stock": 10,
            "category_id": category["id"]
        },
        headers=admin_headers
    )

    assert product_response.status_code == 200

    response = client.delete(
        f"/categories/{category['id']}",
        headers=admin_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot delete category with products"


def test_customer_cannot_delete_category():
    category = create_test_category()
    customer_headers = get_auth_headers(role="customer")

    response = client.delete(
        f"/categories/{category['id']}",
        headers=customer_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_delete_category_requires_auth():
    category = create_test_category()

    response = client.delete(
        f"/categories/{category['id']}"
    )

    assert response.status_code == 401
