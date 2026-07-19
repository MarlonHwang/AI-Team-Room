"""Small HMAC token format with meeting and participant identity binding."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time


def random_token() -> str:
    return secrets.token_urlsafe(32)


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class TokenSigner:
    def __init__(self, secret: str):
        if len(secret) < 32:
            raise ValueError("control token must contain at least 32 characters")
        self.secret = secret.encode("utf-8")

    def issue(self, meeting_id: str, participant: str) -> str:
        payload = {
            "meeting": meeting_id,
            "participant": participant,
            "issued": int(time.time()),
            "nonce": secrets.token_hex(8),
        }
        body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
        signature = _b64(hmac.new(self.secret, body.encode(), hashlib.sha256).digest())
        return f"atr1.{body}.{signature}"

    def verify(self, token: str) -> dict:
        try:
            version, body, signature = token.split(".")
            expected = _b64(hmac.new(self.secret, body.encode(), hashlib.sha256).digest())
            if version != "atr1" or not hmac.compare_digest(signature, expected):
                raise ValueError
            payload = json.loads(_unb64(body))
            if not isinstance(payload.get("meeting"), str) or not isinstance(payload.get("participant"), str):
                raise ValueError
            return payload
        except (ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("invalid participant token") from exc
