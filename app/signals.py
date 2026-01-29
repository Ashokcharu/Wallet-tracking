"""
Signal Engine v2 - With confidence scoring and cluster validation

Signal Levels:
- WEAK: 1-2 wallets buy
- MODERATE: 3-4 wallets buy  
- STRONG: 5+ high-score wallets, multiple clusters, within 10min

New: Confidence score per signal
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Token, Activity, Wallet, Signal, SignalLevel, TokenCategory
from app.classifier import TokenClassifier

logger = logging.getLogger(__name__)

class SignalEngine:
    
    STRONG_THRESHOLD = 5      # wallets needed for STRONG signal
    HIGH_SCORE_THRESHOLD = 70  # minimum wallet score for STRONG
    MIN_CLUSTERS = 3          # minimum different clusters for STRONG
    TIME_WINDOW_MINUTES = 10   # time window for grouped buys
    
    @classmethod
    async def check_buy_signal(cls, session: AsyncSession, token_mint: str) -> dict:
        """Check if token has a buy signal with confidence score"""
        # Get token to check if DEAD
        token_result = await session.execute(select(Token).where(Token.mint_address == token_mint))
        token = token_result.scalar_one_or_none()
        if token and token.category == TokenCategory.DEAD:
            return {"signal": None, "reason": "Token is DEAD"}
        
        # Get recent buys in last 10 minutes
        time_window = datetime.utcnow() - timedelta(minutes=cls.TIME_WINDOW_MINUTES)
        
        result = await session.execute(
            select(Activity, Wallet).join(
                Wallet, Activity.wallet_address == Wallet.address
            ).where(
                Activity.token_mint == token_mint,
                Activity.activity_type == "BUY",
                Activity.timestamp > time_window
            )
        )
        recent_buys = result.all()
        
        if not recent_buys:
            return {"signal": None}
        
        wallet_count = len(recent_buys)
        high_score_count = sum(1 for _, w in recent_buys if w.score >= cls.HIGH_SCORE_THRESHOLD)
        avg_score = sum(w.score for _, w in recent_buys) / wallet_count if wallet_count > 0 else 0
        
        # Count unique clusters
        cluster_ids = set()
        for _, w in recent_buys:
            if w.cluster_id:
                cluster_ids.add(w.cluster_id)
            else:
                cluster_ids.add(f"solo_{w.address}")  # Treat unclustered as unique
        cluster_count = len(cluster_ids)
        
        # Calculate buy time spread (higher = more organic)
        timestamps = [a.timestamp for a, _ in recent_buys]
        if len(timestamps) > 1:
            time_spread = (max(timestamps) - min(timestamps)).total_seconds() / 60  # minutes
        else:
            time_spread = 0
        
        # Determine signal level with stricter STRONG requirements
        if (high_score_count >= cls.STRONG_THRESHOLD and 
            cluster_count >= cls.MIN_CLUSTERS):
            level = SignalLevel.STRONG
            reason = f"{high_score_count} high-score wallets from {cluster_count} clusters"
        elif wallet_count >= 3:
            level = SignalLevel.MODERATE
            reason = f"{wallet_count} tracked wallets bought recently"
        elif wallet_count >= 1:
            level = SignalLevel.WEAK
            reason = f"{wallet_count} tracked wallet(s) bought"
        else:
            return {"signal": None}
        
        # Calculate confidence score (0-100)
        confidence = cls.calculate_confidence(
            avg_score=avg_score,
            cluster_count=cluster_count,
            time_spread=time_spread,
            wallet_count=wallet_count
        )
        
        return {
            "signal": level,
            "wallet_count": wallet_count,
            "high_score_count": high_score_count,
            "avg_score": round(avg_score, 1),
            "cluster_count": cluster_count,
            "confidence": confidence,
            "reason": reason,
            "first_buy": min(a.timestamp for a, _ in recent_buys)
        }
    
    @staticmethod
    def calculate_confidence(avg_score: float, cluster_count: int, time_spread: float, wallet_count: int) -> int:
        """
        Calculate confidence score (0-100) for a signal
        
        confidence = avg_wallet_score + cluster_diversity + buy_time_spread - rug_risk
        """
        # Base from wallet scores (0-40)
        score_component = min(avg_score * 0.4, 40)
        
        # Cluster diversity bonus (0-25)
        cluster_component = min(cluster_count * 5, 25)
        
        # Time spread bonus - organic buys are spread out (0-20)
        # 5+ minutes spread = max bonus
        spread_component = min(time_spread * 4, 20)
        
        # Volume bonus (0-15)
        volume_component = min(wallet_count * 3, 15)
        
        confidence = score_component + cluster_component + spread_component + volume_component
        return int(min(max(confidence, 0), 100))
    
    @classmethod
    async def check_long_term_signal(cls, session: AsyncSession, token: Token) -> dict:
        """Check if token shows long-term holding signals"""
        # Skip DEAD tokens
        if token.category == TokenCategory.DEAD:
            return {"signal": None}
        
        result = await session.execute(
            select(Activity, Wallet).join(
                Wallet, Activity.wallet_address == Wallet.address
            ).where(
                Activity.token_mint == token.mint_address,
                Activity.activity_type == "BUY",
                Wallet.score >= cls.HIGH_SCORE_THRESHOLD
            )
        )
        high_score_buys = result.all()
        
        if not high_score_buys:
            return {"signal": None}
        
        # Check how many are still holding
        holders = []
        for activity, wallet in high_score_buys:
            sell_result = await session.execute(
                select(Activity).where(
                    Activity.wallet_address == wallet.address,
                    Activity.token_mint == token.mint_address,
                    Activity.activity_type == "SELL",
                    Activity.timestamp > activity.timestamp
                )
            )
            if not sell_result.scalar():
                holders.append((activity, wallet))
        
        if len(holders) < 3:
            return {"signal": None}
        
        hold_times = [(datetime.utcnow() - a.timestamp).total_seconds() / 86400 for a, _ in holders]
        avg_hold = sum(hold_times) / len(hold_times)
        
        long_signals = await TokenClassifier.check_long_term_signals(session, token)
        
        if avg_hold >= 7 and len(holders) >= 3:
            return {
                "signal": "LONG_POTENTIAL",
                "holder_count": len(holders),
                "avg_hold_days": round(avg_hold, 1),
                "avg_score": round(sum(w.score for _, w in holders) / len(holders), 1),
                "reasons": long_signals.get("reasons", []),
                "recommendation": "Consider for long-term portfolio"
            }
        
        return {"signal": None}
    
    @classmethod
    async def check_accumulation_signal(cls, session: AsyncSession, token_mint: str) -> dict:
        """Check if wallets are accumulating (buying multiple times)"""
        result = await session.execute(
            select(
                Activity.wallet_address,
                func.count(Activity.id).label("buy_count"),
                Wallet.score
            ).join(
                Wallet, Activity.wallet_address == Wallet.address
            ).where(
                Activity.token_mint == token_mint,
                Activity.activity_type == "BUY"
            ).group_by(Activity.wallet_address).having(
                func.count(Activity.id) >= 2
            )
        )
        accumulators = result.all()
        
        if not accumulators:
            return {"signal": None}
        
        high_score_accumulators = [a for a in accumulators if a.score >= cls.HIGH_SCORE_THRESHOLD]
        
        if len(high_score_accumulators) >= 2:
            return {
                "signal": "ACCUMULATION",
                "accumulator_count": len(high_score_accumulators),
                "total_repeat_buys": sum(a.buy_count for a in high_score_accumulators),
                "reason": f"{len(high_score_accumulators)} high-score wallets buying multiple times"
            }
        
        return {"signal": None}
    
    @classmethod
    async def save_signal(cls, session: AsyncSession, token_mint: str, signal_data: dict, signal_type: str):
        """Save signal to database"""
        signal = Signal(
            token_mint=token_mint,
            signal_type=signal_type,
            level=signal_data.get("signal", SignalLevel.WEAK),
            wallet_count=signal_data.get("wallet_count", signal_data.get("holder_count", 0)),
            avg_wallet_score=signal_data.get("avg_score", 0),
            reason=signal_data.get("reason", ""),
            notified=False
        )
        session.add(signal)
        return signal
