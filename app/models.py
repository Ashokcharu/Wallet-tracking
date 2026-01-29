from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer, Boolean, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

# Token Categories
class TokenCategory:
    MEME_SHORT = "MEME_SHORT"      # <7 days, quick flip
    MEME_LONG = "MEME_LONG"        # 7-30 days, building momentum
    LONG_POTENTIAL = "LONG_POTENTIAL"  # 30+ days, wallets holding
    BLUE_CHIP = "BLUE_CHIP"        # Established (SOL, BNB, etc.)
    DEAD = "DEAD"                  # Liquidity dropped, no buys, exit signals

# Signal Levels
class SignalLevel:
    WEAK = "WEAK"           # 1-2 wallets
    MODERATE = "MODERATE"   # 3-4 wallets
    STRONG = "STRONG"       # 5+ high-score wallets

class WalletCluster(Base):
    """Groups related wallets (same person/bot using multiple wallets)"""
    __tablename__ = "wallet_clusters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)  # e.g., "Whale Alpha"
    similarity_score = Column(Float, default=0.0)  # 0-1, how confident we are they're related
    created_at = Column(DateTime, default=datetime.utcnow)
    
    wallets = relationship("Wallet", back_populates="cluster")

class Wallet(Base):
    __tablename__ = "wallets"
    
    address = Column(String, primary_key=True)
    label = Column(String, nullable=True)
    cluster_id = Column(Integer, ForeignKey("wallet_clusters.id"), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Scoring fields (0-100)
    score = Column(Float, default=0.0)
    early_buy_rate = Column(Float, default=0.0)    # % of buys that were early
    avg_profit_pct = Column(Float, default=0.0)    # average profit %
    consistency = Column(Float, default=0.0)       # trade consistency
    influence = Column(Float, default=0.0)         # how often others follow
    noise_penalty = Column(Float, default=0.0)     # random low-impact trades
    
    cluster = relationship("WalletCluster", back_populates="wallets")
    activities = relationship("Activity", back_populates="wallet")

class Token(Base):
    __tablename__ = "tokens"
    
    mint_address = Column(String, primary_key=True)
    symbol = Column(String, nullable=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    buy_count = Column(Integer, default=0)
    
    # Classification
    category = Column(String, default=TokenCategory.MEME_SHORT)
    liquidity_health = Column(Float, default=0.0)  # 0-100
    hold_ratio = Column(Float, default=0.0)        # % of buyers still holding
    avg_hold_days = Column(Float, default=0.0)     # average hold time in days
    
    activities = relationship("Activity", back_populates="token")

class Activity(Base):
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    wallet_address = Column(String, ForeignKey("wallets.address"))
    token_mint = Column(String, ForeignKey("tokens.mint_address"))
    tx_signature = Column(String, unique=True)
    activity_type = Column(String)  # BUY or SELL
    amount = Column(Float)
    price_sol = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Enhanced tracking
    profit_pct = Column(Float, nullable=True)       # calculated on sell
    is_early_buy = Column(Boolean, default=False)   # within first hour of token
    sold_at = Column(DateTime, nullable=True)       # when position was closed
    
    wallet = relationship("Wallet", back_populates="activities")
    token = relationship("Token", back_populates="activities")

class Signal(Base):
    """Tracks generated signals for tokens"""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    token_mint = Column(String, ForeignKey("tokens.mint_address"))
    signal_type = Column(String)  # BUY_SIGNAL, LONG_POTENTIAL, ACCUMULATION
    level = Column(String)        # WEAK, MODERATE, STRONG
    wallet_count = Column(Integer)
    avg_wallet_score = Column(Float)
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    notified = Column(Boolean, default=False)
