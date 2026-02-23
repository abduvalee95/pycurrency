"""Admin bot handlers: DB management for owner only."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from sqlalchemy import text

from app.bot import texts
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.config import get_settings
from app.database.session import db_manager
from app.security.telegram_auth import parse_allowed_ids

router = Router()


def _is_owner(user_id: int) -> bool:
    """Check if user is the first (owner) ID in ALLOWED_TELEGRAM_IDS."""
    settings = get_settings()
    allowed = sorted(parse_allowed_ids(settings.allowed_telegram_ids))
    if not allowed:
        return False
    return user_id == allowed[0]


@router.message(Command("admin"))
async def admin_menu(message: Message, state: FSMContext) -> None:
    """Show admin panel (owner only)."""
    user_id = message.from_user.id if message.from_user else None
    if user_id is None or not _is_owner(user_id):
        await message.answer("⛔ Доступ запрещен. Только для администратора.")
        return

    await state.clear()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Очистить базу данных", callback_data="admin_clear_db")],
            [InlineKeyboardButton(text="📊 Статистика БД", callback_data="admin_db_stats")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_close")],
        ]
    )
    await message.answer(texts.ADMIN_MENU_TITLE, reply_markup=keyboard)


@router.callback_query(F.data == "admin_db_stats")
async def admin_db_stats(callback: CallbackQuery) -> None:
    """Show DB entry count statistics."""
    user_id = callback.from_user.id if callback.from_user else None
    if user_id is None or not _is_owner(user_id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    async with db_manager.session_factory() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM cash_entries WHERE deleted_at IS NULL"))
        active_count = result.scalar_one()
        result2 = await session.execute(text("SELECT COUNT(*) FROM cash_entries WHERE deleted_at IS NOT NULL"))
        deleted_count = result2.scalar_one()
        result3 = await session.execute(text("SELECT COUNT(*) FROM cash_entries"))
        total_count = result3.scalar_one()

    await callback.message.answer(
        f"📊 Статистика базы данных:\n\n"
        f"✅ Активные записи: {active_count}\n"
        f"🗑 Удалённые (soft): {deleted_count}\n"
        f"📦 Всего в таблице: {total_count}"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_clear_db")
async def admin_clear_db_confirm(callback: CallbackQuery) -> None:
    """Ask for confirmation before clearing DB."""
    user_id = callback.from_user.id if callback.from_user else None
    if user_id is None or not _is_owner(user_id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚠️ Да, очистить ВСЁ", callback_data="admin_clear_db_yes")],
            [InlineKeyboardButton(text="🗑 Только удалённые (soft)", callback_data="admin_clear_db_soft")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_clear_db_no")],
        ]
    )
    await callback.message.edit_text(
        "⚠️ ВНИМАНИЕ!\n\n"
        "Выберите действие:\n"
        "• «Да, очистить ВСЁ» — удалит ВСЕ записи безвозвратно\n"
        "• «Только удалённые» — удалит только soft-deleted записи\n\n"
        "Это действие необратимо!",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "admin_clear_db_yes")
async def admin_clear_db_execute(callback: CallbackQuery) -> None:
    """Truncate cash_entries table completely."""
    user_id = callback.from_user.id if callback.from_user else None
    if user_id is None or not _is_owner(user_id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)

    try:
        async with db_manager.session_factory() as session:
            async with session.begin():
                await session.execute(text("TRUNCATE TABLE cash_entries RESTART IDENTITY CASCADE"))
        await callback.message.answer(
            "✅ База данных полностью очищена!\n"
            "Все записи удалены, счётчик ID сброшен.",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as exc:  # noqa: BLE001
        await callback.message.answer(f"❌ Ошибка очистки: {exc}", reply_markup=main_menu_keyboard())

    await callback.answer()


@router.callback_query(F.data == "admin_clear_db_soft")
async def admin_clear_soft_deleted(callback: CallbackQuery) -> None:
    """Permanently remove only soft-deleted entries."""
    user_id = callback.from_user.id if callback.from_user else None
    if user_id is None or not _is_owner(user_id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)

    try:
        async with db_manager.session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    text("DELETE FROM cash_entries WHERE deleted_at IS NOT NULL")
                )
                deleted_count = result.rowcount
        await callback.message.answer(
            f"✅ Удалено {deleted_count} soft-deleted записей.",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as exc:  # noqa: BLE001
        await callback.message.answer(f"❌ Ошибка: {exc}", reply_markup=main_menu_keyboard())

    await callback.answer()


@router.callback_query(F.data == "admin_clear_db_no")
async def admin_clear_db_cancel(callback: CallbackQuery) -> None:
    """Cancel DB clearing."""
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Очистка отменена.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_close")
async def admin_close(callback: CallbackQuery) -> None:
    """Close admin panel."""
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Админ панель закрыта.", reply_markup=main_menu_keyboard())
    await callback.answer()
