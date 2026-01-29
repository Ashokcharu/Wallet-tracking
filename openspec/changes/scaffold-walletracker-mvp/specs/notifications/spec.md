# Capability: notifications

## ADDED Requirements

### Requirement: individual-alert
The system SHALL send a notification when a tracked wallet performs a meme token buy.
#### Scenario: Triggering individual alert
- **WHEN** a "BUY" event is detected for wallet `Whale 1` and token `$PEPE`
- **THEN** a Telegram message is sent: `🚨 Whale 1 bought $PEPE!`

### Requirement: aggregate-signal
The system SHALL send a high-priority notification when multiple tracked wallets buy the same token.
#### Scenario: Triggering group signal
- **WHEN** 5 different tracked wallets have bought token `$WIF` within the last hour
- **THEN** a Telegram message is sent: `🔥 MEME SIGNAL: $WIF bought by 5 tracked wallets!`
