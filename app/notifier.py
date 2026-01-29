import os
from telegram import Bot
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not self.token or not self.chat_id:
            logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not found in environment.")
            self.bot = None
        else:
            self.bot = Bot(token=self.token)

    async def send_message(self, message: str):
        if not self.bot:
            logger.info(f"Notification (Dry run): {message}")
            return
        
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    async def notify_buy(self, wallet_label: str, wallet_address: str, token_symbol: str, token_mint: str, wallet_score: float = 0):
        score_emoji = "🔥" if wallet_score >= 70 else "📊"
        msg = (
            f"🚨 <b>Meme Buy Detected!</b>\n\n"
            f"👤 <b>Wallet:</b> {wallet_label} (<code>{wallet_address[:6]}...{wallet_address[-4:]}</code>)\n"
            f"{score_emoji} <b>Score:</b> {wallet_score:.0f}/100\n"
            f"🪙 <b>Token:</b> ${token_symbol}\n"
            f"📝 <b>Mint:</b> <code>{token_mint}</code>\n"
            f"🔗 <a href='https://solscan.io/token/{token_mint}'>Solscan</a> | <a href='https://dexscreener.com/solana/{token_mint}'>DexScreener</a>"
        )
        await self.send_message(msg)

    async def notify_signal(self, token_symbol: str, token_mint: str, signal_data: dict):
        """Send tiered signal notification with confidence score"""
        level = signal_data.get("signal", "WEAK")
        confidence = signal_data.get("confidence", 0)
        emoji_map = {"WEAK": "📢", "MODERATE": "📣", "STRONG": "🔥🔥🔥"}
        emoji = emoji_map.get(level, "📢")
        
        msg = (
            f"{emoji} <b>TOKEN SIGNAL: ${token_symbol}</b>\n\n"
            f"📊 <b>Level:</b> {level} (Confidence: {confidence}/100)\n"
            f"👥 <b>Wallets:</b> {signal_data.get('wallet_count', 0)} (avg score {signal_data.get('avg_score', 0)})\n"
            f"🔗 <b>Clusters:</b> {signal_data.get('cluster_count', 'N/A')}\n"
            f"💡 <b>Reason:</b> {signal_data.get('reason', 'N/A')}\n"
            f"📝 <b>Mint:</b> <code>{token_mint}</code>\n"
            f"🔗 <a href='https://solscan.io/token/{token_mint}'>Solscan</a> | <a href='https://dexscreener.com/solana/{token_mint}'>DexScreener</a>"
        )
        await self.send_message(msg)

    async def notify_long_term(self, token_symbol: str, token_mint: str, signal_data: dict):
        """Send long-term potential alert"""
        reasons = signal_data.get("reasons", [])
        reasons_text = "\n".join([f"  • {r}" for r in reasons]) if reasons else "Multiple holding signals"
        
        msg = (
            f"💎 <b>LONG-TERM POTENTIAL: ${token_symbol}</b>\n\n"
            f"👥 <b>Held by:</b> {signal_data.get('holder_count', 0)} tracked wallets (avg score {signal_data.get('avg_score', 0)})\n"
            f"⏱ <b>Avg hold time:</b> {signal_data.get('avg_hold_days', 0):.1f} days\n"
            f"📈 <b>Signals:</b>\n{reasons_text}\n\n"
            f"📝 <b>Mint:</b> <code>{token_mint}</code>\n"
            f"🔗 <a href='https://solscan.io/token/{token_mint}'>Solscan</a> | <a href='https://dexscreener.com/solana/{token_mint}'>DexScreener</a>"
        )
        await self.send_message(msg)

    async def notify_accumulation(self, token_symbol: str, token_mint: str, signal_data: dict):
        """Send accumulation alert when wallets buy multiple times"""
        msg = (
            f"📈 <b>ACCUMULATION DETECTED: ${token_symbol}</b>\n\n"
            f"👥 <b>Accumulators:</b> {signal_data.get('accumulator_count', 0)} high-score wallets\n"
            f"🔄 <b>Repeat buys:</b> {signal_data.get('total_repeat_buys', 0)} total\n"
            f"💡 <b>Reason:</b> {signal_data.get('reason', 'Wallets buying multiple times')}\n\n"
            f"📝 <b>Mint:</b> <code>{token_mint}</code>\n"
            f"🔗 <a href='https://solscan.io/token/{token_mint}'>Solscan</a> | <a href='https://dexscreener.com/solana/{token_mint}'>DexScreener</a>"
        )
        await self.send_message(msg)

    async def notify_aggregate(self, token_symbol: str, token_mint: str, count: int):
        """Legacy aggregate notification"""
        msg = (
            f"🔥 <b>MEME SIGNAL!</b>\n\n"
            f"The token <b>${token_symbol}</b> was just bought by <b>{count}</b> tracked wallets!\n"
            f"📝 <b>Mint:</b> <code>{token_mint}</code>\n"
            f"🔗 <a href='https://solscan.io/token/{token_mint}'>Solscan</a> | <a href='https://dexscreener.com/solana/{token_mint}'>DexScreener</a>"
        )
        await self.send_message(msg)
