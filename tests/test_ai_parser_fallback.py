from __future__ import annotations

from app.ai.fallback_parser import RuleBasedAIParser


def test_fallback_parser_maps_to_inflow_outflow_and_plain_rate_note() -> None:
    parser = RuleBasedAIParser()

    buy = parser.parse("Ali 1000 usd 8900 dan oldim")
    sell = parser.parse("Rustamga 500 usd 9050 dan sotdim")

    assert buy["flow_direction"] == "INFLOW"
    assert buy["note"] == "rate: 8900"
    assert sell["flow_direction"] == "OUTFLOW"
    assert sell["note"] == "rate: 9050"
