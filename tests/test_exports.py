"""Tests for async CSV export with SSE progress."""

import json

import pytest
from httpx import AsyncClient

from tests.conftest import admin_headers


@pytest.mark.anyio
async def test_export_requires_jwt(client: AsyncClient) -> None:
    """Export endpoints require JWT, not API key."""
    api_key_headers = {"X-API-Key": "changeme-api-key"}

    # POST export with only API key -> 401
    resp = await client.post(
        "/waitlists/x/entries/export",
        headers=api_key_headers,
    )
    assert resp.status_code == 401

    # GET export status with no auth -> 401
    resp = await client.get("/waitlists/x/entries/export/abc123/status")
    assert resp.status_code == 401

    # GET entries list with only API key -> 401
    resp = await client.get("/waitlists/x/entries", headers=api_key_headers)
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_export_full_flow(client: AsyncClient, admin_token: str) -> None:
    """Full export flow: create waitlist, add entries, trigger export, poll SSE, download."""
    jwt = admin_headers(admin_token)
    api_key_headers = {"X-API-Key": "changeme-api-key"}

    # Create waitlist via JWT
    await client.post(
        "/waitlists",
        json={"slug": "export-test", "title": "Export Test"},
        headers=jwt,
    )

    # Add 2 entries via public API key with tricky data
    await client.post(
        "/waitlists/export-test/entries",
        json={"data": {"name": "Ana María", "emoji": "🎉"}},
        headers=api_key_headers,
    )
    await client.post(
        "/waitlists/export-test/entries",
        json={"data": {"name": "Bob", "email": '=HYPERLINK("http://evil")'}},
        headers=api_key_headers,
    )

    # Trigger export
    resp = await client.post(
        "/waitlists/export-test/entries/export",
        headers=jwt,
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    assert job_id

    # Consume SSE until done
    async with client.stream(
        "GET",
        f"/waitlists/export-test/entries/export/{job_id}/status",
        headers=jwt,
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"

        seen_progress = False
        seen_done = False
        download_url = None
        line_count = 0

        async for line in resp.aiter_lines():
            line_count += 1
            if line_count > 200:
                break

            if not line or line.startswith(":"):
                continue

            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                try:
                    payload = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                if event_type == "progress":
                    seen_progress = True
                    assert payload["progress"] >= 0
                    assert payload["progress"] <= 100
                elif event_type == "done":
                    seen_done = True
                    assert payload["progress"] == 100
                    download_url = payload.get("download_url")
                    break
                elif event_type == "error":
                    pytest.fail(f"Export error: {payload.get('message')}")

        assert seen_progress, "Should have seen progress event"
        assert seen_done, "Should have seen done event"
        assert download_url, "Done event should have download_url"

    # Download the CSV
    resp = await client.get(download_url, headers=jwt)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")

    body = resp.text
    # Check BOM
    assert body.startswith("\ufeff"), "CSV should start with UTF-8 BOM"

    # Check content
    assert "Ana María" in body
    assert "'=HYPERLINK" in body  # sanitized
    assert "name" in body  # header
    assert "emoji" in body  # header


@pytest.mark.anyio
async def test_export_nonexistent_waitlist(client: AsyncClient, admin_token: str) -> None:
    """Export for non-existent waitlist returns 404."""
    jwt = admin_headers(admin_token)
    resp = await client.post(
        "/waitlists/nonexistent-waitlist/entries/export",
        headers=jwt,
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_export_download_unknown_job(client: AsyncClient, admin_token: str) -> None:
    """Download/status for unknown job returns 404."""
    jwt = admin_headers(admin_token)

    # Unknown job status
    resp = await client.get(
        "/waitlists/any/entries/export/unknown-job-id/status",
        headers=jwt,
    )
    assert resp.status_code == 404

    # Unknown job download
    resp = await client.get(
        "/waitlists/any/entries/export/unknown-job-id/download",
        headers=jwt,
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_export_empty_waitlist(client: AsyncClient, admin_token: str) -> None:
    """Export empty waitlist produces header-only CSV."""
    jwt = admin_headers(admin_token)

    # Create waitlist, no entries
    await client.post(
        "/waitlists",
        json={"slug": "empty-export", "title": "Empty Export"},
        headers=jwt,
    )

    # Trigger export
    resp = await client.post(
        "/waitlists/empty-export/entries/export",
        headers=jwt,
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    # Consume SSE until done
    async with client.stream(
        "GET",
        f"/waitlists/empty-export/entries/export/{job_id}/status",
        headers=jwt,
    ) as resp:
        assert resp.status_code == 200

        seen_done = False
        download_url = None
        line_count = 0

        async for line in resp.aiter_lines():
            line_count += 1
            if line_count > 200:
                break

            if not line or line.startswith(":"):
                continue

            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                try:
                    payload = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                if event_type == "done":
                    seen_done = True
                    download_url = payload.get("download_url")
                    break
                elif event_type == "error":
                    pytest.fail(f"Export error: {payload.get('message')}")

        assert seen_done, "Should have seen done event"
        assert download_url, "Done event should have download_url"

    # Download the CSV
    resp = await client.get(download_url, headers=jwt)
    assert resp.status_code == 200

    body = resp.text
    assert body.startswith("\ufeff"), "CSV should start with UTF-8 BOM"
    # Header only: id,email,referrer,created_at
    lines = body.strip().split("\n")
    assert len(lines) == 1
    assert lines[0] == "\ufeffid,email,referrer,created_at"
