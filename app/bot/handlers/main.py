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
        await message.answer("Доступ запрещен.")
        return False
    return True


async def _ensure_allowed_callback(callback) -> bool:
    settings = get_settings()
    user_id = callback.from_user.id if callback.from_user else None
    if user_id is None or not is_bot_user_allowed(user_id, settings):
        await callback.message.answer("Доступ запрещен.")
        await callback.answer()
        return False
    return True


def _summary_from_data(data: dict) -> str:
    return (
        "Подтвердите:\n"
        f"Сумма: {_fmt(Decimal(data['amount']), data['currency_code'])}\n"
        f"Тип: {data['flow_direction']}\n"
        f"Клиент: {data['client_name']}\n"
        f"Заметка: {data.get('note') or '-'}"
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
    await message.answer("Привет. Я готов. Выберите ➕ Новая запись или 🤖 AI Ассистент.", reply_markup=main_menu_keyboard())


@router.message(F.text == texts.CANCEL_OPERATION)
async def cancel_operation(message: Message, state: FSMContext) -> None:
    """Cancel any in-progress flow."""

    if not await _ensure_allowed_message(message):
        return
    await state.clear()
    await message.answer("Операция отменена.", reply_markup=main_menu_keyboard())


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
    await message.answer("1/5 Введите сумму (например: 1000)")


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
        await message.answer("Неверная сумма. Введите число.")
        return

    await state.update_data(amount=str(amount))
    await state.set_state(ManualEntryStates.waiting_currency)
    await message.answer("2/5 Введите валюту: USD / RUB / UZS / KGS / EUR")


@router.message(ManualEntryStates.waiting_currency)
async def entry_currency(message: Message, state: FSMContext) -> None:
    """Collect currency code."""

    if not await _ensure_allowed_message(message):
        return

    currency = (message.text or "").strip().upper()
    if currency not in {"USD", "RUB", "UZS", "KGS", "EUR"}:
        await message.answer("Валюта должна быть USD, RUB, UZS, KGS или EUR.")
        return

    await state.update_data(currency_code=currency)
    await state.set_state(ManualEntryStates.waiting_flow)
    await message.answer(f"3/5 Выберите тип: {texts.FLOW_IN} или {texts.FLOW_OUT}")


@router.message(ManualEntryStates.waiting_flow)
async def entry_flow(message: Message, state: FSMContext) -> None:
    """Collect flow direction."""

    if not await _ensure_allowed_message(message):
        return

    raw = (message.text or "").strip().lower()
    if "in" in raw or "📥" in raw:
        flow = "INFLOW"
    elif "out" in raw or "📤" in raw or "расход" in raw:
        flow = "OUTFLOW"
    else:
        await message.answer(f"Неверный тип. Напишите {texts.FLOW_IN} или {texts.FLOW_OUT}.")
        return

    await state.update_data(flow_direction=flow)
    await state.set_state(ManualEntryStates.waiting_client)
    await message.answer("4/5 Введите имя клиента")


@router.message(ManualEntryStates.waiting_client)
async def entry_client(message: Message, state: FSMContext) -> None:
    """Collect client name."""

    if not await _ensure_allowed_message(message):
        return

    client_name = (message.text or "").strip()
    if not client_name:
        await message.answer("Имя клиента не может быть пустым.")
        return

    await state.update_data(client_name=client_name)
    await state.set_state(ManualEntryStates.waiting_note)
    await message.answer("5/5 Заметка (опционально). Отправьте '-', чтобы пропустить.")


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
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="manual_confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="manual_cancel")],
        ]
    )

    await state.set_state(ManualEntryStates.waiting_confirm)
    await message.answer(_summary_from_data(data), reply_markup=keyboard)


