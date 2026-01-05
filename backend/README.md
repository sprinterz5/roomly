# Roomly Backend

## Requirements
- Python 3.11+
- Postgres 14+

## Setup
```
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

## Environment
Set these before running (or place them in `.env` at the repo root):
- `DATABASE_URL` (example: `postgresql+psycopg://roomly:roomly@localhost:5432/roomly`)
- `BOT_TOKEN` (Telegram bot token)
- `BOT_ADMIN_TOKEN` (shared secret for the role bot)
- `JWT_SECRET` (random secret)
- `APP_TZ` (default `Asia/Almaty`)

## Run
```
uvicorn app.main:app --reload
```

Front-end is served from `/` along with `/style.css`, `/script.js`, and `/assets`.

Role assignment bot lives in `backend/bot/README.md`.

## Create tables (dev)
```
python -m app.init_db
```

## Auth flow
1. WebApp sends `initData` to `POST /api/auth/telegram`.
2. Backend verifies signature and returns JWT.
3. Use `Authorization: Bearer <token>` for API calls.

## Roles
- New users default to `student`.
- Only admins can assign roles and club leaders.
- Club events are created as `pending` and require admin approval.
