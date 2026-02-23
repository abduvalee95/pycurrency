"""Prompt builder for natural-language cash entry parsing."""


def build_transaction_parse_prompt() -> str:
    """Return strict instructions to parse text into cash entry JSON."""

    return (
        "You are a parser for exchange operator messages. "
        "Return ONLY valid JSON with keys: amount, currency_code, flow_direction, client_name, note. "
        "amount must be numeric and > 0. "
        "currency_code must be one of USD, RUB, UZS, KGS, EUR. "
        "flow_direction must be INFLOW or OUTFLOW. "
        "Treat verbs: 'oldim', 'oldi', 'sotib oldim', 'buy', 'kirdi', 'kirim', 'inflow', 'berdi' as INFLOW; "
        "'sotdim', 'prodal', 'sell', 'berdim', 'chiqim', 'chiqdi', 'outflow' as OUTFLOW. "
        "client_name can be null if not present. Extract raw names without suffixes (e.g. 'aliakaga' -> 'aliaka'). "
        "note can be null. If user mentions rate (e.g. 12100), place it in note as 'rate: 12100'. "
        "If there is a punctuation mark like '.' or ',' or ':', EVERYTHING after it MUST be captured as the 'note'. "
        "Do not include markdown or explanations. "
        "Interpret 'oldim/sotib oldim/kupил' as INFLOW and 'sotdim/prodal' as OUTFLOW. "
        "Example: 'Ali 1000 usd 12100 rate oldim' => "
        "{\"amount\":1000,\"currency_code\":\"USD\",\"flow_direction\":\"INFLOW\",\"client_name\":\"Ali\",\"note\":\"rate: 12100\"}."
    )
