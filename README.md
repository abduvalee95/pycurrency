# Simple Cashflow Backend (FastAPI + Telegram + AI)

This project now uses a simplified cashflow model:
- `amount`
- `currency_code` (`USD`, `RUB`, `UZS`)
- `flow_direction` (`INFLOW`, `OUTFLOW`)
- `client_name`
- `created_at`
- `note` (optional)

## Core Features
- Telegram bot for manual and AI-assisted entry creation
- Telegram Mini Web App (React-in-template) for entry input and reports
- AI parser that returns `amount/currency_code/flow_direction/client_name/note`
- Reports:
  - daily profit by currency
  - currency balances
  - client debts (`outflow - inflow`)
  - cash total (with explicit UZS total)
- Security:
  - allowed Telegram ID whitelist
  - API request auth via Telegram WebApp `X-Telegram-Init-Data`
  - `X-Telegram-Id` is accepted only in debug/dev mode
- Daily CSV backup:
  - writes CSV files to disk
  - sends CSV to first allowed Telegram ID

## Endpoints
- `POST /api/v1/entries`
- `GET /api/v1/entries`
- `POST /api/v1/ai/parse`
- `GET /api/v1/reports/daily-profit`
- `GET /api/v1/reports/currency-balances`
- `GET /api/v1/reports/client-debts`
- `GET /api/v1/reports/cash-total`
- `POST /api/v1/reports/export-daily-csv`

## Run
1. Install deps:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2. Configure env:
```bash
cp .env.example .env
```
3. Migrate DB:
```bash
alembic upgrade head
```
4. Run API:
```bash
uvicorn app.main:app --reload
```
5. Run bot:
```bash
python -m app.bot.app
```
`/export_today` command can trigger daily CSV export manually from Telegram.

6. Open Mini Web App:
```text
http://localhost:8000/
```

## Tests
```bash
pip install -r requirements-dev.txt
pytest
```
