"""Reply keyboard builders."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.types.web_app_info import WebAppInfo

from app.bot import texts
from app.config import get_settings


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard with operator actions."""

    settings = get_settings()
    
    # Base layout
    keyboard = [
        [KeyboardButton(text=texts.NEW_ENTRY), KeyboardButton(text=texts.AI_CHAT)],
        [KeyboardButton(text=texts.REPORTS), KeyboardButton(text=texts.EXPORT_CSV)],
        [KeyboardButton(text=texts.CANCEL_OPERATION)],
    ]
    
    # Add Dashboard Web App button if URL is configured
    if settings.webapp_url:
        webapp_btn = KeyboardButton(text="📊 Dashboard (Web)", web_app=WebAppInfo(url=settings.webapp_url))
        keyboard.insert(0, [webapp_btn])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )
