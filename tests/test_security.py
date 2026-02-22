from __future__ import annotations

from app.config import Settings
from app.security.telegram_auth import is_bot_user_allowed, parse_allowed_ids


def test_parse_allowed_ids() -> None:
    parsed = parse_allowed_ids("1001, 1002,invalid,,1003")
    assert parsed == {1001, 1002, 1003}


def test_bot_user_whitelist() -> None:
    settings = Settings(allowed_telegram_ids="10,20")
    assert is_bot_user_allowed(10, settings) is True
    assert is_bot_user_allowed(99, settings) is False
