"""Telegram user authorization utilities for bot/web/api."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Optional
from urllib.parse import parse_qsl

from fastapi import Depends, Request

from app.api.errors import AppError
from app.config import Settings, get_settings


def parse_allowed_ids(raw: str) -> set[int]:
    """Parse comma-separated allowed Telegram IDs from config."""

    ids: set[int] = set()
    for chunk in raw.split(","):
        value = chunk.strip()
        if not value:
            continue
        try:
            ids.add(int(value))
        except ValueError:
            continue
    return ids


def is_bot_user_allowed(user_id: int, settings: Settings) -> bool:
    """Return whether bot user is allowed by configured whitelist."""

    allowed = parse_allowed_ids(settings.allowed_telegram_ids)
    if not allowed:
        return True
    return user_id in allowed


def _verify_init_data_and_get_user_id(init_data: str, bot_token: str) -> Optional[int]:
    """Verify Telegram initData signature and return user ID."""

    if not init_data or not bot_token:
        return None

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    hash_value = parsed.pop("hash", None)
    if not hash_value:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items(), key=lambda item: item[0]))

    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, hash_value):
        return None

    user_raw = parsed.get("user")
    if user_raw:
        try:
            user_obj = json.loads(user_raw)
            user_id = user_obj.get("id")
            return int(user_id) if user_id is not None else None
        except Exception:
            return None

    user_id_raw = parsed.get("user_id")
    if user_id_raw:
        try:
            return int(user_id_raw)
        except ValueError:
            return None

    return None


def _extract_telegram_id_from_request(
    request: Request,
    settings: Settings,
    *,
    allow_dev_header: bool,
) -> Optional[int]:
    """Resolve Telegram user ID from verified initData or dev header."""

    init_data = request.headers.get("X-Telegram-Init-Data")
    if init_data:
        return _verify_init_data_and_get_user_id(init_data, settings.telegram_bot_token)

    if allow_dev_header:
        direct_id = request.headers.get("X-Telegram-Id")
        if direct_id:
            try:
                return int(direct_id)
            except ValueError:
                return None

    return None


async def require_api_auth(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Optional[int]:
    """Enforce request-level Telegram auth for API routes."""

    allowed = parse_allowed_ids(settings.allowed_telegram_ids)
    enforce = settings.telegram_webapp_enforce or bool(allowed)

    user_id = _extract_telegram_id_from_request(
        request,
        settings,
        allow_dev_header=(not enforce) or settings.debug,
    )

    if enforce and user_id is None:
        raise AppError("Telegram authorization required", status_code=403)

    if user_id is not None and allowed and user_id not in allowed:
        raise AppError("Access denied for this Telegram user", status_code=403)

    request.state.telegram_id = user_id
    request.state.telegram_auth_enforced = enforce
    return user_id


async def get_request_telegram_id(
    request: Request,
    _auth: Optional[int] = Depends(require_api_auth),
) -> int:
    """Return authorized Telegram user ID for write operations."""

    user_id = getattr(request.state, "telegram_id", None)
    if user_id is None and not getattr(request.state, "telegram_auth_enforced", False):
        # Development fallback when strict Telegram auth is disabled.
        return 0
    if user_id is None:
        raise AppError("Telegram ID is required for this operation", status_code=403)
    return int(user_id)
