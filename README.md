# Roomly

Roomly is a university room reservation system with role-based portals, a calendar, and a Telegram bot for onboarding and role assignment. The web UI is served by the FastAPI backend and is designed for students, club leaders, and admins.

## Features
- Role-based portals: Student, Club Leader, Administration.
- Calendar with recurring events (RRULE) and approval workflow.
- Room management by room code (e.g., A101).
- Club management with leader and member assignment by email.
- Telegram WebApp auth (initData) with JWT.
- Telegram bot for onboarding, email linking, and admin actions.
- Admin Data panel to review and delete records across tables.

## Tech Stack
- Backend: FastAPI, SQLAlchemy, Postgres
- Frontend: HTML/CSS/JS, FullCalendar
- Bot: python-telegram-bot

## Project Structure
- `index.html`, `style.css`, `script.js` - frontend UI
- `assets/` - static images
- `backend/app` - FastAPI app and routers
- `backend/bot` - Telegram bot
- `deploy/` - systemd and Nginx templates

## Local Setup (Backend + Bot)
### Requirements
- Python 3.11+
- Postgres 14+

### Install
```bash
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r backend/requirements.txt
pip install -r backend/bot/requirements.txt
```

### Environment
Create `.env` at repo root:
```
DATABASE_URL=postgresql+psycopg://roomly:roomly@localhost:5432/roomly
JWT_SECRET=change_me
APP_TZ=Asia/Almaty

TELEGRAM_BOT_TOKEN=...
BOT_ADMIN_TOKEN=...
BOT_ADMIN_IDS=123456789
API_BASE_URL=http://127.0.0.1:8000
API_VERIFY_SSL=false
```

### Create tables
```bash
cd backend
python -m app.init_db
```

### Run backend
```bash
cd backend
uvicorn app.main:app --reload
```

The frontend is served from:
- `/` (index)
- `/style.css`
- `/script.js`
- `/assets/*`

### Run bot
```bash
cd backend
python -m bot.bot
```

## Telegram Bot Commands
- `/start` - admins see commands; new users get email prompt
- `/help` - admins only
- `/email <email>` - link your email
- `/setemail <tg_id> <email>` - admin only
- `/setrole <email> <role>` - admin only
- `/setroletg <tg_id> <role>` - admin only
- `/setleader <club name> | <email>` - admin only
- `/setleadertg <club name> | <tg_id>` - admin only
- `/createclub <club name>` - admin only

Roles: `student`, `club_leader`, `admin`.

## Roles and Access Rules
- New users default to `student`.
- Club leaders can create club events and add members by email.
- Admins can approve/reject events and manage all data.
- Students can leave clubs they belong to (except leader role).

## Calendar and Events
- Events support recurring rules (RRULE).
- Club events are created as `pending` and require admin approval.
- Event creation accepts room code (e.g., `A101`).

## Rooms
- Rooms are stored in DB and managed in Admin panel.
- Club and Student portals show available rooms from DB.

## Admin Panel
- Manage roles, clubs, and rooms.
- Data tab lists and allows deletion of:
  - users
  - clubs
  - club members
  - events
  - event participants

## Telegram WebApp Auth
1. WebApp sends `initData` to `POST /api/auth/telegram`.
2. Backend verifies signature and returns JWT.
3. API calls use `Authorization: Bearer <token>`.

Email is required to access the WebApp. Users must link email via bot first.

## Deployment (Ubuntu)
See `deploy/ubuntu-setup.md` for a full step-by-step guide and systemd templates.

### HTTPS requirement
Telegram WebApp requires a valid HTTPS URL. For production, use a real domain + Lets Encrypt.
For quick testing without a domain, use Cloudflare Tunnel or ngrok.
