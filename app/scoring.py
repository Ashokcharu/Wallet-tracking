"""
Wallet Scoring Engine v2 - Dual scoring with lifetime + recent performance

Formula:
final_score = 0.7 * lifetime_score + 0.3 * recent_score

Where:
- lifetime_score = full history
- recent_score = last 14 days only (for adaptability)
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Wallet, Activity, Token

logger = logging.getLogger(__name__)

RECENT_DAYS = 14  # Window for recent_score

class ScoringEngine:
    # Weights from research
    WEIGHT_EARLY_BUY = 0.25
    WEIGHT_PROFIT = 0.30
    WEIGHT_CONSISTENCY = 0.20
    WEIGHT_INFLUENCE = 0.15
    WEIGHT_NOISE = 0.10
    
    # Dual score weights
    LIFETIME_WEIGHT = 0.7
    RECENT_WEIGHT = 0.3
    
    @staticmethod
    def calculate_early_buy_percentile(token_first_seen: datetime, buy_time: datetime, total_buys: int, buy_position: int) -> float:
        """
        Calculate early-buy score as percentile (not binary)
        Returns 1.0 if first 5%, 0.7 if first 10%, 0.4 if first 20%, else 0
        """
        if total_buys == 0:
            return 1.0  # First buyer
        
        percentile = buy_position / total_buys
        
        if percentile <= 0.05:
            return 1.0
        elif percentile <= 0.10:
            return 0.7
        elif percentile <= 0.20:
            return 0.4
        else:
            return 0.0
    
    @staticmethod
    async def calculate_early_buy_rate(session: AsyncSession, wallet_address: str, since: datetime = None) -> float:
        """Calculate average early-buy percentile score"""
        query = select(Activity).where(
            Activity.wallet_address == wallet_address,
            Activity.activity_type == "BUY"
        )
        if since:
            query = query.where(Activity.timestamp >= since)
        
        result = await session.execute(query)
        buys = result.scalars().all()
        if not buys:
            return 0.0
        
        scores = []
        for buy in buys:
            # Get buy position for this token
            position_result = await session.execute(
                select(func.count(Activity.id)).where(
                    Activity.token_mint == buy.token_mint,
                    Activity.activity_type == "BUY",
                    Activity.timestamp < buy.timestamp
                )
            )
            position = position_result.scalar() or 0
            
            total_result = await session.execute(
                select(func.count(Activity.id)).where(
                    Activity.token_mint == buy.token_mint,
                    Activity.activity_type == "BUY"
                )
            )
            total = total_result.scalar() or 1
            
            token_result = await session.execute(
                select(Token.first_seen_at).where(Token.mint_address == buy.token_mint)
            )
            first_seen = token_result.scalar()
            
            score = ScoringEngine.calculate_early_buy_percentile(
                first_seen or buy.timestamp, buy.timestamp, total, position
            )
            scores.append(score)
        
        return (sum(scores) / len(scores)) * 100 if scores else 0
    
    @staticmethod
    async def calculate_avg_profit(session: AsyncSession, wallet_address: str, since: datetime = None) -> float:
        """Calculate average profit % across all closed trades"""
        query = select(Activity).where(
            Activity.wallet_address == wallet_address,
            Activity.activity_type == "SELL",
            Activity.profit_pct.isnot(None)
        )
        if since:
            query = query.where(Activity.timestamp >= since)
        
        result = await session.execute(query)
        sells = result.scalars().all()
        if not sells:
            return 0.0
        
        avg = sum(s.profit_pct for s in sells) / len(sells)
        # Normalize to 0-100 scale (cap at 200% profit = 100 score)
        return min(max(avg / 2, 0), 100)
    
    @staticmethod
    async def calculate_consistency(session: AsyncSession, wallet_address: str, since: datetime = None) -> float:
        """Measure trading consistency over time"""
        query = select(Activity).where(
            Activity.wallet_address == wallet_address
        ).order_by(Activity.timestamp)
        if since:
            query = query.where(Activity.timestamp >= since)
        
        result = await session.execute(query)
        activities = result.scalars().all()
        if len(activities) < 2:
            return 0.0
        
        intervals = []
        for i in range(1, len(activities)):
            delta = (activities[i].timestamp - activities[i-1].timestamp).total_seconds() / 3600
            intervals.append(delta)
        
        if not intervals:
            return 0.0
        
        avg_interval = sum(intervals) / len(intervals)
        # Regular trading (every 6-24h) scores highest
        if 6 <= avg_interval <= 24:
            return 100
        elif avg_interval < 6:
            return 70  # Very active, might be bot
        else:
            return max(0, 100 - (avg_interval - 24) * 2)
    
    @staticmethod
    async def calculate_influence(session: AsyncSession, wallet_address: str, wallet_cluster_id: int = None, since: datetime = None) -> float:
        """
        Cross-cluster influence: How often do OTHER clusters follow this wallet?
        Excludes same-cluster wallets to prevent bot ring inflation.
        """
        query = select(Activity.token_mint, Activity.timestamp).where(
            Activity.wallet_address == wallet_address,
            Activity.activity_type == "BUY"
        )
        if since:
            query = query.where(Activity.timestamp >= since)
        
        result = await session.execute(query)
        wallet_buys = result.all()
        
        if not wallet_buys:
            return 0.0
        
        followers = 0
        for token_mint, buy_time in wallet_buys:
            # Count other wallets that bought same token within 30 min after
            # EXCLUDING same cluster
            follow_query = select(func.count(Activity.id)).select_from(
                Activity
            ).join(
                Wallet, Activity.wallet_address == Wallet.address
            ).where(
                Activity.token_mint == token_mint,
                Activity.activity_type == "BUY",
                Activity.wallet_address != wallet_address,
                Activity.timestamp > buy_time,
                Activity.timestamp < buy_time + timedelta(minutes=30)
            )
            
            # Exclude same cluster if wallet has one
            if wallet_cluster_id:
                follow_query = follow_query.where(
                    (Wallet.cluster_id != wallet_cluster_id) | (Wallet.cluster_id.is_(None))
                )
            
            follow_result = await session.execute(follow_query)
            followers += follow_result.scalar() or 0
        
        # Normalize: 10+ followers per trade = max score
        return min((followers / len(wallet_buys)) * 10, 100)
    
    @staticmethod
    async def calculate_noise(session: AsyncSession, wallet_address: str, since: datetime = None) -> float:
        """Penalty for low-impact random trades"""
        query = select(Activity).where(
            Activity.wallet_address == wallet_address,
            Activity.activity_type == "SELL",
            Activity.profit_pct.isnot(None)
        )
        if since:
            query = query.where(Activity.timestamp >= since)
        
        result = await session.execute(query)
        sells = result.scalars().all()
        if not sells:
            return 0.0
        
        noise_trades = sum(1 for s in sells if s.profit_pct < -10)
        noise_ratio = noise_trades / len(sells)
        return noise_ratio * 100
    
    @classmethod
    async def calculate_score_components(cls, session: AsyncSession, wallet_address: str, cluster_id: int = None, since: datetime = None) -> dict:
        """Calculate all score components for a given time period"""
        early_buy = await cls.calculate_early_buy_rate(session, wallet_address, since)
        profit = await cls.calculate_avg_profit(session, wallet_address, since)
        consistency = await cls.calculate_consistency(session, wallet_address, since)
        influence = await cls.calculate_influence(session, wallet_address, cluster_id, since)
        noise = await cls.calculate_noise(session, wallet_address, since)
        
        score = (
            cls.WEIGHT_EARLY_BUY * early_buy +
            cls.WEIGHT_PROFIT * profit +
            cls.WEIGHT_CONSISTENCY * consistency +
            cls.WEIGHT_INFLUENCE * influence -
            cls.WEIGHT_NOISE * noise
        )
        
        return {
            "score": round(max(0, min(score, 100)), 2),
            "early_buy_rate": round(early_buy, 2),
            "avg_profit_pct": round(profit, 2),
            "consistency": round(consistency, 2),
            "influence": round(influence, 2),
            "noise_penalty": round(noise, 2)
        }
    
    @classmethod
    async def calculate_wallet_score(cls, session: AsyncSession, wallet_address: str, cluster_id: int = None) -> dict:
        """
        Dual score system:
        final_score = 0.7 * lifetime_score + 0.3 * recent_score
        """
        # Lifetime score (all time)
        lifetime = await cls.calculate_score_components(session, wallet_address, cluster_id)
        
        # Recent score (last 14 days)
        recent_cutoff = datetime.utcnow() - timedelta(days=RECENT_DAYS)
        recent = await cls.calculate_score_components(session, wallet_address, cluster_id, recent_cutoff)
        
        # Weighted final score
        final_score = (
            cls.LIFETIME_WEIGHT * lifetime["score"] +
            cls.RECENT_WEIGHT * recent["score"]
        )
        
        return {
            "score": round(max(0, min(final_score, 100)), 2),
            "lifetime_score": lifetime["score"],
            "recent_score": recent["score"],
            "early_buy_rate": lifetime["early_buy_rate"],
            "avg_profit_pct": lifetime["avg_profit_pct"],
            "consistency": lifetime["consistency"],
            "influence": lifetime["influence"],
            "noise_penalty": lifetime["noise_penalty"]
        }
    
    @classmethod
    async def update_wallet_score(cls, session: AsyncSession, wallet: Wallet):
        """Update wallet scoring fields in database"""
        scores = await cls.calculate_wallet_score(session, wallet.address, wallet.cluster_id)
        
        wallet.score = scores["score"]
        wallet.early_buy_rate = scores["early_buy_rate"]
        wallet.avg_profit_pct = scores["avg_profit_pct"]
        wallet.consistency = scores["consistency"]
        wallet.influence = scores["influence"]
        wallet.noise_penalty = scores["noise_penalty"]
        
        logger.info(f"Score {wallet.address[:8]}...: {scores['score']} (L:{scores['lifetime_score']} R:{scores['recent_score']})")
        return scores
