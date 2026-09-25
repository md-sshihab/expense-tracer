from datetime import date

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    username = "testuser"
    password = "12345678"

    # Register user
    client.post(
        "/auth/register",
        json={
            "username": username,
            "email": "testuser@example.com",
            "password": password
        }
    )

    # Login user
    response = client.post(
        "/auth/login",
        data={
            "username": username,
            "password": password
        }
    )

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def transaction_data():
    return {
        "title": "Salary",
        "amount": 50000,
        "type": "income",
        "category": "Job",
        "date": str(date.today())
    }


def test_create_transaction(client, auth_headers):

    response = client.post(
        "/transactions",
        json=transaction_data(),
        headers=auth_headers
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Salary"
    assert response.json()["amount"] == 50000
    assert response.json()["owner_id"] > 0


def test_get_transactions(client, auth_headers):

    before = client.get(
        "/transactions",
        headers=auth_headers
    )

    before_count = len(before.json())

    client.post(
        "/transactions",
        json=transaction_data(),
        headers=auth_headers
    )

    response = client.get(
        "/transactions",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert len(response.json()) == before_count + 1


def test_get_specific_transaction(client, auth_headers):

    created = client.post(
        "/transactions",
        json=transaction_data(),
        headers=auth_headers
    )

    transaction_id = created.json()["id"]

    response = client.get(
        f"/transactions/{transaction_id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["id"] == transaction_id


def test_update_transaction(client, auth_headers):

    created = client.post(
        "/transactions",
        json=transaction_data(),
        headers=auth_headers
    )

    transaction_id = created.json()["id"]

    response = client.put(
        f"/transactions/{transaction_id}",
        json={
            "title": "Updated Salary",
            "amount": 55000
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Salary"
    assert response.json()["amount"] == 55000


def test_delete_transaction(client, auth_headers):

    created = client.post(
        "/transactions",
        json=transaction_data(),
        headers=auth_headers
    )

    transaction_id = created.json()["id"]

    response = client.delete(
        f"/transactions/{transaction_id}",
        headers=auth_headers
    )

    assert response.status_code == 200

    response = client.get(
        f"/transactions/{transaction_id}",
        headers=auth_headers
    )

    assert response.status_code == 404