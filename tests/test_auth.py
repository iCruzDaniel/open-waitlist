"""Tests for auth endpoints (login, me)."""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_login_success(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "changeme-admin-password",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_wrong_password(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "wrong-password",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.anyio
async def test_login_wrong_email(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "changeme-admin-password",
        },
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_me_with_valid_token(client: AsyncClient) -> None:
    login_resp = await client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "changeme-admin-password",
        },
    )
    token = login_resp.json()["access_token"]

    me_resp = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "admin@example.com"
    assert "id" in me_data


@pytest.mark.anyio
async def test_me_no_token(client: AsyncClient) -> None:
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_me_invalid_token(client: AsyncClient) -> None:
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
