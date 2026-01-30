import asyncio
import random
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc
from app.models import Token, NewsArticle, Activity
from app.api import async_session

logger = logging.getLogger(__name__)

class TrendMonitor:
    """
    Background service that monitors token activity and generates
    meme narratives and global news articles based on viral trends.
    """
    def __init__(self, interval: int = 3600): # Default 1 hour
        self.interval = interval
        self.trends = [
            {"keyword": "Penguin", "title": "Sad Penguin Viral Moment", "summary": "A viral video of a sad penguin on X has sparked a new wave of seasonal meme tokens."},
            {"keyword": "Mars", "title": "Elon Mars Tweet", "summary": "Elon Musk's latest cryptic tweet about Mars has triggered several planetary-themed launches."},
            {"keyword": "Grok", "title": "Grok 1.5 Update", "summary": "Community-led AI tokens are surging following the latest Grok model release."},
            {"keyword": "Chill", "title": "Chill Guy Narrative", "summary": "The 'Chill Guy' aesthetic is dominating Solana right now, with high retention on themed tokens."},
        ]

    async def start(self):
        logger.info("🚀 Trend Monitor starting...")
        while True:
            try:
                await self.process_trends()
                await self.generate_news()
                await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error(f"❌ Trend Monitor Error: {e}")
                await asyncio.sleep(60)

    async def generate_news(self):
        """Randomly inject viral news articles into the DB"""
        async with async_session() as session:
            # Check if we already have news recently
            now = datetime.utcnow()
            result = await session.execute(
                select(NewsArticle).where(NewsArticle.created_at >= now - timedelta(hours=1))
            )
            if result.scalars().first():
                return

            trend = random.choice(self.trends)
            article = NewsArticle(
                title=trend["title"],
                summary=trend["summary"],
                trend=trend["keyword"],
                created_at=now
            )
            session.add(article)
            await session.commit()
            logger.info(f"🗞️ Published new news: {trend['title']}")

    async def process_trends(self):
        """Update token narratives based on current trends and activity"""
        async with async_session() as session:
            # Get tokens without narratives
            result = await session.execute(
                select(Token).where(Token.narrative == None).limit(10)
            )
            tokens = result.scalars().all()
            
            for token in tokens:
                # Assign a random trend narrative
                trend = random.choice(self.trends)
                token.narrative = f"{trend['summary']} This token appears to be a leading candidate in the #{trend['keyword']} meta."
                token.narrative_status = "RISING"
                token.last_updated_at = datetime.utcnow()
                
                # Mock social links
                token.twitter_url = f"httpss://x.com/search?q={token.symbol}"
                token.website_url = f"https://{token.symbol.replace('$', '').lower()}.fun"
            
            await session.commit()
            if tokens:
                logger.info(f"🧠 Generated narratives for {len(tokens)} tokens")

trend_monitor = TrendMonitor()
