import httpx
import pytest
import asyncio
from app.api import app
from app.models import Wallet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

API_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_api_stats():
    """Verify the statistics endpoint is working"""
    async with httpx.AsyncClient(base_url=API_URL) as ac:
        try:
            response = await ac.get("/api/stats")
            assert response.status_code == 200
            data = response.json()
            assert "wallets" in data
            assert "tokens" in data
        except httpx.ConnectError:
            pytest.fail("API server not running. Start main.py first.")

@pytest.mark.asyncio
async def test_wallet_upload():
    """Verify wallet upload via API"""
    test_wallets = {
        "wallets": [
            {"address": "9ZPsRWGkJsKxN3yzV5tVmQeXdExdB3sZ5o7z8qXnvW4D", "label": "TestWhale"},
            {"address": "ASTyfSim4Bk3p6SbPQdTDqNbJR8e3LxPvPbNwcQxJq9A", "label": "TestTrader"}
        ]
    }
    async with httpx.AsyncClient(base_url=API_URL) as ac:
        response = await ac.post("/api/wallets/upload", json=test_wallets)
        assert response.status_code == 200
        data = response.json()
        assert data["added"] >= 0  # Might be 0 if already in DB
        assert data["total"] == 2

@pytest.mark.asyncio
async def test_tokens_endpoint():
    """Verify high-potential tokens list"""
    async with httpx.AsyncClient(base_url=API_URL) as ac:
        response = await ac.get("/api/tokens")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_db_sync_verification():
    """Verify uploaded wallets exist in the Database"""
    from dotenv import load_dotenv
    import os
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./walletracker.db")
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        result = await session.execute(
            select(Wallet).where(Wallet.address == "9ZPsRWGkJsKxN3yzV5tVmQeXdExdB3sZ5o7z8qXnvW4D")
        )
        wallet = result.scalar_one_or_none()
        assert wallet is not None
        assert wallet.label == "TestWhale"
