import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://roomly:roomly@localhost:5432/roomly",
)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_ADMIN_TOKEN = os.getenv("BOT_ADMIN_TOKEN", "")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "1440"))
APP_TZ = os.getenv("APP_TZ", "Asia/Almaty")
