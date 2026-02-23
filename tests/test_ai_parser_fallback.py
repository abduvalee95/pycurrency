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


def test_fallback_parser_expanded_flow_dictionary() -> None:
    parser = RuleBasedAIParser()

    assert parser.parse("Azizga 200 usd berdim")["flow_direction"] == "OUTFLOW"
    assert parser.parse("Sardor 300 usd chiqdi")["flow_direction"] == "OUTFLOW"
    assert parser.parse("Mik 400 usd kirdi")["flow_direction"] == "INFLOW"
    assert parser.parse("Ali 500 usd oldi")["flow_direction"] == "INFLOW"
