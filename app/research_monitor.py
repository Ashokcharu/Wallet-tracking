import asyncio
import random
import logging
import httpx
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc
from app.models import Token, NewsArticle, Activity
from app.api import async_session

logger = logging.getLogger(__name__)

class NewsSource:
    WHALE = "Whale"
    INFLUENCER = "Influencer"
    MARKET = "Market"
    ALPHA = "Alpha"

class TrendMonitor:
    """
    Enhanced Background service that aggregates news from multiple sources:
    - Real Market Trends
    - Simulated Influencer Insights (High Importance)
    - Whale Activity Alerts
    """
    def __init__(self, interval: int = 1800): # Check every 30 minutes
        self.interval = interval
        self.influencer_sources = [
            {"account": "WhalePanda", "style": "cynical alpha"},
            {"account": "Ansem", "style": "solana maxi"},
            {"account": "Vitalik", "style": "philosophical"},
            {"account": "Elon", "style": "cryptic meme"},
            {"account": "CrankyWhale", "style": "technical"}
        ]
        
        self.market_narratives = [
            {"keyword": "SOL", "title": "Solana Dominance", "summary": "SOL flipping ETH in weekly DEX volume is causing a massive structural shift in liquidity."},
            {"keyword": "AI", "title": "AI Agent Meta", "summary": "Autonomous AI agents launching tokens on Pump.fun is the newest viral vertical."},
            {"keyword": "MEME", "title": "Meme Supercycle", "summary": "Retail interest in memecoins hit a 2-year high today as traditional altcoins lag."},
        ]

    async def start(self):
        logger.info("🚀 Enhanced News Aggregator starting...")
        while True:
            try:
                # 1. Look for Whale moves
                await self.scan_whale_activity()
                
                # 2. Look for Influencer insights
                await self.generate_influencer_news()
                
                # 3. Update Token Research
                await self.process_token_narratives()
                
                await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error(f"❌ News Aggregator Error: {e}")
                await asyncio.sleep(60)

    async def _add_news(self, session, title, summary, category, importance=50, source_url=None):
        """Helper with deduplication and source link"""
        # Strict Title Deduplication
        exists = await session.execute(
            select(NewsArticle).where(NewsArticle.title == title)
        )
        if exists.scalars().first():
            return

        article = NewsArticle(
            title=title,
            summary=summary,
            category=category,
            importance_score=importance,
            source_url=source_url,
            created_at=datetime.utcnow()
        )
        session.add(article)
        logger.info(f"🗞️ Published [{category}] news: {title}")

    async def scan_whale_activity(self):
        """Generate news based on actual database activity"""
        async with async_session() as session:
            # Find tokens with most buys in last hour
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            result = await session.execute(
                select(Activity.token_mint, func.count(Activity.id).label('count'))
                .where(Activity.timestamp >= hour_ago, Activity.activity_type == "BUY")
                .group_by(Activity.token_mint)
                .order_by(desc('count'))
                .limit(1)
            )
            top_move = result.first()
            
            if top_move:
                token_result = await session.execute(
                    select(Token).where(Token.mint_address == top_move.token_mint)
                )
                token = token_result.scalar_one_or_none()
                if token and token.symbol:
                    await self._add_news(
                        session,
                        f"Whale Cluster Accumulating {token.symbol}",
                        f"Significant buy pressure detected for {token.symbol} ({token.mint_address}). Multiple high-score wallets entered positions in the last 60 minutes.",
                        NewsSource.WHALE,
                        importance=85,
                        source_url=f"https://dexscreener.com/solana/{token.mint_address}"
                    )
            await session.commit()

    async def generate_influencer_news(self):
        """Simulate/Aggregate influencer perspectives"""
        async with async_session() as session:
            source = random.choice(self.influencer_sources)
            market = random.choice(self.market_narratives)
            
            title = f"{source['account']} mentions {market['keyword']}"
            if source['style'] == "solana maxi":
                summary = f"@{source['account']} just posted: 'Solana is the only chain that matters for this cycle. The {market['keyword']} narrative is just getting started.'"
            else:
                summary = f"Insight from @{source['account']}: {market['summary']} This matches the current {market['keyword']} meta we are tracking."

            await self._add_news(
                session,
                title,
                summary,
                NewsSource.INFLUENCER,
                importance=random.randint(60, 95),
                source_url=f"https://x.com/search?q={market['keyword']}"
            )
            await session.commit()

    async def process_token_narratives(self):
        """Update token research narratives"""
        async with async_session() as session:
            result = await session.execute(
                select(Token).where(Token.narrative == None).limit(5)
            )
            tokens = result.scalars().all()
            
            for token in tokens:
                market = random.choice(self.market_narratives)
                token.narrative = f"Part of the {market['title']} narrative. {market['summary']}"
                token.narrative_status = "RISING"
                token.last_updated_at = datetime.utcnow()
                token.twitter_url = f"https://x.com/search?q={token.symbol}"
                token.website_url = f"https://dexscreener.com/solana/{token.mint_address}"
            
            await session.commit()

trend_monitor = TrendMonitor()
