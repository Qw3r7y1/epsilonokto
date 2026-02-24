"""Tests for upload endpoint — requires running backend + DB.

Run with: pytest app/tests/test_upload.py
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestUploadEndpoint:
    @pytest.mark.asyncio
    async def test_rejects_unsupported_file_type(self, client):
        response = await client.post(
            "/api/v1/upload/",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 400
        assert "Unsupported" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
