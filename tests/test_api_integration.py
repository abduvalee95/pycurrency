from __future__ import annotations

from datetime import date

import pytest


@pytest.mark.asyncio
async def test_post_entries_then_list_and_reports(api_client, allowed_headers: dict[str, str]) -> None:
    payload_1 = {
        "amount": "100",
        "currency_code": "USD",
        "flow_direction": "INFLOW",
        "client_name": "Ali",
        "note": "manual",
    }
    payload_2 = {
        "amount": "50",
        "currency_code": "USD",
        "flow_direction": "OUTFLOW",
        "client_name": "Ali",
        "note": None,
    }

    r1 = await api_client.post("/api/v1/entries", headers=allowed_headers, json=payload_1)
    r2 = await api_client.post("/api/v1/entries", headers=allowed_headers, json=payload_2)
    assert r1.status_code == 200
    assert r2.status_code == 200

    entries = await api_client.get("/api/v1/entries", headers=allowed_headers)
    assert entries.status_code == 200
    entries_json = entries.json()
    assert entries_json["total"] == 2

    daily = await api_client.get(f"/api/v1/reports/daily-profit?date={date.today().isoformat()}", headers=allowed_headers)
    balances = await api_client.get("/api/v1/reports/currency-balances", headers=allowed_headers)
    debts = await api_client.get("/api/v1/reports/client-debts", headers=allowed_headers)
    cash_total = await api_client.get("/api/v1/reports/cash-total", headers=allowed_headers)

    assert daily.status_code == 200
    assert balances.status_code == 200
    assert debts.status_code == 200
    assert cash_total.status_code == 200
    assert daily.json()["by_currency"]["USD"] == "50.00000000"


@pytest.mark.asyncio
async def test_ai_parse_then_confirm_create_entry(api_client, allowed_headers: dict[str, str]) -> None:
    parse_response = await api_client.post(
        "/api/v1/ai/parse",
        headers=allowed_headers,
        json={"text": "Rustamga 200 rub sotdim"},
    )
    assert parse_response.status_code == 200
    parsed = parse_response.json()
    assert parsed["currency_code"] == "RUB"
    assert parsed["flow_direction"] == "OUTFLOW"

    create_response = await api_client.post(
        "/api/v1/entries",
        headers=allowed_headers,
        json={
            "amount": parsed["amount"],
            "currency_code": parsed["currency_code"],
            "flow_direction": parsed["flow_direction"],
            "client_name": parsed["client_name"] or "Rustam",
            "note": parsed.get("note"),
        },
    )
    assert create_response.status_code == 200
    body = create_response.json()
    assert body["currency_code"] == "RUB"
    assert body["flow_direction"] == "OUTFLOW"


@pytest.mark.asyncio
async def test_unauthorized_telegram_id_returns_403(api_client, denied_headers: dict[str, str]) -> None:
    response = await api_client.get("/api/v1/entries", headers=denied_headers)
    assert response.status_code == 403
