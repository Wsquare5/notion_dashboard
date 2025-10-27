# Binance USDT-M Perpetual -> Notion Sync

This small project fetches Binance USDT-M perpetual futures symbols and metrics,
enriches them with CoinGecko market data, and upserts records into a Notion
database.

Files added:

- `scripts/binance_to_notion.py` - main sync script (Python)
- `requirements.txt` - Python dependencies
- `.env.example` - example environment variables file
- `overrides.json` - manual mapping for tricky symbols -> CoinGecko IDs

Requirements

- Python 3.9+
- A Notion integration and a target Notion database (see steps below)

Setup

1. Create and activate a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in `NOTION_TOKEN` and `NOTION_DATABASE_ID`.

Creating a Notion integration and database

1. In Notion, go to Settings & Members → Integrations → Develop your own integrations → New integration.
2. Give it a name and copy the "Internal Integration Token" into `NOTION_TOKEN` in your `.env`.
3. Create a new database (Table) in Notion with these properties (case-sensitive):

   - `Name` (Title)
   - `Symbol` (Rich Text)
   - `Price (USD)` (Number)
   - `Market Cap (USD)` (Number)
   - `Open Interest` (Number)
   - `24h Volume (USD)` (Number)
   - `CoinGecko ID` (Rich Text)
   - `Website` (URL)

4. Share the database with your integration (top-right Share → Invite → select your integration).
5. Copy the database ID from the URL and paste into `NOTION_DATABASE_ID` in `.env`.

Quick run (smoke test, processes 20 symbols):

```bash
python scripts/binance_to_notion.py --limit 20
```

Next steps / Improvements

- Add robust mapping UI / CSV export for missing CoinGecko IDs.
- Add retries with backoff for Notion 429s and better logging.
- Add GitHub Actions workflow for scheduled runs.
