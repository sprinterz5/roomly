import os
from pathlib import Path
from typing import List

import requests
from dotenv import load_dotenv
import urllib3

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
BOT_ADMIN_TOKEN = os.getenv("BOT_ADMIN_TOKEN", "")
API_VERIFY_SSL = os.getenv("API_VERIFY_SSL", "true").lower() not in {"0", "false", "no"}

if not API_VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ADMIN_IDS: List[int] = []
_admin_raw = os.getenv("BOT_ADMIN_IDS", "")
if _admin_raw:
    ADMIN_IDS = [int(x.strip()) for x in _admin_raw.split(",") if x.strip().isdigit()]


def is_admin(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id in ADMIN_IDS)


def api_post(path: str, payload: dict):
    url = f"{API_BASE_URL}{path}"
    headers = {"X-Admin-Token": BOT_ADMIN_TOKEN}
    return requests.post(url, json=payload, headers=headers, timeout=10, verify=API_VERIFY_SSL)


def extract_email(value: str) -> str | None:
    if not value:
        return None
    if "@" in value and "." in value:
        return value.lower()
    return None


def parse_pipe_args(update: Update) -> tuple[str, str] | None:
    message = update.message.text if update.message else ""
    if not message:
        return None
    parts = message.split(None, 1)
    if len(parts) < 2:
        return None
    rest = parts[1]
    if "|" not in rest:
        return None
    left, right = rest.split("|", 1)
    left = left.strip()
    right = right.strip()
    if not left or not right:
        return None
    return left, right


def ensure_user(update: Update, mark_intro: bool | None = None) -> dict | None:
    user = update.effective_user
    if not user:
        return None
    full_name = " ".join(filter(None, [user.first_name, user.last_name])) or None
    payload = {
        "tg_id": str(user.id),
        "username": user.username,
        "full_name": full_name,
    }
    if mark_intro is not None:
        payload["mark_intro"] = mark_intro
    try:
        res = api_post("/api/bot/upsert-user", payload)
        if res.ok:
            return res.json()
    except requests.RequestException:
        return None
    return None


def format_api_response(res: requests.Response, success_message=None) -> str:
    try:
        data = res.json()
    except ValueError:
        return res.text

    if res.ok:
        if success_message:
            if callable(success_message):
                return success_message(data)
            return success_message
        return "Done."

    if isinstance(data, dict) and data.get("detail"):
        return f"Error: {data['detail']}"
    return f"Error: {res.status_code}"


async def send_help(update: Update) -> None:
    text = (
        "Commands:\n"
        "/setrole <email> <role>\n"
        "/setroletg <tg_id> <role>\n"
        "/setleader <club name> | <email>\n"
        "/setleadertg <club name> | <tg_id>\n"
        "/createclub <club name>\n\n"
        "/setemail <tg_id> <email>\n"
        "/email <email>\n\n"
        "Roles: student, club_leader, admin"
    )
    await update.message.reply_text(text)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    info = ensure_user(update)
    if not is_admin(update):
        intro_seen = info.get("bot_intro_seen") if isinstance(info, dict) else False
        if not intro_seen:
            await update.message.reply_text(
                "Welcome to Roomly!\n\n"
                "Please link your email:\n"
                "/email you@domain.com\n\n"
                "After that you can open the web app."
            )
            ensure_user(update, mark_intro=True)
        else:
            await update.message.reply_text(
                "Please link your email:\n"
                "/email you@domain.com"
            )
        return
    await send_help(update)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    info = ensure_user(update)
    if not is_admin(update):
        intro_seen = info.get("bot_intro_seen") if isinstance(info, dict) else False
        if not intro_seen:
            await update.message.reply_text(
                "Welcome to Roomly!\n\n"
                "Please link your email:\n"
                "/email you@domain.com"
            )
            ensure_user(update, mark_intro=True)
        else:
            await update.message.reply_text("Send your email with /email you@domain.com")
        return
    await send_help(update)


async def set_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ensure_user(update)
    if not is_admin(update):
        await update.message.reply_text("Access denied.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /setrole <email> <role>")
        return

    identifier = context.args[0]
    role = context.args[1]
    email = extract_email(identifier)
    if email:
        payload = {"email": email, "role": role}
    else:
        payload = {"user_id": int(identifier), "role": role}
    res = api_post("/api/bot/assign-role", payload)
    await update.message.reply_text(format_api_response(res, f"Role updated: {role}."))


