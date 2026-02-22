"""Stress test: 20+ realistic transaction messages through AI Chat parser."""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Optional

from app.ai.chat_service import AIChatService
from app.ai.context_builder import ChatContextBuilder
from app.config import get_settings
from app.database.session import db_manager


@dataclass
class TestCase:
    """One test scenario."""
    msg: str  # user message
    expected_action: str  # text / create_entry / delete_entry
    expected_direction: Optional[str] = None  # INFLOW / OUTFLOW
    expected_currency: Optional[str] = None
    expected_amount: Optional[float] = None
    expected_client: Optional[str] = None
    description: str = ""


@dataclass
class TestResult:
    """Result of one test."""
    test: TestCase
    actual: dict
    passed: bool
    error: str = ""
    latency_ms: float = 0


# ──────────── 25 TEST CASES ────────────
TESTS = [
    # ── INFLOW (pul keldi) ──
    TestCase("Ali 1000 dollar berdi", "create_entry", "INFLOW", "USD", 1000, "Ali", "Simple inflow USD"),
    TestCase("Bekdan 5000 som oldim", "create_entry", "INFLOW", "UZS", 5000, "Bek", "Inflow UZS with -dan suffix"),
    TestCase("Rustam 500 evro berdi", "create_entry", "INFLOW", "EUR", 500, "Rustam", "Inflow EUR using 'evro'"),
    TestCase("Isa 3000 rubl berdi", "create_entry", "INFLOW", "RUB", 3000, "Isa", "Inflow RUB using 'rubl'"),
    TestCase("Aziz 20000 som kirim", "create_entry", "INFLOW", "KGS", 20000, "Aziz", "Inflow KGS using 'som kirim'"),
    TestCase("Erkin 100 usd sotdi", "create_entry", "INFLOW", "USD", 100, "Erkin", "Inflow - 'sotdi' = client sold to us"),
    TestCase("Jahondan 2000 kgs oldik", "create_entry", "INFLOW", "KGS", 2000, "Jahon", "Inflow KGS with 'oldik'"),

    # ── OUTFLOW (pul ketdi) ──
    TestCase("Karimga 500 dollar berdim", "create_entry", "OUTFLOW", "USD", 500, "Karim", "Outflow with -ga suffix"),
    TestCase("Nodir 200 evro oldi", "create_entry", "OUTFLOW", "EUR", 200, "Nodir", "Outflow EUR - 'oldi' = client took"),
    TestCase("Sanjardan 10000 rub chiqim", "create_entry", "OUTFLOW", "RUB", 10000, "Sanjar", "Outflow RUB explicit 'chiqim'"),
    TestCase("Timurga 800 usd berdik", "create_entry", "OUTFLOW", "USD", 800, "Timur", "Outflow with 'berdik'"),
    TestCase("Farhod 50000 kgs oldi", "create_entry", "OUTFLOW", "KGS", 50000, "Farhod", "Outflow KGS - client took"),

    # ── WITH NOTES ──
    TestCase("Oybek 300 usd berdi, avans uchun", "create_entry", "INFLOW", "USD", 300, "Oybek", "Inflow with note"),
    TestCase("Sherzodga 1500 rub berdim qarz hisobiga", "create_entry", "OUTFLOW", "RUB", 1500, "Sherzod", "Outflow with note"),

    # ── SLANG / SHORT / TYPOS ── 
    TestCase("ali 2k usd berd", "create_entry", "INFLOW", "USD", 2000, "Ali", "Slang '2k' and truncated 'berd'"),
    TestCase("bob 100$ kirim", "create_entry", "INFLOW", "USD", 100, "Bob", "Dollar sign instead of 'usd'"),
    TestCase("vali 50 eur chiqim", "create_entry", "OUTFLOW", "EUR", 50, "Vali", "Short direct outflow"),

    # ── QUESTIONS (should return text) ──
    TestCase("balansni ko'rsat", "text", description="Balance query"),
    TestCase("bugungi operatsiyalar", "text", description="Today's operations query"),
    TestCase("qancha pul bor kassada", "text", description="Cash question"),
    TestCase("mijozlar ro'yxati", "text", description="Client list query"),

    # ── DELETE ──
    TestCase("#1 ni o'chir", "delete_entry", description="Delete by ID"),
    TestCase("entry 2 delete qil", "delete_entry", description="Delete with English-Uzbek mix"),

    # ── AMBIGUOUS ──
    TestCase("Anvar 1000", "create_entry", description="Ambiguous: no currency or direction"),
    TestCase("salom", "text", description="Greeting, should not create entry"),
]


