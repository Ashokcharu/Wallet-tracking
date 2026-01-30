# token-data-v2 Specification

## Purpose
TBD - created by archiving change enhance-meme-research-platform. Update Purpose after archive.
## Requirements
### Requirement: Token Age Tracking
The system SHALL calculate and display the relative age of tokens since they were first detected.
#### Scenario: Assessing token risk
- **Given** a token was launched X time ago
- **When** displayed on the dashboard
- **Then** it shows the relative age (e.g., "Age: 6 hours").
- **And** if the age is < 24h, a "🔥 New" badge is displayed.

### Requirement: Sorting and Filters
The system SHALL allow users to sort tokens by Age, Newest, Trending, and Volume.
#### Scenario: Finding newest tokens
- **Given** the user wants to see the latest launches
- **When** they select "Newest" from the filter bar
- **Then** the token list re-ranks based on `first_seen_at` descending.

### Requirement: Pagination
The system SHALL support paginated loading of tokens and wallets to maintain dashboard performance.
#### Scenario: Loading more data
- **Given** there are more than 50 tokens or wallets
- **When** the user reaches the end of the current page
- **Then** a pagination control (Page 1, 2, 3...) or "Load More" button allows them to fetch the next batch.

