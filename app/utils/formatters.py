from typing import Union
from decimal import Decimal


def format_currency(amount: Union[float, Decimal, str], currency: str) -> str:
    """Format amount with thousand separators (dot) and localized currency name."""

    # Localize currency names
    currency_map = {
        "UZS": "so'm",
        "KGS": "som",
        "RUB": "rubl",
        "USD": "dollar"
    }
    currency_name = currency_map.get(str(currency).upper(), str(currency))

    try:
        val = float(amount)
    except (ValueError, TypeError):
        val = 0.0

    # Format 1234567.89 -> "1,234,567.89"
    s = f"{val:,.2f}"

    # Remove .00 if present
    if s.endswith(".00"):
        s = s[:-3]

    # Swap comma/dot: "10,000" -> "10 000" then "10.000"
    # User requested dot as thousand separator: 10.000
    
    # Re-implement using split to be precise
    parts = f"{val:,.2f}".split(".")
    integer_part = parts[0].replace(",", ".")
    decimal_part = parts[1]

    if decimal_part == "00":
        formatted_num = integer_part
    else:
        formatted_num = f"{integer_part},{decimal_part}"  # 10.000,50 (comma as decimal sep)

    return f"{formatted_num} {currency_name}"