async def run_tests():
    settings = get_settings()
    chat_service = AIChatService.from_settings(settings)
    if chat_service is None:
        print("ERROR: AI chat service not configured")
        return

    await db_manager.connect()

    async with db_manager.session_factory() as session:
        builder = ChatContextBuilder(base_currency_code=settings.base_currency_code)
        context = await builder.build(session)

    results: list[TestResult] = []
    passed = 0
    failed = 0

    print(f"{'='*80}")
    print(f"AI CHAT STRESS TEST — {len(TESTS)} test cases")
    print(f"Provider: {settings.ai_provider}")
    print(f"{'='*80}\n")

    for i, test in enumerate(TESTS, 1):
        start = time.time()
        try:
            result = await chat_service.answer(question=test.msg, context=context)
            latency = (time.time() - start) * 1000
        except Exception as e:
            latency = (time.time() - start) * 1000
            result = {"action": "error", "data": {"message": str(e)}}

        actual_action = result.get("action", "unknown")
        data = result.get("data", {})

        # Evaluate
        errors = []
        if actual_action != test.expected_action:
            errors.append(f"action: got '{actual_action}' expected '{test.expected_action}'")

        if test.expected_action == "create_entry" and actual_action == "create_entry":
            if test.expected_direction and data.get("flow_direction") != test.expected_direction:
                errors.append(f"direction: got '{data.get('flow_direction')}' expected '{test.expected_direction}'")
            if test.expected_currency and data.get("currency_code") != test.expected_currency:
                errors.append(f"currency: got '{data.get('currency_code')}' expected '{test.expected_currency}'")
            if test.expected_amount and float(data.get("amount", 0)) != test.expected_amount:
                errors.append(f"amount: got {data.get('amount')} expected {test.expected_amount}")
            if test.expected_client:
                actual_client = str(data.get("client_name", "")).lower()
                if test.expected_client.lower() not in actual_client:
                    errors.append(f"client: got '{data.get('client_name')}' expected '{test.expected_client}'")

        is_pass = len(errors) == 0
        if is_pass:
            passed += 1
        else:
            failed += 1

        status = "✅ PASS" if is_pass else "❌ FAIL"
        print(f"#{i:02d} {status} [{latency:.0f}ms] {test.description or test.msg}")
        if actual_action == "create_entry":
            d = "+" if data.get("flow_direction") == "INFLOW" else "-"
            print(f"     → {d} {data.get('amount')} {data.get('currency_code')} | {data.get('client_name')} | note: {data.get('note', '-')}")
        elif actual_action == "delete_entry":
            print(f"     → delete entry #{data.get('entry_id')}")
        elif actual_action == "text":
            msg = str(data.get("message", ""))[:80]
            print(f"     → text: {msg}...")
        elif actual_action == "error":
            print(f"     → ERROR: {data.get('message', '')[:80]}")

        if errors:
            for e in errors:
                print(f"     ⚠️  {e}")

        results.append(TestResult(test=test, actual=result, passed=is_pass, error="; ".join(errors), latency_ms=latency))

        # Small delay to avoid rate limits
        await asyncio.sleep(0.5)

    # Summary
    total = len(results)
    avg_latency = sum(r.latency_ms for r in results) / total
    score = round((passed / total) * 10, 1)

    print(f"\n{'='*80}")
    print(f"RESULTS: {passed}/{total} passed | {failed} failed")
    print(f"Average latency: {avg_latency:.0f}ms")
    print(f"SCORE: {score}/10")
    print(f"{'='*80}")

    # Failed details
    if failed > 0:
        print(f"\nFAILED TESTS:")
        for r in results:
            if not r.passed:
                print(f"  - '{r.test.msg}' → {r.error}")

    await db_manager.dispose()


if __name__ == "__main__":
    asyncio.run(run_tests())
