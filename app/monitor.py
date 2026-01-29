import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models import Wallet, Activity
from app.rpc import SolanaRPCManager
from solders.pubkey import Pubkey
from solders.signature import Signature
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class WalletMonitor:
    def __init__(self, rpc_manager: SolanaRPCManager, db_url: str):
        self.rpc_manager = rpc_manager
        self.engine = create_async_engine(db_url)
        self.async_session = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        self.last_signatures = {}  # wallet_address -> last_signature
        self.poll_delay = 1.0  # seconds between wallet polls (Helius allows faster)
        self.batch_size = 10   # wallets per polling cycle (Helius allows more)
        self.batch_index = 0   # current batch position

    async def get_active_wallets(self):
        async with self.async_session() as session:
            result = await session.execute(select(Wallet).where(Wallet.active == True))
            return result.scalars().all()

    async def poll_wallets(self):
        wallets = await self.get_active_wallets()
        total = len(wallets)
        
        if total == 0:
            logger.info("No active wallets to poll.")
            return
        
        # Get batch of wallets for this cycle
        start = self.batch_index
        end = min(start + self.batch_size, total)
        batch = wallets[start:end]
        
        # Move to next batch for next cycle
        self.batch_index = end if end < total else 0
        
        logger.info(f"Polling batch {start+1}-{end} of {total} wallets...")
        
        for i, wallet in enumerate(batch):
            try:
                await self.poll_wallet(wallet)
            except Exception as e:
                logger.error(f"Error: {wallet.address[:8]}...: {e}")
            
            # Rate limit: wait between wallets
            if i < len(batch) - 1:
                await asyncio.sleep(self.poll_delay)

    async def poll_wallet(self, wallet: Wallet):
        pubkey = Pubkey.from_string(wallet.address)
        last_sig = self.last_signatures.get(wallet.address)
        
        kwargs = {"limit": 5}  # Reduced to avoid rate limits
        if last_sig:
            # Convert string back to Signature object
            kwargs["until"] = Signature.from_string(last_sig)

        response = await self.rpc_manager.call_with_retry("get_signatures_for_address", pubkey, **kwargs)
        
        if not response or not response.value:
            return

        signatures = response.value
        if not signatures:
            return

        logger.info(f"Detected {len(signatures)} new transactions for {wallet.address[:8]}...")

        # Reverse to process oldest first
        for sig_info in reversed(signatures):
            sig_str = str(sig_info.signature)
            # Emit to processor
            await self.process_transaction(wallet, sig_str)
            self.last_signatures[wallet.address] = sig_str
            
            # Delay between transaction fetches (free RPC friendly)
            await asyncio.sleep(1.0)

    async def process_transaction(self, wallet: Wallet, signature: str):
        # This will call the TransactionParser via the callback set in main.py
        logger.info(f"Processing tx: {signature[:16]}... for {wallet.address[:8]}...")

    async def run(self, interval: int = 60):
        while True:
            logger.info("Starting polling cycle...")
            await self.poll_wallets()
            logger.info(f"Polling complete. Waiting {interval}s...")
            await asyncio.sleep(interval)