@router.callback_query(F.data == "manual_cancel")
async def manual_cancel(callback, state: FSMContext):
    """Cancel manual flow."""

    if not await _ensure_allowed_callback(callback):
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.clear()
    await callback.message.answer("Запись отменена.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "manual_confirm")
async def manual_confirm(callback, state: FSMContext):
    """Create entry from manual flow."""

    if not await _ensure_allowed_callback(callback):
        return
    await callback.message.edit_reply_markup(reply_markup=None)

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
        await callback.message.answer(f"Запись #{entry.id} сохранена.", reply_markup=main_menu_keyboard())
    except Exception as exc:  # noqa: BLE001
        await callback.message.answer(f"Ошибка: {exc}")

    await state.clear()
    await callback.answer()


@router.message(F.text == texts.AI_ASSISTANT_INPUT)
async def start_ai_input(message: Message, state: FSMContext) -> None:
    """Start AI parser flow."""

    if not await _ensure_allowed_message(message):
        return
    await state.clear()
    await state.set_state(AIInputStates.waiting_raw_text)
    await message.answer("Отправьте текст для AI. Например: 'Али дал 1000 usd'.")


@router.message(AIInputStates.waiting_raw_text)
async def ai_raw_input(message: Message, state: FSMContext) -> None:
    """Parse free text using AI and ask for confirmation."""

    if not await _ensure_allowed_message(message):
        return

    text = (message.text or "").strip()
    if text.lower() in {"hello", "hi", "hey", "salom", "привет", "здравствуйте"}:
        await message.answer("Привет. Отправьте текст записи: 'Али дал 1000 usd'.")
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
        await message.answer("Имя клиента не найдено. Введите:")
        return

    await state.update_data(ai_parsed=data)
    await state.set_state(AIInputStates.waiting_confirm)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="ai_confirm")],
            [InlineKeyboardButton(text="✏️ Изменить", callback_data="ai_edit")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="ai_cancel")],
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
        await message.answer("Имя клиента не может быть пустым.")
        return

    data = await state.get_data()
    parsed = data.get("ai_parsed", {})
    parsed["client_name"] = client_name
    await state.update_data(ai_parsed=parsed)
    await state.set_state(AIInputStates.waiting_confirm)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="ai_confirm")],
            [InlineKeyboardButton(text="✏️ Изменить", callback_data="ai_edit")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="ai_cancel")],
        ]
    )
    await message.answer(_summary_from_data(parsed), reply_markup=keyboard)


@router.callback_query(F.data == "ai_edit")
async def ai_edit(callback, state: FSMContext):
    """Return to raw text input."""

    if not await _ensure_allowed_callback(callback):
        return
    await state.set_state(AIInputStates.waiting_raw_text)
    await callback.message.answer("Отправьте новый текст.")
    await callback.answer()


@router.callback_query(F.data == "ai_cancel")
async def ai_cancel(callback, state: FSMContext):
    """Cancel AI flow."""

    if not await _ensure_allowed_callback(callback):
        return
    await state.clear()
    await callback.message.answer("AI ввод отменен.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "ai_confirm")
async def ai_confirm(callback, state: FSMContext):
    """Create entry from AI confirmation."""

    if not await _ensure_allowed_callback(callback):
        return

    data = await state.get_data()
    parsed = data.get("ai_parsed")
    if not parsed:
        await callback.message.answer("Нет данных.")
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
        await callback.message.answer(f"AI запись #{entry.id} сохранена.", reply_markup=main_menu_keyboard())
    except Exception as exc:  # noqa: BLE001
        await callback.message.answer(f"Ошибка: {exc}")

    await state.clear()
    await callback.answer()


@router.message(F.text == texts.REPORTS)
async def show_reports(message: Message) -> None:
    """Show balances, today's operations, and client debts."""

    if not await _ensure_allowed_message(message):
        return

    settings = get_settings()
    service = EntryService()
    today = datetime.now(ZoneInfo(settings.timezone)).date()

    async with db_manager.session_factory() as session:
        balances = await service.currency_balances(session)
        daily_profits = await service.daily_profit_by_currency(session, today)
        debts = await service.client_debts(session)
        _, kgs_total = await service.cash_total(session)
        entries = await service.entries_for_day(session, today)

    lines = [f"📊 Отчет ({today.isoformat()}):", ""]

    lines.append("💰 Баланс (по валютам):")
    for currency, amount in sorted(balances.items()):
        lines.append(f"  {currency}: {_fmt(amount, currency)}")

    lines.append("")
    lines.append("📈 Сегодняшняя чистая прибыль (Приход - Расход):")
    if daily_profits:
        for currency, amount in sorted(daily_profits.items()):
            sign = "+" if amount >= 0 else ""
            lines.append(f"  {currency}: {sign}{_fmt(amount, currency)}")
    else:
        lines.append("  Сегодня операций нет.")

    lines.append("")
    lines.append(f"Количество операций сегодня: {len(entries)}")

    if entries:
        lines.append("")
        lines.append("Последние операции:")
        for entry in entries[-10:]:
            sign = "взял +" if entry.flow_direction == "INFLOW" else "продал -"
            note_str = f" | {entry.note}" if entry.note else ""
            lines.append(
                f"  #{entry.id} | {sign} {_fmt(entry.amount, entry.currency_code)} "
                f"| {entry.client_name}{note_str}"
            )

    lines.append("")
    lines.append("Долги по клиентам (топ 10):")
    for client_name, currency, debt in debts[:10]:
        lines.append(f"  {client_name} [{currency}]: {_fmt(debt, currency)}")

    lines.append("")
    lines.append(f"💵 Итого в кассе (KGS): {_fmt(kgs_total, 'KGS')}")

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

        await message.answer_document(entries_file, caption=f"📋 Записи: {today.isoformat()}")
        await message.answer_document(reports_file, caption=f"📊 Отчеты: {today.isoformat()}")
        await message.answer("✅ CSV файлы отправлены!", reply_markup=main_menu_keyboard())

    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Ошибка экспорта: {exc}", reply_markup=main_menu_keyboard())


@router.message(Command("delete"))
async def delete_entry_command(message: Message) -> None:
    """Soft delete an entry by ID with confirmation: /delete <id>."""

    if not await _ensure_allowed_message(message):
        return

    parts = (message.text or "").strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("❌ Использование: /delete <entry_id>\nНапример: /delete 5")
        return

    entry_id = int(parts[1])
    service = EntryService()

    async with db_manager.session_factory() as session:
        entry = await service.get_entry_by_id(session, entry_id)

    if entry is None:
        await message.answer(f"❌ Запись #{entry_id} не найдена или уже удалена.")
        return

    direction = "📥 ПРИХОД" if entry.flow_direction == "INFLOW" else "📤 РАСХОД"
    summary = (
        f"🗑 Хотите удалить?\n\n"
        f"#{entry.id} | {direction}\n"
        f"Сумма: {_fmt(entry.amount, entry.currency_code)}\n"
        f"Клиент: {entry.client_name}\n"
        f"Заметка: {entry.note or '-'}\n"
        f"Дата: {entry.created_at.strftime('%d.%m.%Y %H:%M')}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"del_yes_{entry_id}")],
            [InlineKeyboardButton(text="❌ Нет, отменить", callback_data="del_no")],
        ]
    )
    await message.answer(summary, reply_markup=keyboard)


