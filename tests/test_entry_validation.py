from __future__ import annotations

from pydantic import ValidationError
import pytest

from app.schemas.entry import EntryCreate


def test_entry_create_valid_payload() -> None:
    entry = EntryCreate(
        amount="100.50",
        currency_code="usd",
        flow_direction="inflow",
        client_name=" Ali ",
        note=" test ",
    )
    assert str(entry.amount) == "100.50"
    assert entry.currency_code == "USD"
    assert entry.flow_direction == "INFLOW"
    assert entry.client_name == "Ali"
    assert entry.note == " test "


@pytest.mark.parametrize(
    "payload",
    [
        {"amount": "0", "currency_code": "USD", "flow_direction": "INFLOW", "client_name": "Ali"},
        {"amount": "-1", "currency_code": "USD", "flow_direction": "INFLOW", "client_name": "Ali"},
        {"amount": "10", "currency_code": "EUR", "flow_direction": "INFLOW", "client_name": "Ali"},
        {"amount": "10", "currency_code": "USD", "flow_direction": "BUY", "client_name": "Ali"},
        {"amount": "10", "currency_code": "USD", "flow_direction": "INFLOW", "client_name": " "},
    ],
)
def test_entry_create_invalid_payload(payload: dict) -> None:
    with pytest.raises(ValidationError):
        EntryCreate(**payload)