async def set_role_tg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ensure_user(update)
    if not is_admin(update):
        await update.message.reply_text("Access denied.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /setroletg <tg_id> <role>")
        return

    tg_id = context.args[0]
    role = context.args[1]
    res = api_post("/api/bot/assign-role", {"tg_id": tg_id, "role": role})
    await update.message.reply_text(format_api_response(res, f"Role updated: {role}."))


async def set_leader(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ensure_user(update)
    if not is_admin(update):
        await update.message.reply_text("Access denied.")
        return
    pipe_args = parse_pipe_args(update)
    if pipe_args:
        club_name, identifier = pipe_args
        identifier = identifier.split()[0]
        email = extract_email(identifier)
        if email:
            payload = {"club_name": club_name, "email": email}
        elif identifier.isdigit():
            payload = {"club_name": club_name, "user_id": int(identifier)}
        else:
            await update.message.reply_text("Usage: /setleader <club name> | <user_id|email>")
            return
    else:
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /setleader <club name> | <email>")
            return

        club_id = context.args[0]
        identifier = context.args[1]
        if not club_id.isdigit():
            await update.message.reply_text("Use: /setleader <club name> | <email>")
            return
        email = extract_email(identifier)
        if email:
            payload = {"club_id": int(club_id), "email": email}
        else:
            payload = {"club_id": int(club_id), "user_id": int(identifier)}
    res = api_post("/api/bot/assign-club-leader", payload)
    await update.message.reply_text(format_api_response(res, "Leader assigned."))


async def set_leader_tg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ensure_user(update)
    if not is_admin(update):
        await update.message.reply_text("Access denied.")
        return
    pipe_args = parse_pipe_args(update)
    if pipe_args:
        club_name, tg_id = pipe_args
        tg_id = tg_id.split()[0]
        if not tg_id.isdigit():
            await update.message.reply_text("Usage: /setleadertg <club name> | <tg_id>")
            return
        res = api_post(
            "/api/bot/assign-club-leader",
            {"club_name": club_name, "tg_id": tg_id},
        )
    else:
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /setleadertg <club name> | <tg_id>")
            return

        club_id = context.args[0]
        tg_id = context.args[1]
        if not club_id.isdigit():
            await update.message.reply_text("Use: /setleadertg <club name> | <tg_id>")
            return
        res = api_post(
            "/api/bot/assign-club-leader",
            {"club_id": int(club_id), "tg_id": tg_id},
        )
    await update.message.reply_text(format_api_response(res, "Leader assigned."))


async def create_club(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ensure_user(update)
    if not is_admin(update):
        await update.message.reply_text("Access denied.")
        return
    name = " ".join(context.args).strip()
    if not name:
        await update.message.reply_text("Usage: /createclub <club name>")
        return

    res = api_post("/api/bot/create-club", {"name": name})
    await update.message.reply_text(
        format_api_response(res, lambda data: f"Club created: {data.get('name', name)}.")
    )


async def set_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ensure_user(update)
    if not is_admin(update):
        await update.message.reply_text("Access denied.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /setemail <tg_id> <email>")
        return

    identifier = context.args[0]
    email = extract_email(context.args[1])
    if not email:
        await update.message.reply_text("Invalid email.")
        return

    payload = {"email": email}
    if identifier.isdigit():
        payload["user_id"] = int(identifier)
    else:
        payload["tg_id"] = identifier

    res = api_post("/api/bot/set-email", payload)
    await update.message.reply_text(format_api_response(res, "Email linked."))


async def set_email_self(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ensure_user(update)
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /email <email>")
        return
    email = extract_email(context.args[0])
    if not email:
        await update.message.reply_text("Invalid email.")
        return
    user = update.effective_user
    if not user:
        await update.message.reply_text("User not found.")
        return

    res = api_post("/api/bot/set-email", {"tg_id": str(user.id), "email": email})
    await update.message.reply_text(
        format_api_response(res, "Email linked. You can open the web app.")
    )


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    if not BOT_ADMIN_TOKEN:
        raise RuntimeError("BOT_ADMIN_TOKEN is required")
    if not ADMIN_IDS:
        raise RuntimeError("BOT_ADMIN_IDS is required")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("setrole", set_role))
    app.add_handler(CommandHandler("setroletg", set_role_tg))
    app.add_handler(CommandHandler("setleader", set_leader))
    app.add_handler(CommandHandler("setleadertg", set_leader_tg))
    app.add_handler(CommandHandler("createclub", create_club))
    app.add_handler(CommandHandler("setemail", set_email))
    app.add_handler(CommandHandler("email", set_email_self))

    app.run_polling()


if __name__ == "__main__":
    main()
