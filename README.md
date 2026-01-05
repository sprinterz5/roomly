# Roomly

Roomly is a university room reservation system with role-based portals, a calendar, rooms, clubs, and a Telegram bot for onboarding and role assignment. The web UI is served by the FastAPI backend.

## Features
- Role-based portals: Student, Club Leader, Administration.
- Calendar with recurring events (RRULE) and approval workflow.
- Rooms managed by room code (example: A101).
- Clubs with leaders and members assigned by email.
- Student can leave clubs (leader cannot leave own club).
- Telegram WebApp auth (initData) with JWT.
- Telegram bot onboarding and admin commands.
- Admin Data tab to list and delete records across tables.

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

## Roles and Permissions
- `student`:
  - View own events
  - View available rooms
  - See club memberships
  - Leave clubs (if role is member)
- `club_leader`:
  - Create club events (pending approval)
  - Add members by email to own clubs
  - View and manage own clubs
- `admin`:
  - Full access to all data
  - Approve/reject events
  - Manage roles, clubs, rooms
  - Delete records from all tables via Admin Data tab

## Core Flows
### WebApp auth
1. Telegram WebApp sends `initData` to `POST /api/auth/telegram`.
2. Backend verifies signature and returns JWT.
3. UI stores JWT and uses `Authorization: Bearer <token>` for API calls.
4. Email is required to access the WebApp (users must link email in bot).

### Events
- Club events are created as `pending` and require admin approval.
- Admin events/lessons are created as `approved`.
- Recurring events use RRULE + duration.
- Event creation uses `room_code` (not room id).

### Clubs
- Club leaders can add members by email to their clubs.
- Students can leave clubs (except leaders).
- Students see their club memberships list.

### Rooms
- Rooms are stored in DB and managed in the Admin panel.
- Student/Club portals show available rooms from DB.

## API Routes (Summary)
### Auth
- `POST /api/auth/telegram`

### Calendar
- `GET /api/calendar/events`
- `POST /api/calendar/events`
- `PATCH /api/calendar/events/{event_id}/cancel`

### Clubs
- `GET /api/clubs/my` (club leaders/admins)
- `GET /api/clubs/memberships` (user memberships)
- `POST /api/clubs/members` (add member by email)
- `GET /api/clubs/members?club_name=...` (list members for a club)
- `DELETE /api/clubs/members?club_name=...` (leave club)

### Rooms
- `GET /api/rooms/available`

### Admin
- `POST /api/admin/users/role` (assign role by email)
- `POST /api/admin/clubs` (create club)
- `POST /api/admin/clubs/leader` (assign leader by name+email)
- `GET /api/admin/rooms` / `POST /api/admin/rooms` / `PATCH /api/admin/rooms/{room_code}` / `DELETE /api/admin/rooms/{room_code}`
- `GET /api/admin/users` / `DELETE /api/admin/users/{user_id}`
- `GET /api/admin/clubs` / `DELETE /api/admin/clubs/{club_id}`
- `GET /api/admin/club-members` / `DELETE /api/admin/club-members?club_id=...&user_id=...`
- `GET /api/admin/events` / `DELETE /api/admin/events/{event_id}`
- `GET /api/admin/event-participants` / `DELETE /api/admin/event-participants?event_id=...&user_id=...`
- `POST /api/admin/events/{event_id}/approve`
- `POST /api/admin/events/{event_id}/reject`

## Telegram Bot
### Commands
- `/start` (admins see commands; new users get email prompt)
- `/help` (admins only)
- `/email <email>`
- `/setemail <tg_id> <email>` (admin only)
- `/setrole <email> <role>` (admin only)
- `/setroletg <tg_id> <role>` (admin only)
- `/setleader <club name> | <email>` (admin only)
- `/setleadertg <club name> | <tg_id>` (admin only)
- `/createclub <club name>` (admin only)

Roles: `student`, `club_leader`, `admin`.

## Local Setup
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

### Run bot
```bash
cd backend
python -m bot.bot
```

Frontend is served from:
- `/` (index)
- `/style.css`
- `/script.js`
- `/assets/*`

## Deployment (Ubuntu)
See `deploy/ubuntu-setup.md` for full steps and systemd templates.

### HTTPS requirement
Telegram WebApp requires a valid HTTPS URL (no self-signed cert).
- Production: real domain + Lets Encrypt
- Quick dev: Cloudflare Tunnel or ngrok
