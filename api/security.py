import base64
import hashlib
import hmac
import json
import os
import time


SECRET = os.getenv("API_TOKEN_SECRET", "change-me-in-production")
TTL_SECONDS = int(os.getenv("API_TOKEN_TTL_SECONDS", "43200"))  # 12h


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64url(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("ascii"))


def create_token(user_id: int, email: str) -> str:
    payload = {
        "uid": int(user_id),
        "email": email,
        "exp": int(time.time()) + TTL_SECONDS,
    }
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64url(sig)}"


def verify_token(token: str) -> dict | None:
    try:
        body, sig = token.split(".", 1)
        expected = hmac.new(SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        got = _unb64url(sig)
        if not hmac.compare_digest(expected, got):
            return None
        payload = json.loads(_unb64url(body).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
