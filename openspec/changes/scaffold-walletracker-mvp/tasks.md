# Tasks: walleTracker MVP

## Phase 1: Foundation
- [x] Initialize project structure and database schema [id: foundation-1]
- [x] Implement basic Solana RPC client with rate limiting [id: foundation-2]
- [x] Set up Telegram Bot skeleton for notifications/commands [id: foundation-3]

## Phase 2: Monitoring & Detection
- [x] Implement `Monitor` to poll transaction signatures for tracked wallets [id: monitor-1]
- [x] Implement `TransactionParser` to detect Raydium/Jupiter/Pump.fun buys [id: monitor-2]
- [/] Implement logic to store buy events and update token buy counts [id: monitor-3]

## Phase 3: Notifications & Scoring
- [x] Trigger Telegram alerts for individual buys [id: alert-1]
- [x] Trigger aggregate alerts when >5 wallets buy the same token [id: alert-2]
- [x] Implement background task to check token price/liquidity for PnL calculation [id: scoring-1]
- [x] Calculate and display wallet accuracy scores [id: scoring-2]

## Phase 4: Validation
- [x] Unit tests for transaction parsing [id: valid-1]
- [x] Integration test with live public RPC (mocked if needed) [id: valid-2]
- [x] End-to-end flow validation [id: valid-3]
