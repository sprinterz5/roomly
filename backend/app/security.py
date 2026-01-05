import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl

import jwt

from .config import BOT_TOKEN, JWT_ALG, JWT_EXPIRES_MINUTES, JWT_SECRET


class AuthError(Exception):
    pass


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRES_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError as exc:
        raise AuthError("invalid token") from exc


def _build_data_check_string(data: Dict[str, str]) -> str:
    pairs = [f"{k}={v}" for k, v in sorted(data.items()) if k != "hash"]
    return "\n".join(pairs)


def verify_telegram_init_data(init_data: str) -> Optional[Dict[str, Any]]:
    if not BOT_TOKEN:
        raise AuthError("BOT_TOKEN is not configured")

    data = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = data.get("hash")
    if not received_hash:
        return None

    data_check_string = _build_data_check_string(data)
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if calculated_hash != received_hash:
        return None

    user_raw = data.get("user")
    if not user_raw:
        return None

    return json.loads(user_raw)
