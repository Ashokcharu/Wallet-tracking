import sys
import os
import asyncio
import logging
import threading
from datetime import datetime
from dotenv import load_dotenv

# Fix imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.rpc import SolanaRPCManager
from app.monitor import WalletMonitor
from app.parser import TransactionParser
from app.notifier import TelegramNotifier
from app.models import Base, Wallet, Token, Activity, TokenCategory
from app.scoring import ScoringEngine
from app.classifier import TokenClassifier
from app.signals import SignalEngine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, desc, func
from app.research_monitor import trend_monitor

load_dotenv()

# Logging Configuration
# Console: Only ERRORs
# File: INFO and above
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_formatter = logging.Formatter('%(levelname)s: %(message)s')

file_handler = logging.FileHandler('bot_output.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)
console_handler.setFormatter(console_formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger("walleTracker")

TOP_WALLETS_COUNT = 10

class App:
    def __init__(self):
        default_rpcs = [
            "https://api.mainnet-beta.solana.com",
            "https://solana-api.projectserum.com",
            "https://rpc.ankr.com/solana",
            "https://solana-mainnet.g.allnodes.com",
            "https://api.witness.co"
        ]
        user_rpcs = os.getenv("SOLANA_RPC_URLS")
        rpc_urls = user_rpcs.split(",") if user_rpcs else default_rpcs
        self.rpc_manager = SolanaRPCManager(rpc_urls)
        
        helius_url = os.getenv("HELIUS_RPC_URL")
        if helius_url:
            self.helius_manager = SolanaRPCManager([helius_url])
            logger.info("🚀 Helius RPC enabled for top wallets")
        else:
            self.helius_manager = None
            logger.warning("No HELIUS_RPC_URL - using public RPC only")
        
        self.db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./walletracker.db")
        self.monitor = WalletMonitor(self.rpc_manager, self.db_url)
        self.notifier = TelegramNotifier()
        self.engine = create_async_engine(self.db_url)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self.wallets_file = "wallets.txt"
        self.top_wallets = set()

    async def update_top_wallets(self):
        async with self.async_session() as session:
            result = await session.execute(
                select(Wallet.address).where(Wallet.active == True)
                .order_by(desc(Wallet.score))
                .limit(TOP_WALLETS_COUNT)
            )
            self.top_wallets = set(row[0] for row in result.all())
        logger.info(f"📊 Top {len(self.top_wallets)} wallets updated for Helius tracking")

    async def sync_wallets_from_file(self):
        if not os.path.exists(self.wallets_file):
            return
        with open(self.wallets_file, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith("#")]
        if not lines: return

        async with self.async_session() as session:
            added_count = 0
            for line in lines:
                parts = [p.strip() for p in line.split(",")]
                address = parts[0]
                label = parts[1] if len(parts) > 1 else None
                result = await session.execute(select(Wallet).where(Wallet.address == address))
                wallet = result.scalar_one_or_none()
                if not wallet:
                    wallet = Wallet(address=address, label=label, active=True)
                    session.add(wallet)
                    added_count += 1
                else:
                    wallet.active = True
                    if label: wallet.label = label
            await session.commit()
        with open(self.wallets_file, "w") as f:
            f.write("# Wallets synced to DB. Paste new wallets here.\n")
        logger.info(f"Synced {added_count} new wallets.")

    async def handle_buy(self, wallet, buy_info, signature):
        async with self.async_session() as session:
            token_mint = buy_info["mint"]
            token_result = await session.execute(select(Token).where(Token.mint_address == token_mint))
            token = token_result.scalar_one_or_none()
            is_early_buy = False
            if not token:
                token = Token(mint_address=token_mint, buy_count=1, first_seen_at=datetime.utcnow(), symbol=buy_info.get("symbol"))
                session.add(token)
                is_early_buy = True
            else:
                token.buy_count += 1
                if not token.symbol: token.symbol = buy_info.get("symbol")
                if token.first_seen_at:
                    hours_since_launch = (datetime.utcnow() - token.first_seen_at).total_seconds() / 3600
                    is_early_buy = hours_since_launch < 1
            
            activity = Activity(
                wallet_address=wallet.address,
                token_mint=token_mint,
                tx_signature=signature,
                activity_type="BUY",
                amount=buy_info["amount"],
                price_sol=buy_info.get("pay_amount", 0) / buy_info["amount"] if buy_info["amount"] > 0 else 0,
                is_early_buy=is_early_buy
            )
            session.add(activity)
            await ScoringEngine.update_wallet_score(session, wallet)
            await TokenClassifier.classify_token(session, token)
            await session.commit()
            
            await self.notifier.notify_buy(wallet.label or "Unknown", wallet.address, token.symbol or "UNKNOWN", token_mint, wallet.score or 0)
            
            buy_signal = await SignalEngine.check_buy_signal(session, token_mint)
            if buy_signal.get("signal"):
                await SignalEngine.save_signal(session, token_mint, buy_signal, "BUY_SIGNAL")
                await self.notifier.notify_signal(token.symbol or "UNKNOWN", token_mint, buy_signal)
            await session.commit()

    async def handle_sell(self, wallet, sell_info, signature):
        async with self.async_session() as session:
            token_mint = sell_info["mint"]
            activity = Activity(
                wallet_address=wallet.address,
                token_mint=token_mint,
                tx_signature=signature,
                activity_type="SELL",
                amount=sell_info["amount"],
                price_sol=sell_info.get("receive_amount", 0) / sell_info["amount"] if sell_info["amount"] > 0 else 0
            )
            session.add(activity)
            await ScoringEngine.update_wallet_score(session, wallet)
            await session.commit()

    async def run(self):
        await self.sync_wallets_from_file()
        await self.update_top_wallets()

        async def processor(wallet, signature_str):
            if wallet.address in self.top_wallets and self.helius_manager:
                rpc = self.helius_manager
            else:
                return  # Skip for non-top wallets to stay free
            
            from solders.signature import Signature
            sig = Signature.from_string(signature_str)
            tx_response = await rpc.call_with_retry("get_transaction", sig, max_supported_transaction_version=0)
            if tx_response and tx_response.value:
                buy_info = await TransactionParser.parse_buy(tx_response.value, wallet.address)
                if buy_info:
                    await self.handle_buy(wallet, buy_info, signature_str)
                else:
                    sell_info = await TransactionParser.parse_sell(tx_response.value, wallet.address)
                    if sell_info:
                        await self.handle_sell(wallet, sell_info, signature_str)

        self.monitor.process_transaction = processor
        async def refresh_loop():
            while True:
                await asyncio.sleep(300)
                await self.update_top_wallets()
        
        asyncio.create_task(refresh_loop())
        logger.info("🤖 Bot is active and monitoring...")
        await self.monitor.run(interval=120)

from app.api import app

# Create global bot instance
bot_instance = App()

@app.on_event("startup")
async def start_bot():
    """Start the bot and research monitor in the background when the API starts"""
    logger.info("🎬 Starting bot background task...")
    asyncio.create_task(bot_instance.run())
    
    logger.info("🧠 Starting Research Monitor background task...")
    asyncio.create_task(trend_monitor.start())

if __name__ == "__main__":
    import uvicorn
    # If run directly via python main.py, start uvicorn
    # The bot will be started by the @app.on_event("startup") handler
    uvicorn.run(app, host="0.0.0.0", port=8000)
