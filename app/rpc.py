"""
Solana RPC Manager with round-robin endpoint rotation and rate limit handling
"""
import asyncio
import httpx
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Finalized
from solana.rpc.core import RPCException
from solders.pubkey import Pubkey
from solders.signature import Signature
import logging

logger = logging.getLogger(__name__)

class SolanaRPCManager:
    def __init__(self, rpc_urls: list[str]):
        self.rpc_urls = [url.strip() for url in rpc_urls if url.strip()]
        self.current_index = 0
        self.clients = [AsyncClient(url, commitment=Finalized) for url in self.rpc_urls]
        self.base_backoff = 2.0  # initial backoff seconds
        self.max_backoff = 30.0  # max backoff seconds
        self.current_backoff = self.base_backoff
        self.min_request_interval = 0.5  # minimum seconds between requests
        self.last_request_time = 0

    async def get_client(self):
        return self.clients[self.current_index]

    async def rotate_client(self):
        """Switch to next RPC endpoint"""
        old_url = self.rpc_urls[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.clients)
        new_url = self.rpc_urls[self.current_index]
        if old_url != new_url:
            logger.info(f"🔄 RPC: {old_url[:25]}... → {new_url[:25]}...")

    async def _throttle(self):
        """Ensure minimum interval between requests"""
        import time
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    async def call_with_retry(self, method_name: str, *args, **kwargs):
        max_retries = len(self.clients) * 3
        last_error = None
        
        for attempt in range(max_retries):
            await self._throttle()
            client = await self.get_client()
            try:
                method = getattr(client, method_name)
                response = await method(*args, **kwargs)
                # Success - reset backoff
                self.current_backoff = self.base_backoff
                return response
                
            except RPCException as e:
                error_msg = str(e)
                if "429" in error_msg or "Too Many Requests" in error_msg or "rate" in error_msg.lower():
                    logger.warning(f"⏳ Rate limited, backing off {self.current_backoff:.1f}s...")
                    await asyncio.sleep(self.current_backoff)
                    self.current_backoff = min(self.current_backoff * 1.5, self.max_backoff)
                    await self.rotate_client()
                else:
                    last_error = e
                    await self.rotate_client()
                    
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                status = getattr(getattr(e, 'response', None), 'status_code', 0)
                if status == 429:
                    logger.warning(f"⏳ HTTP 429, backing off {self.current_backoff:.1f}s...")
                    await asyncio.sleep(self.current_backoff)
                    self.current_backoff = min(self.current_backoff * 1.5, self.max_backoff)
                    await self.rotate_client()
                else:
                    last_error = e
                    await self.rotate_client()
                    await asyncio.sleep(1)
                    
            except Exception as e:
                last_error = e
                await self.rotate_client()
                await asyncio.sleep(1)
        
        logger.error(f"All RPC retries failed: {last_error}")
        return None

    async def close(self):
        for client in self.clients:
            await client.close()
