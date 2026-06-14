import time

from tests.helpers import client


def test_register_user():
    username = f"test_user_{time.time()}"
    email = f"{username}@example.com"

    response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "123456"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["username"] == username
    assert data["email"] == email
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data

def test_login_user():
    username = f"login_user_{time.time()}"
    email = f"{username}@example.com"
    password = "123456"

    register_response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password
        }
    )

    assert register_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        data={
            "username": username,
            "password": password
        }
    )

    assert login_response.status_code == 200

    data = login_response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_get_current_user():
    username = f"me_user_{time.time()}"
    email = f"{username}@example.com"
    password = "123456"

    register_response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password
        }
    )

    assert register_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        data={
            "username": username,
            "password": password
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    me_response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert me_response.status_code == 200

    data = me_response.json()

    assert data["username"] == username
    assert data["email"] == email
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data

def test_register_user_cannot_create_admin():
    response = client.post(
        "/auth/register",
        json={
            "username": f"not_admin_{time.time()}",
            "email": f"not_admin_{time.time()}@example.com",
            "password": "123456",
            "role": "admin"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["role"] == "customer"
