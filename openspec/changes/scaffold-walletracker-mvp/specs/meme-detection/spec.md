# Capability: meme-detection

## ADDED Requirements

### Requirement: dex-filter
The system SHALL identify transactions interacting with Raydium, Jupiter, or Pump.fun programs.
#### Scenario: Identifying a Raydium swap
- **WHEN** a transaction involves the Raydium Liquidity Pool V4 program ID (`675k1q2...`)
- **THEN** it is flagged as a potential swap activity

### Requirement: buy-detection
The system MUST distinguish between "Buy" and "Sell" events based on balance changes.
#### Scenario: Detecting a buy
- **WHEN** the wallet's SOL/USDC balance decreases
- **AND** a new token (not SOL/USDC/WSOL) balance increases
- **THEN** it is recorded as a "BUY" event for that token

### Requirement: token-metadata-extraction
The system SHALL attempt to extract the token mint address and symbol for detected buys.
#### Scenario: Extracting mint
- **WHEN** a "BUY" event is detected
- **THEN** the token mint address is identified and stored