@router.callback_query(F.data.startswith("del_yes_"))
async def confirm_delete(callback, state: FSMContext):
    """Execute soft delete after user confirmation."""

    if not await _ensure_allowed_callback(callback):
        return
    await callback.message.edit_reply_markup(reply_markup=None)

    entry_id = int(callback.data.split("_")[-1])
    service = EntryService()

    async with db_manager.session_factory() as session:
        entry = await service.soft_delete_entry(session, entry_id, user_id=callback.from_user.id)

    if entry:
        await callback.message.answer(
            f"✅ Запись #{entry_id} удалена (soft delete).\n"
            f"Для восстановления: /restore {entry_id}",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await callback.message.answer(f"❌ Запись #{entry_id} не найдена.", reply_markup=main_menu_keyboard())

    await callback.answer()


@router.callback_query(F.data == "del_no")
async def cancel_delete(callback, state: FSMContext):
    """Cancel delete operation."""

    if not await _ensure_allowed_callback(callback):
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Удаление отменено.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.message(Command("restore"))
async def restore_entry_command(message: Message) -> None:
    """Restore a soft-deleted entry: /restore <id>."""

    if not await _ensure_allowed_message(message):
        return

    parts = (message.text or "").strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("❌ Использование: /restore <entry_id>\nНапример: /restore 5")
        return

    entry_id = int(parts[1])
    service = EntryService()

    async with db_manager.session_factory() as session:
        entry = await service.restore_entry(session, entry_id, user_id=message.from_user.id)

    if entry:
        await message.answer(
            f"✅ Запись #{entry_id} восстановлена!\n"
            f"Сумма: {_fmt(entry.amount, entry.currency_code)}\n"
            f"Клиент: {entry.client_name}",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await message.answer(f"❌ Запись #{entry_id} не найдена или уже активна.", reply_markup=main_menu_keyboard())


@router.message(Command("q"))
async def quick_entry_command(message: Message) -> None:
    """Quick entry without AI or wizard: /q <amount> <currency> <in|out> <client> [note...]

    Examples:
      /q 1000 usd in Ali
      /q 500 rub out Karim qarz
      /q 20000 kgs in Manas oylik to'lov
    """

    if not await _ensure_allowed_message(message):
        return

    raw = (message.text or "").strip()
    parts = raw.split(None, 5)  # /q amount currency dir client [note]

    usage = (
        "❌ Формат: /q <сумма> <валюта> <in|out> <клиент> [заметка]\n"
        "Пример: /q 1000 usd in Али\n"
        "       /q 500 rub out Карим за долг"
    )

    if len(parts) < 5:
        await message.answer(usage)
        return

    _, amount_str, currency_raw, direction_raw, client_name = parts[0], parts[1], parts[2], parts[3], parts[4]
    note = parts[5] if len(parts) > 5 else None
    direction_raw = direction_raw.lower()

    # Parse direction
    if direction_raw in {"in", "kirim", "+", "i", "приход"}:
        direction = "INFLOW"
    elif direction_raw in {"out", "chiqim", "-", "o", "расход"}:
        direction = "OUTFLOW"
    else:
        await message.answer(f"❌ Неверное направление: '{direction_raw}'\nИспользуйте: in или out")
        return

    # Parse amount
    try:
        amount = Decimal(amount_str.replace(",", ".").replace(" ", ""))
        if amount <= 0:
            raise ValueError
    except (Exception,):
        await message.answer(f"❌ Неверная сумма: '{amount_str}'")
        return

    # Parse currency
    from app.utils.currency import normalize_currency
    currency = normalize_currency(currency_raw)
    if currency is None:
        await message.answer(f"❌ Неверная валюта: '{currency_raw}'\nРазрешены: USD, RUB, UZS, KGS, EUR")
        return

    try:
        payload = EntryCreate(
            amount=amount,
            currency_code=currency,
            flow_direction=direction,
            client_name=client_name,
            note=note,
        )
    except Exception as exc:
        await message.answer(f"❌ Xato: {exc}")
        return

    user_id = message.from_user.id if message.from_user else 0
    service = EntryService()

    async with db_manager.session_factory() as session:
        entry = await service.create_entry(session, payload, user_id)

    sign = "📥 +" if direction == "INFLOW" else "📤 -"
    note_str = f"\nЗаметка: {note}" if note else ""
    await message.answer(
        f"✅ #{entry.id} сохранена!\n"
        f"{sign} {_fmt(entry.amount, entry.currency_code)} | {entry.client_name}{note_str}",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("edit"))
async def edit_entry_command(message: Message) -> None:
    """Edit a specific field of an existing entry: /edit <id> <field> <value>

    Fields: amount, currency, direction (in/out), client, note
    Examples:
      /edit 5 amount 1500
      /edit 5 currency EUR
      /edit 5 client Nodir
      /edit 5 direction out
      /edit 5 note qarz uchun
    """

    if not await _ensure_allowed_message(message):
        return

    parts = (message.text or "").strip().split(None, 3)
    usage = (
        "❌ Формат: /edit <id> <поле> <новое_значение>\n"
        "Поля: amount, currency, direction, client, note\n"
        "Пример: /edit 5 amount 1500\n"
        "       /edit 5 client Нодир"
    )

    if len(parts) < 4:
        await message.answer(usage)
        return

    _, entry_id_str, field, new_value = parts

    if not entry_id_str.isdigit():
        await message.answer("❌ ID записи должен быть числом.")
        return

    entry_id = int(entry_id_str)
    field = field.lower().strip()

    allowed_fields = {"amount", "currency", "direction", "client", "note"}
    if field not in allowed_fields:
        await message.answer(f"❌ Неверное поле: '{field}'\nРазрешены: {', '.join(sorted(allowed_fields))}")
        return

    service = EntryService()

    async with db_manager.session_factory() as session:
        entry = await service.get_entry_by_id(session, entry_id)

    if entry is None:
        await message.answer(f"❌ Запись #{entry_id} не найдена.")
        return

    # Build updated payload
    try:
        new_amount = Decimal(str(entry.amount))
        new_currency = entry.currency_code
        new_direction = entry.flow_direction
        new_client = entry.client_name
        new_note = entry.note

        if field == "amount":
            new_amount = Decimal(new_value.replace(",", "."))
        elif field == "currency":
            new_currency = new_value.upper().strip()
        elif field == "direction":
            mapping = {"in": "INFLOW", "kirim": "INFLOW", "+": "INFLOW",
                       "out": "OUTFLOW", "chiqim": "OUTFLOW", "-": "OUTFLOW"}
            new_direction = mapping.get(new_value.lower(), new_value.upper())
        elif field == "client":
            new_client = new_value.strip()
        elif field == "note":
            new_note = new_value.strip() or None

        updated_payload = EntryCreate(
            amount=new_amount,
            currency_code=new_currency,
            flow_direction=new_direction,
            client_name=new_client,
            note=new_note,
        )
    except Exception as exc:
        await message.answer(f"❌ Новое значение неверно: {exc}")
        return

    # Soft delete old, create new
    user_id = message.from_user.id if message.from_user else 0

    async with db_manager.session_factory() as session:
        await service.soft_delete_entry(session, entry_id, user_id=user_id)
        new_entry = await service.create_entry(session, updated_payload, user_id)

    sign = "📥 +" if new_entry.flow_direction == "INFLOW" else "📤 -"
    await message.answer(
        f"✅ Запись #{entry_id} обновлена → #{new_entry.id}\n"
        f"{sign} {_fmt(new_entry.amount, new_entry.currency_code)} | {new_entry.client_name}\n"
        f"(Старая #{entry_id} заархивирована)",
        reply_markup=main_menu_keyboard(),
    )


