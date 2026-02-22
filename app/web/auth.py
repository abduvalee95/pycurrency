import hashlib
import hmac
from urllib.parse import parse_qsl

from fastapi import HTTPException
from app.config import get_settings


def validate_telegram_data(init_data: str) -> bool:
    """Validate data received from Telegram Mini App.
    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    settings = get_settings()
    token = settings.telegram_bot_token
    
    if not init_data:
        return False
        
    try:
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
        if "hash" not in parsed_data:
            return False

        hash_value = parsed_data.pop("hash")
        
        # Sort and join all key=value pairs
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )
        
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=token.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return calculated_hash == hash_value
        
    except Exception:
        return False
