# Capability: wallet-monitoring

## ADDED Requirements

### Requirement: wallet-track-list
The system SHALL maintain a manually-managed list of Solana wallet addresses to monitor.
#### Scenario: Adding a new wallet
- **WHEN** a user adds wallet address `5vV...` with label `Whale 1`
- **THEN** the wallet is saved to the database and included in the next scan cycle

### Requirement: rpc-polling
The system SHALL poll public Solana RPC endpoints to fetch new transaction signatures for all tracked wallets.
#### Scenario: Polling cycle
- **WHEN** the scheduler triggers a scan (every 60 seconds)
- **THEN** `getSignaturesForAddress` is called for each wallet, fetching signatures since the last seen transaction

### Requirement: transaction-fetching
The system SHALL fetch full transaction details for any new signatures found.
#### Scenario: Fetching transaction
- **WHEN** `getTransaction` is called with `maxSupportedTransactionVersion: 0`
- **THEN** the transaction metadata and message are retrieved for parsing
