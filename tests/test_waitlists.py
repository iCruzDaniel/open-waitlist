"""Tests for waitlist CRUD endpoints."""

import pytest
from httpx import AsyncClient

from app.config import get_settings


@pytest.mark.anyio
async def test_create_waitlist(client: AsyncClient) -> None:
    response = await client.post(
        "/waitlists",
        json={"slug": "early-access", "title": "Early Access"},
        headers={"X-API-Key": get_settings().api_key},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "early-access"
    assert data["title"] == "Early Access"
    assert data["is_active"] is True
    assert data["entry_count"] == 0


@pytest.mark.anyio
async def test_create_duplicate_slug(client: AsyncClient) -> None:
    headers = {"X-API-Key": get_settings().api_key}
    await client.post(
        "/waitlists",
        json={"slug": "dup", "title": "First"},
        headers=headers,
    )
    response = await client.post(
        "/waitlists",
        json={"slug": "dup", "title": "Second"},
        headers=headers,
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_list_waitlists(client: AsyncClient) -> None:
    headers = {"X-API-Key": get_settings().api_key}
    await client.post("/waitlists", json={"slug": "a", "title": "A"}, headers=headers)
    await client.post("/waitlists", json={"slug": "b", "title": "B"}, headers=headers)

    response = await client.get("/waitlists", headers=headers)
    assert response.status_code == 200
    data = response.json()
    slugs = [w["slug"] for w in data]
    assert "a" in slugs
    assert "b" in slugs


@pytest.mark.anyio
async def test_get_waitlist_by_slug(client: AsyncClient) -> None:
    headers = {"X-API-Key": get_settings().api_key}
    await client.post(
        "/waitlists",
        json={"slug": "my-list", "title": "My List"},
        headers=headers,
    )
    response = await client.get("/waitlists/my-list", headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "My List"


@pytest.mark.anyio
async def test_get_waitlist_not_found(client: AsyncClient) -> None:
    response = await client.get(
        "/waitlists/nonexistent",
        headers={"X-API-Key": get_settings().api_key},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_waitlist(client: AsyncClient) -> None:
    headers = {"X-API-Key": get_settings().api_key}
    await client.post(
        "/waitlists",
        json={"slug": "update-me", "title": "Original"},
        headers=headers,
    )
    response = await client.patch(
        "/waitlists/update-me",
        json={"title": "Updated Title", "description": "New desc"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["description"] == "New desc"


@pytest.mark.anyio
async def test_soft_delete_waitlist(client: AsyncClient) -> None:
    headers = {"X-API-Key": get_settings().api_key}
    await client.post(
        "/waitlists",
        json={"slug": "delete-me", "title": "Delete Me"},
        headers=headers,
    )
    # Delete
    delete_resp = await client.delete("/waitlists/delete-me", headers=headers)
    assert delete_resp.status_code == 204

    # Should not appear in list
    list_resp = await client.get("/waitlists", headers=headers)
    slugs = [w["slug"] for w in list_resp.json()]
    assert "delete-me" not in slugs

    # But still accessible directly (include_inactive)
    get_resp = await client.get("/waitlists/delete-me", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["is_active"] is False


@pytest.mark.anyio
async def test_unauthorized_without_api_key(client: AsyncClient) -> None:
    response = await client.get("/waitlists")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_unauthorized_wrong_api_key(client: AsyncClient) -> None:
    response = await client.get("/waitlists", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


@pytest.mark.anyio
async def test_create_invalid_slug(client: AsyncClient) -> None:
    headers = {"X-API-Key": get_settings().api_key}
    resp = await client.post(
        "/waitlists",
        json={"slug": "INVALID_SLUG", "title": "Bad"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_update_non_existent_waitlist(client: AsyncClient) -> None:
    headers = {"X-API-Key": get_settings().api_key}
    resp = await client.patch(
        "/waitlists/no-such-list",
        json={"title": "Nope"},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_non_existent_waitlist(client: AsyncClient) -> None:
    headers = {"X-API-Key": get_settings().api_key}
    resp = await client.delete("/waitlists/no-such-list", headers=headers)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_waitlist_empty_body(client: AsyncClient) -> None:
    headers = {"X-API-Key": get_settings().api_key}
    await client.post(
        "/waitlists",
        json={"slug": "no-change", "title": "Original"},
        headers=headers,
    )
    resp = await client.patch(
        "/waitlists/no-change",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Original"
