# Tasks: Meme Research Platform

## UI Foundation [x]
- [x] Create `frontend/research.html` for deep-dive pages.
- [x] Implement card-based dark-mode grid in `index.html`.
- [x] Add copy icons with toast notifications ("Copied ✔️").
- [x] Add external links (pump.fun, DexScreener).

## Frontend Logic [x]
- [x] Implement pagination in `app.js`.
- [x] Implement sorting filters (Age, Volume).
- [x] Display token age relative to current time.

## News & Research [x]
- [x] Implement background Trend Scraper/Monitor (periodically fetch viral events).
- [x] Add `NewsArticle` model to `app/models.py`.
- [x] Create `/api/news` endpoint in `app/api.py`.
- [x] Create `/api/tokens/{mint}/research` endpoint.

## Verification [x]
- [x] Verify pagination with 50+ tokens.
- [x] Verify copy-to-clipboard functionality in browser.
- [x] Verify news linking logic.
