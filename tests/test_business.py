"""Tests for the /users and /products endpoints."""

import pytest

from tests import counter_value, make_client
from app.config import get_settings
from app.database import get_connection
pytestmark = pytest.mark.asyncio

async def test_users_are_read_from_sqlite() -> None:
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO users (id, name, email, role, active) VALUES (?, ?, ?, ?, ?)",
            (999, "Test Insert", "test.insert@example.com", "viewer", 1),
        )
        connection.commit()
    try:
        async with make_client() as client:
            response = await client.get("/users")
        assert any(user["id"] == 999 for user in response.json())
    finally:
        with get_connection() as connection:
            connection.execute("DELETE FROM users WHERE id = 999")
            connection.commit()
    
async def test_users_returns_500_when_database_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    # A directory is not a valid SQLite file, so every query fails.
    monkeypatch.setattr(get_settings(), "database_path", str(tmp_path))
    async with make_client() as client:
        response = await client.get("/users")

    assert response.status_code == 500
            
async def test_users_returns_list_of_users() -> None:
    async with make_client() as client:
        response = await client.get("/users")

    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list) and len(users) >= 1
    assert {"id", "name", "email", "role", "active"} <= set(users[0])


async def test_products_returns_list_of_products() -> None:
    async with make_client() as client:
        response = await client.get("/products")

    assert response.status_code == 200
    products = response.json()
    assert isinstance(products, list) and len(products) >= 1
    assert {"id", "name", "category", "price", "stock"} <= set(products[0])


async def test_successful_requests_increment_counter() -> None:
    before = counter_value("/users", 200)
    async with make_client() as client:
        await client.get("/users")

    assert counter_value("/users", 200) == before + 1


async def test_unknown_route_is_labelled_unmatched() -> None:
    before = counter_value("unmatched", 404)
    async with make_client() as client:
        response = await client.get("/does-not-exist")

    assert response.status_code == 404
    assert counter_value("unmatched", 404) == before + 1