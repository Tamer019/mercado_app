# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

**Everything at once (recommended for local dev):**
```bash
source venv/bin/activate
python start.py
# Backend: http://127.0.0.1:8000  Frontend: http://127.0.0.1:8001
```

**Manually:**
```bash
# Backend
uvicorn api.main:app --reload --port 8000

# Frontend (separate terminal)
python -m http.server 8001 --directory frontend
```

**Scraper (standalone):**
```bash
cd scraper && python main.py
```

**Smoke test:**
```bash
curl "http://127.0.0.1:8000/search?q=mango&plz=72555"
```

There is no test runner or linter configured. Ad-hoc scraper scripts (e.g. `scraper/test_originalpreise.py`) print to stdout and are run individually.

## Architecture

The app compares supermarket prices by merging two data sources:

1. **Live Marktguru API** — called at request time by the FastAPI backend (`api/main.py`) to get current deals (`ist_angebot: true`).
2. **PostgreSQL `originalpreise` table** — stores "normal" (non-sale) prices, populated either manually via admin endpoints or by the `/admin/sync-oldprices` endpoint which scrapes `oldPrice` from the Marktguru API.

The `/search` endpoint merges both: retailers with an active deal come from the API; retailers that appear only in `originalpreise` (no current deal) are appended with `ist_angebot: false`. Results are sorted by price.

The **frontend** (`frontend/script.js`) calls the live Render deployment (`https://mercado-app019.onrender.com`) — not localhost — and renders cards with deal/normal-price badges based on the `ist_angebot` flag.

The **scraper** (`scraper/`) is a separate, sync process using `psycopg2` that writes to an `angebote` table. The API uses `asyncpg` and reads from `originalpreise`. These are two separate tables with different schemas and different DB clients.

## Database

- **Local:** PostgreSQL on `localhost:5433`, database `mercadoDB`, user `tamer`, no password.
- **Production (Render):** set via `DATABASE_URL` env var — `api/db_connection.py` checks this first.
- The scraper's `db_connection.py` is sync (`psycopg2`) and has no `DATABASE_URL` fallback — it always hits localhost.
- On startup, `api/main.py` runs `init_db()` which creates the `originalpreise` table and **upserts hardcoded test data** (Bio Hafermilch, Vegane Butter, Walnusskerne). This runs on every deploy.

## Admin endpoints

Protected by HTTP Basic Auth (credentials hardcoded in `api/main.py`):
- `GET /admin/preise` — list all original prices
- `POST /admin/preise?produkt_name=...&haendler=...&plz=...&preis=...` — add/update a price
- `DELETE /admin/preise/{id}` — delete a price
- `POST /admin/sync-oldprices` — fetch `oldPrice` from Marktguru for a hardcoded product list and save to DB

## Known issues / things to be aware of

- API keys for Marktguru are hardcoded in `api/main.py` and `scraper/marktguru.py`. Recommended env var names: `MARKTGURU_X_CLIENTKEY`, `MARKTGURU_X_APIKEY`.
- Admin credentials (`admin` / `mercado19`) are hardcoded in `api/main.py`.
- `CORS allow_origins=["*"]` is set — intentional for now, be cautious in production.
- `sync-oldprices` opens and closes a new DB connection per offer in a loop.
- The `angebote` table (written by the scraper) is not currently read by the API — the API fetches live from Marktguru instead.
