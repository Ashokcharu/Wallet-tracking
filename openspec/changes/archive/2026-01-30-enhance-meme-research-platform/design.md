# Design: Meme Research Platform

## 1. Data Models

### NewsArticle
- `id`: UUID
- `title`: String
- `summary`: Text
- `trend_keyword`: String (e.g., "Penguin")
- `created_at`: DateTime
- `tokens`: Relationship (M:M with Token)

### TokenMetadata (Extended)
- `origin_story`: Text
- `twitter_url`: String
- `website_url`: String
- `narrative_status`: Enum (NEW, RISING, VETERAN)
- `last_updated_at`: DateTime (For dynamic tracking)

## 2. Dynamic Update Mechanism
- **Trend Scraper/Monitor**: A background task SHALL periodically (every 1 hour) check social aggregates or news APIs for viral meme keywords.
- **Auto-Update**: The `TokenMetadata` and `NewsArticle` associations SHALL be updated dynamically as new trends emerge, ensuring the data doesn't go stale.

## 2. UI Components

### Dashboard Grid
- 3-column layout on desktop.
- Responsive pagination with "Load More" or page numbers.
- Filter Bar: [Newest | Trending | Volume | Age].

### Research Page (New Tab)
- Separate React/HTML entry point or dynamic route.
- Sections: Overview, Narrative, News Timeline, Security/Risk Metrics.

## 3. Tech Stack Impacts
- **Frontend**: Expansion of `styles.css` and `app.js` to support routing and more complex state.
- **Backend**: API endpoints for news and paginated tokens.
