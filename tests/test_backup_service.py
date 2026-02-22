from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.schemas.entry import EntryCreate
from app.services.backup_service import BackupService
from app.services.entry_service import EntryService


@pytest.mark.asyncio
async def test_backup_creates_csv_and_sends_to_telegram(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    settings.backups_dir = str(tmp_path / "backups")
    backup_service = BackupService(settings)
    entry_service = EntryService()

    async with session_factory() as session:
        await entry_service.create_entry(
            session=session,
            payload=EntryCreate(
                amount=Decimal("123"),
                currency_code="USD",
                flow_direction="INFLOW",
                client_name="BackupClient",
                note="backup test",
            ),
            created_by_telegram_id=1001,
        )
        result = await backup_service.export_daily_csv(session, date.today())

    assert result.entries_csv.exists()
    assert result.reports_csv.exists()
    assert result.entries_csv.read_text(encoding="utf-8").startswith("id,amount,currency_code")
    assert "daily_profit" in result.reports_csv.read_text(encoding="utf-8")

    calls: list[str] = []

    async def fake_post(self, url, data=None, files=None):  # noqa: ANN001
        calls.append(url)
        return httpx.Response(status_code=200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    await backup_service.send_backup_to_telegram(result)
    assert len(calls) == 2
