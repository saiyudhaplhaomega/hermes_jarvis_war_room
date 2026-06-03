
"""JWT auth using PyJWT + HS256."""
import os, jwt, secrets
from datetime import datetime, timedelta, timezone
from core.config import SECRET_KEY_FILE, JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_ABSOLUTE_HOURS


def _get_or_create_secret() -> str:
    if SECRET_KEY_FILE.exists():
        return SECRET_KEY_FILE.read_text()
    key = secrets.token_hex(32)
    SECRET_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SECRET_KEY_FILE.write_text(key)
    os.chmod(SECRET_KEY_FILE, 0o600)
    return key


SECRET = _get_or_create_secret()


def create_token(subject: str, fresh: bool = False) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
        "abs": now + timedelta(hours=JWT_ABSOLUTE_HOURS),
        "fresh": fresh,
    }
    return jwt.encode(payload, SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET, algorithms=[JWT_ALGORITHM])
