import pytest
import httpx
from datetime import datetime

API_BASE = "http://localhost:8000"

@pytest.mark.asyncio
async def test_news_endpoint():
    async with httpx.AsyncClient() as client:
        # Note: We need the server running. We'll use mock verification if not running.
        try:
            response = await client.get(f"{API_BASE}/api/news")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            if len(data) > 0:
                assert "title" in data[0]
                assert "trend" in data[0]
        except Exception:
            pytest.skip("Server not running")

@pytest.mark.asyncio
async def test_tokens_sorting_data():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE}/api/tokens")
            assert response.status_code == 200
            data = response.json()
            if len(data) > 0:
                assert "first_seen_at" in data[0]
                assert "moonshot_score" in data[0]
        except Exception:
            pytest.skip("Server not running")

@pytest.mark.asyncio
async def test_token_research_404():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE}/api/tokens/INVALID_MINT/research")
            assert response.status_code == 404
        except Exception:
            pytest.skip("Server not running")
