"""
Transaction Parser - Detects meme token buys/sells from Solana transactions

Works with solders transaction objects (not dicts)
"""
import logging

logger = logging.getLogger(__name__)

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

class TransactionParser:
    @staticmethod
    async def parse_buy(tx_data, wallet_address: str):
        """
        Parses a solders transaction to detect if it's a 'Buy' event.
        A 'Buy' is defined as SOL decreasing and another token increasing.
        """
        try:
            # tx_data is EncodedConfirmedTransactionWithStatusMeta
            if not tx_data:
                return None
            
            meta = tx_data.meta
            if not meta:
                return None
            
            # Get token balances
            pre_token_balances = meta.pre_token_balances or []
            post_token_balances = meta.post_token_balances or []
            
            # Find token that INCREASED for the wallet
            bought_token = None
            for post in post_token_balances:
                owner = str(post.owner) if post.owner else None
                if owner == wallet_address:
                    mint = str(post.mint)
                    if mint in [SOL_MINT, USDC_MINT]:
                        continue
                    
                    # Check if it increased
                    pre_amount = 0
                    for pre in pre_token_balances:
                        if str(pre.mint) == mint and str(pre.owner) == wallet_address:
                            pre_amount = int(pre.ui_token_amount.amount)
                            break
                    
                    post_amount = int(post.ui_token_amount.amount)
                    if post_amount > pre_amount:
                        decimals = post.ui_token_amount.decimals
                        bought_token = {
                            "mint": mint,
                            "amount": (post_amount - pre_amount) / (10 ** decimals),
                            "symbol": None
                        }
                        break

            if not bought_token:
                return None

            # Confirm SOL decreased (they paid for the token)
            pre_balances = meta.pre_balances or []
            post_balances = meta.post_balances or []
            
            if pre_balances and post_balances and len(pre_balances) > 0:
                sol_diff = post_balances[0] - pre_balances[0]  # First account is usually signer
                if sol_diff < 0:
                    bought_token["pay_amount"] = abs(sol_diff) / 1e9
                    bought_token["pay_mint"] = SOL_MINT
                    return bought_token
            
            return bought_token
            
        except Exception as e:
            logger.debug(f"Parse buy error: {e}")
            return None

    @staticmethod
    async def parse_sell(tx_data, wallet_address: str):
        """
        Parses a solders transaction to detect if it's a 'Sell' event.
        A 'Sell' is defined as a token decreasing and SOL/USDC increasing.
        """
        try:
            if not tx_data:
                return None
            
            meta = tx_data.meta
            if not meta:
                return None

            pre_token_balances = meta.pre_token_balances or []
            post_token_balances = meta.post_token_balances or []
            
            # Find token that DECREASED for the wallet
            sold_token = None
            for pre in pre_token_balances:
                owner = str(pre.owner) if pre.owner else None
                if owner == wallet_address:
                    mint = str(pre.mint)
                    if mint in [SOL_MINT, USDC_MINT]:
                        continue
                    
                    # Check if it decreased
                    post_amount = 0
                    for post in post_token_balances:
                        if str(post.mint) == mint and str(post.owner) == wallet_address:
                            post_amount = int(post.ui_token_amount.amount)
                            break
                    
                    pre_amount = int(pre.ui_token_amount.amount)
                    if pre_amount > post_amount:
                        decimals = pre.ui_token_amount.decimals
                        sold_token = {
                            "mint": mint,
                            "amount": (pre_amount - post_amount) / (10 ** decimals),
                            "symbol": None
                        }
                        break

            if not sold_token:
                return None

            # Confirm SOL increased (they received payment)
            pre_balances = meta.pre_balances or []
            post_balances = meta.post_balances or []
            
            if pre_balances and post_balances and len(pre_balances) > 0:
                sol_diff = post_balances[0] - pre_balances[0]
                if sol_diff > 0:
                    sold_token["receive_amount"] = sol_diff / 1e9
                    sold_token["receive_mint"] = SOL_MINT
                    return sold_token

            return sold_token
            
        except Exception as e:
            logger.debug(f"Parse sell error: {e}")
            return None
