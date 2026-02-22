"""Telegram bot handlers for simplified cashflow workflow."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Union
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.ai.parser import AIParserService
from app.bot import texts
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.states.exchange import AIInputStates, ManualEntryStates
from app.config import get_settings
from app.database.session import db_manager
from app.schemas.entry import EntryCreate
from app.security.telegram_auth import is_bot_user_allowed
from app.services.backup_service import BackupScheduler
from app.services.entry_service import EntryService

router = Router()


def _fmt(value: Union[Decimal, int, float], currency: str) -> str:
    return f"{Decimal(value):,.2f} {currency}".replace(",", " ")


async def _ensure_allowed_message(message: Message) -> bool:
    settings = get_settings()
    user_id = message.from_user.id if message.from_user else None
    if user_id is None or not is_bot_user_allowed(user_id, settings):
        await message.answer("Access denied.")
        return False
    return True


async def _ensure_allowed_callback(callback) -> bool:
    settings = get_settings()
    user_id = callback.from_user.id if callback.from_user else None
    if user_id is None or not is_bot_user_allowed(user_id, settings):
        await callback.message.answer("Access denied.")
        await callback.answer()
        return False
    return True


def _summary_from_data(data: dict) -> str:
    return (
        "Tasdiqlang:\n"
        f"Amount: {_fmt(Decimal(data['amount']), data['currency_code'])}\n"
        f"Flow: {data['flow_direction']}\n"
        f"Client: {data['client_name']}\n"
        f"Note: {data.get('note') or '-'}"
    )


@router.message(CommandStart())
async def on_start(message: Message, state: FSMContext) -> None:
    """Reset state and show main menu."""

    if not await _ensure_allowed_message(message):
        return
    await state.clear()
    await message.answer(texts.MAIN_MENU_TITLE, reply_markup=main_menu_keyboard())


@router.message(F.text.regexp(re.compile(r"^(hello|hi|hey|salom|assalomu alaykum)$", re.IGNORECASE)))
async def on_greeting(message: Message) -> None:
    """Reply to greetings and point user to main actions."""

    if not await _ensure_allowed_message(message):
        return
    await message.answer("Salom. Men tayyorman. ➕ New Entry yoki 🤖 AI Assistant ni tanlang.", reply_markup=main_menu_keyboard())


@router.message(F.text == texts.CANCEL_OPERATION)
async def cancel_operation(message: Message, state: FSMContext) -> None:
    """Cancel any in-progress flow."""

    if not await _ensure_allowed_message(message):
        return
    await state.clear()
    await message.answer("Operation cancelled.", reply_markup=main_menu_keyboard())


@router.message(Command("export_today"))
async def export_today_command(message: Message) -> None:
    """Manual CSV export trigger command."""

    await export_csv(message)


@router.message(F.text == texts.NEW_ENTRY)
async def start_new_entry(message: Message, state: FSMContext) -> None:
    """Start manual entry FSM."""

    if not await _ensure_allowed_message(message):
        return
    await state.clear()
    await state.set_state(ManualEntryStates.waiting_amount)
    await message.answer("1/5 Amount kiriting (masalan: 1000)")


@router.message(ManualEntryStates.waiting_amount)
async def entry_amount(message: Message, state: FSMContext) -> None:
    """Collect amount."""

    if not await _ensure_allowed_message(message):
        return

    try:
        amount = Decimal((message.text or "").strip())
        if amount <= 0:
            raise ValueError
    except Exception:  # noqa: BLE001
        await message.answer("Amount noto'g'ri. Raqam kiriting.")
        return

    await state.update_data(amount=str(amount))
    await state.set_state(ManualEntryStates.waiting_currency)
    await message.answer("2/5 Currency kiriting: USD / RUB / UZS")


@router.message(ManualEntryStates.waiting_currency)
async def entry_currency(message: Message, state: FSMContext) -> None:
    """Collect currency code."""

    if not await _ensure_allowed_message(message):
        return

    currency = (message.text or "").strip().upper()
    if currency not in {"USD", "RUB", "UZS"}:
        await message.answer("Currency faqat USD, RUB yoki UZS bo'lishi kerak.")
        return

    await state.update_data(currency_code=currency)
    await state.set_state(ManualEntryStates.waiting_flow)
    await message.answer(f"3/5 Flow tanlang: {texts.FLOW_IN} yoki {texts.FLOW_OUT}")


@router.message(ManualEntryStates.waiting_flow)
async def entry_flow(message: Message, state: FSMContext) -> None:
    """Collect flow direction."""

    if not await _ensure_allowed_message(message):
        return

    raw = (message.text or "").strip().lower()
    if "in" in raw or "📥" in raw:
        flow = "INFLOW"
    elif "out" in raw or "📤" in raw:
        flow = "OUTFLOW"
    else:
        await message.answer(f"Flow noto'g'ri. {texts.FLOW_IN} yoki {texts.FLOW_OUT} yozing.")
        return

    await state.update_data(flow_direction=flow)
    await state.set_state(ManualEntryStates.waiting_client)
    await message.answer("4/5 Client name kiriting")


@router.message(ManualEntryStates.waiting_client)
async def entry_client(message: Message, state: FSMContext) -> None:
    """Collect client name."""

    if not await _ensure_allowed_message(message):
        return

    client_name = (message.text or "").strip()
    if not client_name:
        await message.answer("Client name bo'sh bo'lmasin.")
        return

    await state.update_data(client_name=client_name)
    await state.set_state(ManualEntryStates.waiting_note)
    await message.answer("5/5 Note (optional). O'tkazib yuborish uchun '-' yuboring.")


@router.message(ManualEntryStates.waiting_note)
async def entry_note(message: Message, state: FSMContext) -> None:
    """Collect optional note and show confirmation."""

    if not await _ensure_allowed_message(message):
        return

    note_raw = (message.text or "").strip()
    note = None if note_raw == "-" else note_raw
    await state.update_data(note=note)

    data = await state.get_data()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Tasdiqlash", callback_data="manual_confirm")],
            [InlineKeyboardButton(text="Bekor qilish", callback_data="manual_cancel")],
        ]
    )

    await state.set_state(ManualEntryStates.waiting_confirm)
    await message.answer(_summary_from_data(data), reply_markup=keyboard)


@router.callback_query(F.data == "manual_cancel")
async def manual_cancel(callback, state: FSMContext):
    """Cancel manual flow."""

    if not await _ensure_allowed_callback(callback):
        return
    await state.clear()
    await callback.message.answer("Entry cancelled.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "manual_confirm")
async def manual_confirm(callback, state: FSMContext):
    """Create entry from manual flow."""

    if not await _ensure_allowed_callback(callback):
        return

    data = await state.get_data()
    try:
        payload = EntryCreate(
            amount=Decimal(data["amount"]),
            currency_code=data["currency_code"],
            flow_direction=data["flow_direction"],
            client_name=data["client_name"],
            note=data.get("note"),
        )
        service = EntryService()
        async with db_manager.session_factory() as session:
            entry = await service.create_entry(
                session=session,
                payload=payload,
                created_by_telegram_id=callback.from_user.id,
            )
        await callback.message.answer(f"Entry #{entry.id} saqlandi.", reply_markup=main_menu_keyboard())
    except Exception as exc:  # noqa: BLE001
        await callback.message.answer(f"Xatolik: {exc}")

    await state.clear()
    await callback.answer()


@router.message(F.text == texts.AI_ASSISTANT_INPUT)
async def start_ai_input(message: Message, state: FSMContext) -> None:
    """Start AI parser flow."""

    if not await _ensure_allowed_message(message):
        return
    await state.clear()
    await state.set_state(AIInputStates.waiting_raw_text)
    await message.answer("AI uchun matn yuboring. Masalan: 'Ali 1000 usd oldim'.")


@router.message(AIInputStates.waiting_raw_text)
async def ai_raw_input(message: Message, state: FSMContext) -> None:
    """Parse free text using AI and ask for confirmation."""

    if not await _ensure_allowed_message(message):
        return

    text = (message.text or "").strip()
    if text.lower() in {"hello", "hi", "hey", "salom", "assalomu alaykum"}:
        await message.answer("Salom. Entry matnini yuboring: 'Ali 1000 usd oldim'.")
        return

    try:
        parser = AIParserService.from_settings(get_settings())
        parsed = await parser.parse(text)
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"AI parse failed: {exc}")
        return

    data = parsed.model_dump()
    if not data.get("client_name"):
        await state.update_data(ai_parsed=data)
        await state.set_state(AIInputStates.waiting_client)
        await message.answer("Client name topilmadi. Kiriting:")
        return

    await state.update_data(ai_parsed=data)
    await state.set_state(AIInputStates.waiting_confirm)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Tasdiqlash", callback_data="ai_confirm")],
            [InlineKeyboardButton(text="O'zgartirish", callback_data="ai_edit")],
            [InlineKeyboardButton(text="Bekor qilish", callback_data="ai_cancel")],
        ]
    )
    await message.answer(_summary_from_data(data), reply_markup=keyboard)


@router.message(AIInputStates.waiting_client)
async def ai_client_input(message: Message, state: FSMContext) -> None:
    """Collect missing client name for AI flow."""

    if not await _ensure_allowed_message(message):
        return

    client_name = (message.text or "").strip()
    if not client_name:
        await message.answer("Client name bo'sh bo'lmasin.")
        return

    data = await state.get_data()
    parsed = data.get("ai_parsed", {})
    parsed["client_name"] = client_name
    await state.update_data(ai_parsed=parsed)
    await state.set_state(AIInputStates.waiting_confirm)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Tasdiqlash", callback_data="ai_confirm")],
            [InlineKeyboardButton(text="O'zgartirish", callback_data="ai_edit")],
            [InlineKeyboardButton(text="Bekor qilish", callback_data="ai_cancel")],
        ]
    )
    await message.answer(_summary_from_data(parsed), reply_markup=keyboard)


@router.callback_query(F.data == "ai_edit")
async def ai_edit(callback, state: FSMContext):
    """Return to raw text input."""

    if not await _ensure_allowed_callback(callback):
        return
    await state.set_state(AIInputStates.waiting_raw_text)
    await callback.message.answer("Yangi matn yuboring.")
    await callback.answer()


@router.callback_query(F.data == "ai_cancel")
async def ai_cancel(callback, state: FSMContext):
    """Cancel AI flow."""

    if not await _ensure_allowed_callback(callback):
        return
    await state.clear()
    await callback.message.answer("AI flow cancelled.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "ai_confirm")
async def ai_confirm(callback, state: FSMContext):
    """Create entry from AI confirmation."""

    if not await _ensure_allowed_callback(callback):
        return

    data = await state.get_data()
    parsed = data.get("ai_parsed")
    if not parsed:
        await callback.message.answer("No data.")
        await callback.answer()
        return

    try:
        payload = EntryCreate.model_validate(parsed)
        service = EntryService()
        async with db_manager.session_factory() as session:
            entry = await service.create_entry(
                session=session,
                payload=payload,
                created_by_telegram_id=callback.from_user.id,
            )
        await callback.message.answer(f"AI entry #{entry.id} saqlandi.", reply_markup=main_menu_keyboard())
    except Exception as exc:  # noqa: BLE001
        await callback.message.answer(f"Xatolik: {exc}")

    await state.clear()
    await callback.answer()


@router.message(F.text == texts.REPORTS)
async def show_reports(message: Message) -> None:
    """Show daily profit, balances, client debts and cash total."""

    if not await _ensure_allowed_message(message):
        return

    settings = get_settings()
    service = EntryService()
    today = datetime.now(ZoneInfo(settings.timezone)).date()

    async with db_manager.session_factory() as session:
        daily = await service.daily_profit_by_currency(session, today)
        balances = await service.currency_balances(session)
        debts = await service.client_debts(session)
        _, uzs_total = await service.cash_total(session)

    lines = [f"Hisobot ({today.isoformat()}):", "", "Kunlik foyda (valyuta bo'yicha):"]
    for currency, amount in sorted(daily.items()):
        lines.append(f"- {currency}: {_fmt(amount, currency)}")

    lines.append("")
    lines.append("Valyuta bo'yicha balans:")
    for currency, amount in sorted(balances.items()):
        lines.append(f"- {currency}: {_fmt(amount, currency)}")

    lines.append("")
    lines.append("Client bo'yicha qarz (top 10):")
    for client_name, currency, debt in debts[:10]:
        lines.append(f"- {client_name} [{currency}]: {_fmt(debt, currency)}")

    lines.append("")
    lines.append(f"Jami kassadagi pul (UZS): {_fmt(uzs_total, 'UZS')}")

    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())


@router.message(F.text == texts.EXPORT_CSV)
async def export_csv(message: Message) -> None:
    """Run daily CSV export and send files to Telegram chat."""

    if not await _ensure_allowed_message(message):
        return

    settings = get_settings()
    today = datetime.now(ZoneInfo(settings.timezone)).date()
    scheduler = BackupScheduler(db_manager.session_factory, settings)

    try:
        result = await scheduler.run_once(today)

        # Send CSV files directly to the user's chat
        from aiogram.types import FSInputFile

        entries_file = FSInputFile(str(result.entries_csv), filename=result.entries_csv.name)
        reports_file = FSInputFile(str(result.reports_csv), filename=result.reports_csv.name)

        await message.answer_document(entries_file, caption=f"📋 Entries: {today.isoformat()}")
        await message.answer_document(reports_file, caption=f"📊 Reports: {today.isoformat()}")
        await message.answer("✅ CSV fayllar yuborildi!", reply_markup=main_menu_keyboard())

    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Export xatolik: {exc}", reply_markup=main_menu_keyboard())


@router.message(Command("delete"))
async def delete_entry_command(message: Message) -> None:
    """Soft delete an entry by ID with confirmation: /delete <id>."""

    if not await _ensure_allowed_message(message):
        return

    parts = (message.text or "").strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("❌ Foydalanish: /delete <entry_id>\nMasalan: /delete 5")
        return

    entry_id = int(parts[1])
    service = EntryService()

    async with db_manager.session_factory() as session:
        entry = await service.get_entry_by_id(session, entry_id)

    if entry is None:
        await message.answer(f"❌ Entry #{entry_id} topilmadi yoki allaqachon o'chirilgan.")
        return

    direction = "📥 KIRIM" if entry.flow_direction == "INFLOW" else "📤 CHIQIM"
    summary = (
        f"🗑 O'chirmoqchimisiz?\n\n"
        f"#{entry.id} | {direction}\n"
        f"Amount: {_fmt(entry.amount, entry.currency_code)}\n"
        f"Client: {entry.client_name}\n"
        f"Note: {entry.note or '-'}\n"
        f"Sana: {entry.created_at.strftime('%d.%m.%Y %H:%M')}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"del_yes_{entry_id}")],
            [InlineKeyboardButton(text="❌ Yo'q, bekor qil", callback_data="del_no")],
        ]
    )
    await message.answer(summary, reply_markup=keyboard)


@router.callback_query(F.data.startswith("del_yes_"))
async def confirm_delete(callback, state: FSMContext):
    """Execute soft delete after user confirmation."""

    if not await _ensure_allowed_callback(callback):
        return

    entry_id = int(callback.data.split("_")[-1])
    service = EntryService()

    async with db_manager.session_factory() as session:
        entry = await service.soft_delete_entry(session, entry_id)

    if entry:
        await callback.message.answer(
            f"✅ Entry #{entry_id} o'chirildi (soft delete).\n"
            f"Qayta tiklash uchun: /restore {entry_id}",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await callback.message.answer(f"❌ Entry #{entry_id} topilmadi.", reply_markup=main_menu_keyboard())

    await callback.answer()


@router.callback_query(F.data == "del_no")
async def cancel_delete(callback, state: FSMContext):
    """Cancel delete operation."""

    if not await _ensure_allowed_callback(callback):
        return
    await callback.message.answer("O'chirish bekor qilindi.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.message(Command("restore"))
async def restore_entry_command(message: Message) -> None:
    """Restore a soft-deleted entry: /restore <id>."""

    if not await _ensure_allowed_message(message):
        return

    parts = (message.text or "").strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("❌ Foydalanish: /restore <entry_id>\nMasalan: /restore 5")
        return

    entry_id = int(parts[1])
    service = EntryService()

    async with db_manager.session_factory() as session:
        entry = await service.restore_entry(session, entry_id)

    if entry:
        await message.answer(
            f"✅ Entry #{entry_id} qayta tiklandi!\n"
            f"Amount: {_fmt(entry.amount, entry.currency_code)}\n"
            f"Client: {entry.client_name}",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await message.answer(f"❌ Entry #{entry_id} topilmadi yoki allaqachon faol.", reply_markup=main_menu_keyboard())

