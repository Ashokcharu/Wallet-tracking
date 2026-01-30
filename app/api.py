"""
FastAPI REST API for walleTracker Frontend
Provides endpoints for tokens, signals, wallets
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from app.models import Wallet, Token, Activity, Signal, SignalLevel

load_dotenv()

app = FastAPI(title="WalleTracker API", version="2.1")

# CORS for GitHub Pages frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your GitHub Pages URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./walletracker.db")
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Pydantic Models
class WalletUpload(BaseModel):
    wallets: List[dict]

class TokenResponse(BaseModel):
    mint_address: str
    symbol: Optional[str]
    category: str
    moonshot_score: int
    wallet_count: int
    hold_ratio: int
    volume_pct: float
    first_seen_at: datetime

class SignalResponse(BaseModel):
    token_symbol: str
    level: str
    wallet_count: int
    confidence: int
    created_at: datetime

class WalletResponse(BaseModel):
    score: float

class NewsResponse(BaseModel):
    id: int
    title: str
    summary: str
    trend: str
    created_at: datetime

class ResearchResponse(BaseModel):
    mint_address: str
    symbol: Optional[str]
    narrative: str
    twitter_url: Optional[str]
    website_url: Optional[str]
    status: str
    last_updated: datetime

# API Endpoints
@app.get("/api/tokens", response_model=List[TokenResponse])
async def get_tokens():
    """Get high-potential tokens ranked by moonshot score"""
    async with async_session() as session:
        # Get tokens with activity in last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        result = await session.execute(
            select(Token).where(Token.first_seen_at >= week_ago)
        )
        tokens = result.scalars().all()
        
        token_list = []
        for token in tokens:
            # Get unique wallet count
            wallet_result = await session.execute(
                select(func.count(func.distinct(Activity.wallet_address)))
                .where(Activity.token_mint == token.mint_address, Activity.activity_type == "BUY")
            )
            wallet_count = wallet_result.scalar() or 0
            
            # Get wallets still holding (no sell after buy)
            holds_result = await session.execute(
                select(func.count(func.distinct(Activity.wallet_address)))
                .where(
                    Activity.token_mint == token.mint_address,
                    Activity.activity_type == "BUY",
                    Activity.sold_at == None
                )
            )
            hold_count = holds_result.scalar() or 0
            hold_ratio = int((hold_count / wallet_count * 100) if wallet_count > 0 else 0)
            
            # Calculate moonshot score
            moonshot_score = calculate_moonshot_score(wallet_count, hold_ratio, token)
            
            # Determine category
            category = get_token_category(moonshot_score, token)
            
            token_list.append(TokenResponse(
                mint_address=token.mint_address,
                symbol=token.symbol,
                category=category,
                moonshot_score=moonshot_score,
                wallet_count=wallet_count,
                hold_ratio=hold_ratio,
                volume_pct=0.0, # Placeholder for now
                first_seen_at=token.first_seen_at or datetime.utcnow()
            ))
        
        # Calculate Volume Percentage
        total_token_buys = sum(t.wallet_count for t in token_list)
        for t in token_list:
            if total_token_buys > 0:
                t.volume_pct = round((t.wallet_count / total_token_buys) * 100, 1)
        
        # Sort by moonshot score
        token_list.sort(key=lambda x: x.moonshot_score, reverse=True)
        return token_list[:50]

@app.get("/api/signals", response_model=List[SignalResponse])
async def get_signals():
    """Get recent signals"""
    async with async_session() as session:
        result = await session.execute(
            select(Signal).order_by(desc(Signal.created_at)).limit(20)
        )
        signals = result.scalars().all()
        
        signal_list = []
        for sig in signals:
            # Get token symbol
            token_result = await session.execute(
                select(Token).where(Token.mint_address == sig.token_mint)
            )
            token = token_result.scalar_one_or_none()
            
            signal_list.append(SignalResponse(
                token_symbol=token.symbol if token else "UNKNOWN",
                level=sig.level.value if hasattr(sig.level, 'value') else str(sig.level),
                wallet_count=sig.wallet_count,
                confidence=sig.confidence or 50,
                created_at=sig.created_at
            ))
        
        return signal_list

@app.get("/api/wallets", response_model=List[WalletResponse])
async def get_wallets():
    """Get top wallets by score"""
    async with async_session() as session:
        result = await session.execute(
            select(Wallet).where(Wallet.active == True)
            .order_by(desc(Wallet.score))
            .limit(50)
        )
        wallets = result.scalars().all()
        
        return [
            WalletResponse(
                address=w.address,
                label=w.label,
                score=w.score or 0
            ) for w in wallets
        ]

@app.post("/api/wallets/upload")
async def upload_wallets(data: WalletUpload):
    """Upload wallets from frontend"""
    async with async_session() as session:
        added = 0
        for wallet_data in data.wallets:
            address = wallet_data.get("address", "").strip()
            label = wallet_data.get("label")
            
            if not address or len(address) < 32:
                continue
            
            # Check if exists
            result = await session.execute(
                select(Wallet).where(Wallet.address == address)
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                wallet = Wallet(address=address, label=label, active=True)
                session.add(wallet)
                added += 1
            else:
                existing.active = True
                if label:
                    existing.label = label
        
        await session.commit()
        return {"added": added, "total": len(data.wallets)}

@app.get("/api/news", response_model=List[NewsResponse])
async def get_news():
    """Get trending meme news"""
    from app.models import NewsArticle
    async with async_session() as session:
        result = await session.execute(
            select(NewsArticle).order_by(desc(NewsArticle.created_at)).limit(10)
        )
        articles = result.scalars().all()
        return [
            NewsResponse(
                id=a.id,
                title=a.title,
                summary=a.summary,
                trend=a.trend,
                created_at=a.created_at
            ) for a in articles
        ]

@app.get("/api/tokens/{mint}/research", response_model=ResearchResponse)
async def get_token_research(mint: str):
    """Get deep research for a specific token"""
    async with async_session() as session:
        result = await session.execute(
            select(Token).where(Token.mint_address == mint)
        )
        token = result.scalar_one_or_none()
        
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")
            
        return ResearchResponse(
            mint_address=token.mint_address,
            symbol=token.symbol,
            narrative=token.narrative or "No narrative data available yet. Our background monitor is tracking this token.",
            twitter_url=token.twitter_url,
            website_url=token.website_url,
            status=token.narrative_status or "NEW",
            last_updated=token.last_updated_at or datetime.utcnow()
        )

@app.get("/api/stats")
async def get_stats():
    """Get dashboard stats"""
    async with async_session() as session:
        wallet_count = await session.execute(
            select(func.count()).select_from(Wallet).where(Wallet.active == True)
        )
        token_count = await session.execute(
            select(func.count()).select_from(Token)
        )
        signal_count = await session.execute(
            select(func.count()).select_from(Signal)
        )
        
        return {
            "wallets": wallet_count.scalar() or 0,
            "tokens": token_count.scalar() or 0,
            "signals": signal_count.scalar() or 0
        }

# Helper Functions
def calculate_moonshot_score(wallet_count: int, hold_ratio: int, token: Token) -> int:
    """
    Calculate moonshot score (0-100)
    
    Factors:
    - Early Volume (30%): Multiple wallets in first 24h
    - Whale Interest (25%): High-score wallets holding
    - Cluster Diversity (20%): Wallets from different clusters
    - Hold Ratio (15%): % still holding
    - Signal Strength (10%): STRONG signals triggered
    """
    score = 0
    
    # Early volume (0-30)
    volume_score = min(wallet_count * 4, 30)
    
    # Hold ratio (0-15)
    hold_score = hold_ratio * 0.15
    
    # Base activity score (0-40)
    activity_score = min(wallet_count * 2 + hold_ratio * 0.2, 40)
    
    # Age bonus (newer = higher potential)
    if token.first_seen_at:
        hours_old = (datetime.utcnow() - token.first_seen_at).total_seconds() / 3600
        if hours_old < 24:
            age_bonus = 15
        elif hours_old < 72:
            age_bonus = 10
        else:
            age_bonus = 0
    else:
        age_bonus = 0
    
    score = int(volume_score + hold_score + activity_score + age_bonus)
    return min(max(score, 0), 100)

def get_token_category(moonshot_score: int, token: Token) -> str:
    """Categorize token by score"""
    if moonshot_score >= 80:
        return "MOONSHOT"
    elif moonshot_score >= 60:
        return "RISING"
    elif moonshot_score >= 40:
        return "WATCHLIST"
    else:
        return "DEAD"

# Serve static files (frontend)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
