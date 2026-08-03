"""Tests for waitlist CRUD endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest import admin_headers


@pytest.mark.anyio
async def test_create_waitlist(client: AsyncClient, admin_token: str) -> None:
    jwt = admin_headers(admin_token)
    response = await client.post(
        "/waitlists",
        json={"slug": "early-access", "title": "Early Access"},
        headers=jwt,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "early-access"
    assert data["title"] == "Early Access"
    assert data["is_active"] is True
    assert data["entry_count"] == 0


@pytest.mark.anyio
async def test_create_duplicate_slug(client: AsyncClient, admin_token: str) -> None:
    jwt = admin_headers(admin_token)
    await client.post(
        "/waitlists",
        json={"slug": "dup", "title": "First"},
        headers=jwt,
    )
    response = await client.post(
        "/waitlists",
        json={"slug": "dup", "title": "Second"},
        headers=jwt,
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_list_waitlists(client: AsyncClient, admin_token: str) -> None:
    jwt = admin_headers(admin_token)
    await client.post("/waitlists", json={"slug": "a", "title": "A"}, headers=jwt)
    await client.post("/waitlists", json={"slug": "b", "title": "B"}, headers=jwt)

    response = await client.get("/waitlists", headers=jwt)
    assert response.status_code == 200
    data = response.json()
    slugs = [w["slug"] for w in data]
    assert "a" in slugs
    assert "b" in slugs


@pytest.mark.anyio
async def test_get_waitlist_by_slug(client: AsyncClient, admin_token: str) -> None:
    jwt = admin_headers(admin_token)
    await client.post(
        "/waitlists",
        json={"slug": "my-list", "title": "My List"},
        headers=jwt,
    )
    response = await client.get("/waitlists/my-list", headers=jwt)
    assert response.status_code == 200
    assert response.json()["title"] == "My List"


@pytest.mark.anyio
async def test_get_waitlist_not_found(client: AsyncClient, admin_token: str) -> None:
    jwt = admin_headers(admin_token)
    response = await client.get(
        "/waitlists/nonexistent",
        headers=jwt,
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_waitlist(client: AsyncClient, admin_token: str) -> None:
    jwt = admin_headers(admin_token)
    await client.post(
        "/waitlists",
        json={"slug": "update-me", "title": "Original"},
        headers=jwt,
    )
    response = await client.patch(
        "/waitlists/update-me",
        json={"title": "Updated Title", "description": "New desc"},
        headers=jwt,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["description"] == "New desc"


@pytest.mark.anyio
async def test_soft_delete_waitlist(client: AsyncClient, admin_token: str) -> None:
    jwt = admin_headers(admin_token)
    await client.post(
        "/waitlists",
        json={"slug": "delete-me", "title": "Delete Me"},
        headers=jwt,
    )
    # Delete
    delete_resp = await client.delete("/waitlists/delete-me", headers=jwt)
    assert delete_resp.status_code == 204

    # Should not appear in list
    list_resp = await client.get("/waitlists", headers=jwt)
    slugs = [w["slug"] for w in list_resp.json()]
    assert "delete-me" not in slugs

    # But still accessible directly (include_inactive)
    get_resp = await client.get("/waitlists/delete-me", headers=jwt)
    assert get_resp.status_code == 200
    assert get_resp.json()["is_active"] is False


@pytest.mark.anyio
async def test_unauthorized_without_jwt(client: AsyncClient) -> None:
    response = await client.get("/waitlists")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_unauthorized_wrong_jwt(client: AsyncClient) -> None:
    response = await client.get("/waitlists", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401


@pytest.mark.anyio
async def test_create_invalid_slug(client: AsyncClient, admin_token: str) -> None:
    jwt = admin_headers(admin_token)
    resp = await client.post(
        "/waitlists",
        json={"slug": "INVALID_SLUG", "title": "Bad"},
        headers=jwt,
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_update_non_existent_waitlist(client: AsyncClient, admin_token: str) -> None:
    jwt = admin_headers(admin_token)
    resp = await client.patch(
        "/waitlists/no-such-list",
        json={"title": "Nope"},
        headers=jwt,
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_non_existent_waitlist(client: AsyncClient, admin_token: str) -> None:
    jwt = admin_headers(admin_token)
    resp = await client.delete("/waitlists/no-such-list", headers=jwt)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_waitlist_empty_body(client: AsyncClient, admin_token: str) -> None:
    jwt = admin_headers(admin_token)
    await client.post(
        "/waitlists",
        json={"slug": "no-change", "title": "Original"},
        headers=jwt,
    )
    resp = await client.patch(
        "/waitlists/no-change",
        json={},
        headers=jwt,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Original"
