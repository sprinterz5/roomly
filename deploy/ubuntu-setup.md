# Roomly Ubuntu Setup (manual)

These steps assume:
- code lives in `/opt/roomly`
- you use a single `.env` at `/opt/roomly/.env`
- backend runs on `127.0.0.1:8000` behind Nginx

## 1) System packages
```bash
apt update
apt install -y python3 python3-venv python3-pip nginx
```

## 2) App files
```bash
mkdir -p /opt/roomly
# upload project to /opt/roomly (scp/rsync/git)
```

## 3) Python venv + deps
```bash
cd /opt/roomly/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install -r bot/requirements.txt
```

## 4) Environment file
Create `/opt/roomly/.env`:
```
DATABASE_URL=postgresql+psycopg://roomly:roomly@localhost:5432/roomly
JWT_SECRET=change_me
APP_TZ=Asia/Almaty

TELEGRAM_BOT_TOKEN=...
BOT_ADMIN_TOKEN=...
BOT_ADMIN_IDS=123456789
API_BASE_URL=https://roomly.example.com
API_VERIFY_SSL=true
```

## 5) DB tables
```bash
cd /opt/roomly/backend
. .venv/bin/activate
python -m app.init_db
```

## 6) Systemd services
```bash
cp /opt/roomly/deploy/roomly-backend.service /etc/systemd/system/roomly-backend.service
cp /opt/roomly/deploy/roomly-bot.service /etc/systemd/system/roomly-bot.service
systemctl daemon-reload
systemctl enable --now roomly-backend roomly-bot
```

## 7) Nginx (HTTP)
```bash
cp /opt/roomly/deploy/nginx-roomly.conf /etc/nginx/sites-available/roomly.conf
ln -s /etc/nginx/sites-available/roomly.conf /etc/nginx/sites-enabled/roomly.conf
nginx -t && systemctl reload nginx
```

## 8) HTTPS
Telegram requires a valid HTTPS cert (not self-signed). Use a real domain +
Let's Encrypt or a tunnel (e.g., Cloudflare or ngrok).
