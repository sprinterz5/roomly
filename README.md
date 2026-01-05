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

# Roomly Role Bot

## Requirements
- Python 3.11+

## Setup
```
cd backend/bot
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

## Environment
Set these before running (or place them in `.env` at the repo root):
- `TELEGRAM_BOT_TOKEN` (token from BotFather)
- `BOT_ADMIN_TOKEN` (shared secret with backend)
- `BOT_ADMIN_IDS` (comma-separated Telegram user IDs allowed to run commands)
- `API_BASE_URL` (default `http://127.0.0.1:8000`)
- `API_VERIFY_SSL` (default `true`; set `false` for self-signed dev HTTPS)

## Run
```
python bot.py
```

## Commands
- `/setrole <user_id|email> <role>`
- `/setroletg <tg_id> <role>`
- `/setleader <club_id> <user_id|email>`
- `/setleadertg <club_id> <tg_id>`
- `/createclub <club name>`
- `/setemail <user_id|tg_id> <email>`
- `/email <email>`

Roles: `student`, `club_leader`, `admin`.

Non-admin flow: `/start` → `/email you@domain.com` → open the web app.
