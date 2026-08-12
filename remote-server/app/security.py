from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Final

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
TOKEN_PREFIX_LENGTH: Final[int] = 18


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def generate_access_token(app_type: str) -> str:
    prefix = "mx_live_" if app_type == "matrix_generator" else "rhp_live_"
    return prefix + secrets.token_urlsafe(36)


def token_prefix(token: str) -> str:
    return token[:TOKEN_PREFIX_LENGTH]


def hash_access_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_matches(stored_hash: str, token: str) -> bool:
    return hmac.compare_digest(stored_hash, hash_access_token(token))


def generate_activation_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    raw = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(24)
