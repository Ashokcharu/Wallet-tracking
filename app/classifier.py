"""
Token Classifier v2 - With DEAD category detection

Categories:
- MEME_SHORT: <7 days, quick flip
- MEME_LONG: 7-30 days, building momentum  
- LONG_POTENTIAL: 30+ days, wallets holding
- BLUE_CHIP: Established tokens
- DEAD: Liquidity dropped, no buys, exit signals
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Token, Activity, TokenCategory

logger = logging.getLogger(__name__)

# DEAD token thresholds
DEAD_NO_BUYS_HOURS = 48  # No buys in 48 hours
DEAD_HOLD_RATIO_DROP = 30  # Under 30% holders remaining

class TokenClassifier:
    
    @staticmethod
    async def get_token_age_days(token: Token) -> float:
        """Get token age in days since first seen"""
        if not token.first_seen_at:
            return 0
        delta = datetime.utcnow() - token.first_seen_at
        return delta.total_seconds() / 86400
    
    @staticmethod
    async def calculate_hold_ratio(session: AsyncSession, token_mint: str) -> float:
        """Calculate % of buyers who still hold"""
        buyers_result = await session.execute(
            select(func.count(func.distinct(Activity.wallet_address))).where(
                Activity.token_mint == token_mint,
                Activity.activity_type == "BUY"
            )
        )
        total_buyers = buyers_result.scalar() or 0
        
        if total_buyers == 0:
            return 0.0
        
        sellers_result = await session.execute(
            select(func.count(func.distinct(Activity.wallet_address))).where(
                Activity.token_mint == token_mint,
                Activity.activity_type == "SELL"
            )
        )
        total_sellers = sellers_result.scalar() or 0
        
        holders = total_buyers - total_sellers
        return max(0, (holders / total_buyers) * 100)
    
    @staticmethod
    async def calculate_avg_hold_days(session: AsyncSession, token_mint: str) -> float:
        """Calculate average hold time for this token"""
        buys_result = await session.execute(
            select(Activity).where(
                Activity.token_mint == token_mint,
                Activity.activity_type == "BUY"
            )
        )
        buys = buys_result.scalars().all()
        
        if not buys:
            return 0.0
        
        hold_times = []
        for buy in buys:
            if buy.sold_at:
                hold_time = (buy.sold_at - buy.timestamp).total_seconds() / 86400
            else:
                hold_time = (datetime.utcnow() - buy.timestamp).total_seconds() / 86400
            hold_times.append(hold_time)
        
        return sum(hold_times) / len(hold_times) if hold_times else 0
    
    @staticmethod
    async def check_is_dead(session: AsyncSession, token: Token) -> bool:
        """Check if token should be marked DEAD"""
        # Check 1: No buys in last 48 hours
        cutoff = datetime.utcnow() - timedelta(hours=DEAD_NO_BUYS_HOURS)
        recent_buys = await session.execute(
            select(func.count(Activity.id)).where(
                Activity.token_mint == token.mint_address,
                Activity.activity_type == "BUY",
                Activity.timestamp >= cutoff
            )
        )
        if (recent_buys.scalar() or 0) == 0:
            return True
        
        # Check 2: Hold ratio crashed
        hold_ratio = await TokenClassifier.calculate_hold_ratio(session, token.mint_address)
        if hold_ratio < DEAD_HOLD_RATIO_DROP:
            return True
        
        return False
    
    @classmethod
    async def classify_token(cls, session: AsyncSession, token: Token) -> str:
        """Classify token into category based on metrics"""
        age_days = await cls.get_token_age_days(token)
        hold_ratio = await cls.calculate_hold_ratio(session, token.mint_address)
        avg_hold_days = await cls.calculate_avg_hold_days(session, token.mint_address)
        
        # Update token metrics
        token.hold_ratio = hold_ratio
        token.avg_hold_days = avg_hold_days
        
        # Check DEAD first
        is_dead = await cls.check_is_dead(session, token)
        if is_dead:
            token.category = TokenCategory.DEAD
            logger.info(f"Token {token.mint_address[:8]}... marked DEAD")
            return TokenCategory.DEAD
        
        # Classification logic
        if age_days < 7:
            category = TokenCategory.MEME_SHORT
        elif age_days < 30:
            if hold_ratio > 50 and avg_hold_days > 3:
                category = TokenCategory.MEME_LONG
            else:
                category = TokenCategory.MEME_SHORT
        else:
            if hold_ratio > 70 and avg_hold_days > 7:
                category = TokenCategory.LONG_POTENTIAL
            elif hold_ratio > 80 and avg_hold_days > 30:
                category = TokenCategory.BLUE_CHIP
            else:
                category = TokenCategory.MEME_LONG
        
        token.category = category
        logger.debug(f"Token {token.mint_address[:8]}... classified as {category}")
        return category
    
    @classmethod
    async def check_long_term_signals(cls, session: AsyncSession, token: Token) -> dict:
        """Check if token shows long-term potential signals"""
        age_days = await cls.get_token_age_days(token)
        hold_ratio = await cls.calculate_hold_ratio(session, token.mint_address)
        avg_hold_days = await cls.calculate_avg_hold_days(session, token.mint_address)
        
        signals = {
            "is_long_potential": False,
            "reasons": []
        }
        
        # Skip if DEAD
        if token.category == TokenCategory.DEAD:
            return signals
        
        if hold_ratio > 70:
            signals["reasons"].append(f"70%+ buyers still holding ({hold_ratio:.0f}%)")
            signals["is_long_potential"] = True
        
        if avg_hold_days > 7:
            signals["reasons"].append(f"Avg hold time {avg_hold_days:.1f} days")
            signals["is_long_potential"] = True
        
        if age_days > 30 and token.buy_count > 10:
            signals["reasons"].append(f"Mature token ({age_days:.0f} days, {token.buy_count} buys)")
            signals["is_long_potential"] = True
        
        return signals
