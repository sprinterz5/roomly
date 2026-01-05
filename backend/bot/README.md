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
- `BOT_ADMIN_IDS` (comma-separated Telegram user IDs allowed to run admin commands)
- `API_BASE_URL` (default `http://127.0.0.1:8000`)
- `API_VERIFY_SSL` (default `true`; set `false` for self-signed dev HTTPS)

## Run
```
python bot.py
```

## Commands
- `/start` (admins see commands; new users get email prompt)
- `/help` (admins only)
- `/email <email>` (link your email)
- `/setemail <tg_id> <email>` (admin only)
- `/setrole <email> <role>` (admin only)
- `/setroletg <tg_id> <role>` (admin only)
- `/setleader <club name> | <email>` (admin only)
- `/setleadertg <club name> | <tg_id>` (admin only)
- `/createclub <club name>` (admin only)

Roles: `student`, `club_leader`, `admin`.

Non-admin flow: `/start` -> `/email you@domain.com` -> open the web app.
