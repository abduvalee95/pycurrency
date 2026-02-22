"""Currency code normalization with Cyrillic aliases and typo tolerance."""

from typing import Optional

# Exact and fuzzy aliases → standard ISO code
_CURRENCY_ALIASES: dict[str, str] = {
    # USD
    "usd": "USD", "dollar": "USD", "dollars": "USD", "дол": "USD", "доллар": "USD",
    "долл": "USD", "доллары": "USD", "$": "USD",
    # Typos
    "dolalr": "USD", "dollor": "USD", "dolr": "USD", "dolsr": "USD", "dolar": "USD",
    "doll": "USD", "uusd": "USD", "uds": "USD", "dkk": "USD",

    # RUB
    "rub": "RUB", "rubl": "RUB", "rubel": "RUB", "ruble": "RUB",
    "руб": "RUB", "рубл": "RUB", "рубль": "RUB", "рубли": "RUB", "₽": "RUB",
    # Typos
    "rubll": "RUB", "rbl": "RUB", "rrub": "RUB",

    # KGS
    "kgs": "KGS", "som": "KGS", "сом": "KGS", "сомов": "KGS", "сома": "KGS",
    # Typos
    "kgss": "KGS", "ksg": "KGS", "soom": "KGS",

    # UZS
    "uzs": "UZS", "so'm": "UZS", "sum": "UZS", "сум": "UZS", "сўм": "UZS",
    # Typos
    "uzss": "UZS", "usz": "UZS",

    # EUR
    "eur": "EUR", "euro": "EUR", "evro": "EUR", "евро": "EUR", "€": "EUR",
    # Typos
    "evra": "EUR", "evrp": "EUR", "ero": "EUR", "eurr": "EUR", "euur": "EUR",
}

VALID_CURRENCIES = {"USD", "RUB", "UZS", "KGS", "EUR"}


def normalize_currency(raw: str) -> Optional[str]:
    """Normalize a currency string to standard ISO code.

    Handles Cyrillic, common typos, and aliases.
    Returns None if no match found.
    """
    cleaned = raw.strip().lower()
    # Direct alias match
    if cleaned in _CURRENCY_ALIASES:
        return _CURRENCY_ALIASES[cleaned]
    # Already a valid code (case-insensitive)
    upper = cleaned.upper()
    if upper in VALID_CURRENCIES:
        return upper
    return None
