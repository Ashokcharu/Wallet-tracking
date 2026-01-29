# Design: walleTracker

## Architecture
The system consists of three main components:
1.  **Monitor**: A background worker that polls Solana RPCs for new transactions from tracked wallets.
2.  **Processor**: Logic to decode transaction data, identify token buys, and calculate PnL.
3.  **Notifier**: A Telegram bot interface for sending alerts and managing the wallet list.

## Data Model (SQLite)
- `wallets`: `address` (PK), `label`, `accuracy_score`, `created_at`.
- `tokens`: `mint_address` (PK), `symbol`, `first_seen_at`, `buy_count`.
- `activities`: `wallet_address`, `token_mint`, `tx_signature`, `type` (BUY/SELL), `amount`, `price`, `timestamp`.

## Transaction Detection Logic
Using `getSignaturesForAddress` and `getTransaction` (parsed):
- Filter for transactions involving Raydium (Liquidity Pool V4), Jupiter (Aggregator), or Pump.fun.
- Identify "Buy" by looking for SOL/USDC leaving the wallet and a non-standard token entering.
- Use `approximate` price calculation based on the change in SOL/USDC balance relative to the token balance change.

## Rate Limit Handling
- Round-robin through a list of public RPC endpoints (e.g., tethered to `solana-mainnet.rpcpool.com`, `api.mainnet-beta.solana.com`, etc.).
- Exponential backoff on 429 errors.
- Prioritize "active" wallets if rate limits are hit.
