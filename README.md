# WalletTracker - Solana Wallet Monitoring System

## Overview

A free, on-chain Solana wallet tracking system that monitors wallet activity, detects meme token signals, scores wallets, and sends Telegram alerts.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    WALLETS (1000+)                              │
├─────────────────────────────────────────────────────────────────┤
│  📡 PUBLIC RPC (Unlimited, Free)                                │
│  └─ getSignaturesForAddress → Detect new transactions           │
└────────────────────┬────────────────────────────────────────────┘
                     │
         ┌───────────▼───────────┐
         │   TOP 10 WALLETS?     │ (by score)
         └───────────┬───────────┘
              YES    │    NO
              ▼      │    ▼
    ┌─────────────────────────────────────────────────────────────┐
    │ ⚡ HELIUS RPC (100k free/mo)  │  📝 Log Only (0 credits)    │
    │ └─ getTransaction              │  └─ Save for later scoring  │
    │ └─ Parse buy/sell              │                             │
    │ └─ Send Telegram alerts        │                             │
    └─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Multi-Factor Wallet Scoring
```
score = 0.25 × early_buy_rate 
      + 0.30 × avg_profit 
      + 0.20 × consistency 
      + 0.15 × influence 
      - 0.10 × noise
```

### 2. Token Classification
| Category | Criteria |
|----------|----------|
| MEME_SHORT | < 7 days old |
| MEME_LONG | 7-30 days, >50% holders |
| LONG_POTENTIAL | 30+ days, >70% holders, >7d avg hold |
| BLUE_CHIP | Established tokens |

### 3. Signal Tiers
| Level | Trigger |
|-------|---------|
| WEAK | 1-2 wallets buy |
| MODERATE | 3-4 wallets buy |
| STRONG | 5+ high-score (≥70) wallets buy within 10 min |

### 4. Hybrid RPC Strategy
- **Scales to 1000+ wallets** on free tier
- Only top 10 scored wallets use Helius
- All others use free public RPC

## File Structure

```
walleTracker/
├── main.py                 # Entry point, hybrid RPC logic
├── wallets.txt             # Add wallets here (auto-synced)
├── .env                    # API keys
├── walletracker.db         # SQLite database
└── app/
    ├── models.py           # DB schema (Wallet, Token, Activity, Signal)
    ├── monitor.py          # Batch polling logic
    ├── parser.py           # Transaction parsing (buy/sell detection)
    ├── scoring.py          # Multi-factor wallet scoring
    ├── classifier.py       # Token categorization
    ├── signals.py          # Signal tier engine
    ├── notifier.py         # Telegram alerts
    └── rpc.py              # RPC manager with rotation
```

## Database Schema

```python
class Wallet:
    address: str (PK)
    label: str
    score: float (0-100)
    early_buy_rate, avg_profit_pct, consistency, influence, noise_penalty: float
    cluster_id: FK -> WalletCluster

class Token:
    mint_address: str (PK)
    category: str (MEME_SHORT, MEME_LONG, LONG_POTENTIAL, BLUE_CHIP)
    hold_ratio, avg_hold_days, liquidity_health: float

class Activity:
    wallet_address, token_mint: FK
    activity_type: BUY | SELL
    amount, price_sol, profit_pct: float
    is_early_buy: bool

class Signal:
    token_mint: FK
    signal_type: BUY_SIGNAL | LONG_POTENTIAL | ACCUMULATION
    level: WEAK | MODERATE | STRONG
```

## Configuration

```env
# .env
HELIUS_RPC_URL=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY
SOLANA_RPC_URLS=https://api.mainnet-beta.solana.com
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DATABASE_URL=sqlite+aiosqlite:///./walletracker.db
```

## Usage

```bash
# Add wallets
echo "WalletAddress, Label" >> wallets.txt

# Run
python3.11 main.py
```

## Telegram Alerts

### Buy Detection
```
🚨 Meme Buy Detected!
👤 Wallet: WhaleAlpha (9ZPs...)
🔥 Score: 78/100
🪙 Token: $XYZ
📝 Mint: ABC123...
```

### Signal Tiers
```
🔥🔥🔥 TOKEN SIGNAL: $XYZ
📊 Level: STRONG
👥 Wallets: 5 (avg score 78)
💡 Reason: 5 high-score wallets bought within 10min
```

### Long-Term Potential
```
💎 LONG-TERM POTENTIAL: $XYZ
👥 Held by: 4 wallets (avg score 75)
⏱ Avg hold time: 12 days (no sells)
```

## Scaling

| Wallets | Public RPC Calls | Helius Calls | Monthly Helius |
|---------|------------------|--------------|----------------|
| 38 | ~40/cycle | ~50/cycle | ~72k |
| 100 | ~100/cycle | ~50/cycle | ~72k |
| 1000 | ~1000/cycle | ~50/cycle | ~72k |

**Helius usage stays constant** because only top 10 wallets use it.

## Future Improvements

1. **Helius Webhooks** - Instant alerts for top wallets (no polling)
2. **Auto Wallet Clustering** - Group related wallets via transfer patterns
3. **Sentiment Integration** - Twitter/social signals

## API Credits Estimation

With 1-minute polling intervals:
- 60 cycles/hour × 50 Helius calls = 3,000/hour
- 72,000/day × 30 = ~2.1M/month

Helius free tier: 100k credits/month
→ **Use 2-minute intervals** for safe margin: ~1M/month

## Tech Stack

- Python 3.11+
- SQLAlchemy (async)
- solana-py, solders
- python-telegram-bot
- httpx
