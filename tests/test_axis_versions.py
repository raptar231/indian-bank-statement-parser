# Copyright 2024-{{year}} Koushik Mondal (github.com/raptar231)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

raptar231)/komo0225)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import date
from decimal import Decimal
from pathlib import Path

from bank_parser.banks.axis import AxisCreditCardParser, AxisParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "axis"


def _load(name: str) -> tuple[str, list[str]]:
    text = (FIXTURES_DIR / name).read_text(encoding="utf-8")
    return text, text.split("=== PAGE ===")


def _txns(parser: AxisParser, name: str):
    _, pages = _load(name)
    return parser._parse_transactions(pages)


# ---------------------------------------------------------------------------
# Savings account layout
# ---------------------------------------------------------------------------


def test_savings_2026_transactions():
    txns = _txns(AxisParser(""), "axis_savings-jun-2026.txt")
    assert len(txns) == 12

    assert txns[0].date == date(2026, 4, 2)
    assert txns[0].description == "UPI/P2A/626181509069/TARAPADA /UTIB/Payment/"
    assert txns[0].credit == Decimal("20000.00")
    assert txns[0].debit is None
    assert txns[0].balance == Decimal("29249.73")
    assert txns[0].ref_no == "626181509069"
    assert txns[0].category == "credit"

    assert txns[1].debit == Decimal("1600.00")
    assert txns[1].balance == Decimal("27649.73")

    assert txns[4].description == "CreditCard Payment XX 1184 Ref#O2S96OJ4SZUMI8"
    assert txns[4].debit == Decimal("162.00")
    assert txns[4].ref_no == "O2S96OJ4SZUMI8"

    # Narration continues on the following line.
    assert txns[5].description == (
        "UPI/P2A/609470215741/MADHUMITA MISHRA SIN/UPI/State Bank Of India"
    )
    assert txns[5].debit == Decimal("20000.00")
    assert txns[5].ref_no == "609470215741"

    assert txns[7].credit == Decimal("500.00")
    assert txns[7].ref_no == "534132328296"

    assert txns[10].credit == Decimal("50567.00")
    assert txns[10].balance == Decimal("56537.85")
    assert "SALARY MAY 2026" in txns[10].description
    assert txns[10].ref_no == "50200007377194"

    assert txns[11].date == date(2026, 4, 20)
    assert txns[11].debit == Decimal("300.90")
    assert txns[11].balance == Decimal("56236.95")
    assert txns[11].ref_no == "609784280155"


def test_classify_amount_prefers_balance_trend_over_keywords():
    """Regression: narration leaked from the next row (``BRN-SALARY ...``) or
    footer text containing credit keywords (``SALARY``, ``fixed deposit``) must
    not flip a transaction whose balance clearly moved down/up."""
    parser = AxisParser("")
    debit, credit = parser._classify_amount(
        Decimal("40183.06"),
        Decimal("20000.00"),
        Decimal("20183.06"),
        "BANK/Medical BRN-SALARY PAYMENT-TWDS MAY2021",
    )
    assert debit == Decimal("20000.00")
    assert credit is None

    debit, credit = parser._classify_amount(
        Decimal("126300.06"),
        Decimal("693732.94"),
        Decimal("820032.94"),
        "Mon/STATE B/Savings fixed deposit matured",
    )
    assert debit is None
    assert credit == Decimal("693732.94")


def test_legacy_layout_not_absorbed_by_total_row():
    """Regression: older Axis layouts have no ``##`` markers, so the ``TOTAL``
    row, ``CLOSING BALANCE`` and footer must still terminate the transaction
    section. Otherwise the last block absorbs them, reads its amount/balance
    off the TOTAL row, and the footer text (``fixed deposit``) flips the
    fallback classifier to mark a NEFT debit as a credit."""
    txns = _txns(AxisParser(""), "axis_savings-legacy.txt")
    assert len(txns) == 3

    last = txns[-1]
    assert last.date == date(2024, 1, 10)
    assert last.description == "MON/STATE B/SAVINGS"
    assert last.debit == Decimal("104000.00")
    assert last.credit is None
    assert last.balance == Decimal("24000.00")
    assert last.category == "debit"

    assert not any(t.credit == Decimal("106000.00") for t in txns)
    assert not any("TOTAL" in t.description for t in txns)
    assert not any("CLOSING" in t.description for t in txns)


def test_legacy_layout_metadata():
    text, _ = _load("axis_savings-legacy.txt")
    parser = AxisParser("")
    assert parser._extract_account_number(text) == "999999999999999"
    assert parser._extract_account_type(text) == "Savings"
    assert parser._extract_period(text) == (date(2024, 1, 1), date(2024, 1, 31))
    assert parser._extract_balances(text) == (Decimal("100000.00"), Decimal("24000.00"))


def test_legacy_layout_balance_validation_ok():
    text, pages = _load("axis_savings-legacy.txt")
    parser = AxisParser("")
    stmt = parser._parse_statement(pages, text)
    result = stmt.validate_balances()
    assert result.status == "ok"
    assert result.ok is True
    assert result.difference == Decimal("0")


def test_parsed_statement_balance_validation_ok():
    """End-to-end: a fully parsed statement reconciles opening -> closing."""
    text, pages = _load("axis_savings-jun-2026.txt")
    parser = AxisParser("")
    stmt = parser._parse_statement(pages, text)
    result = stmt.validate_balances()
    assert result.status == "ok"
    assert result.ok is True
    assert result.difference == Decimal("0")


def test_savings_2026_metadata():
    text, _ = _load("axis_savings-jun-2026.txt")
    parser = AxisParser("")
    assert parser._extract_account_number(text) == "919010041000296"
    assert parser._extract_account_type(text) == "Savings"
    assert parser._extract_period(text) == (date(2026, 4, 2), date(2026, 7, 2))
    assert parser._extract_balances(text) == (Decimal("9249.73"), Decimal("56236.95"))


# ---------------------------------------------------------------------------
# Credit card layout
# ---------------------------------------------------------------------------


def test_credit_card_2025_transactions():
    txns = _txns(AxisCreditCardParser(""), "axis_credit-sep-2025.txt")
    assert len(txns) == 8

    assert txns[0].date == date(2025, 9, 12)
    assert txns[0].description == "BALANCE CONVERSION INTO EMI"
    assert txns[0].credit == Decimal("214757.47")
    assert txns[0].debit is None
    assert txns[0].balance == Decimal("0")
    assert txns[0].ref_no is None
    assert txns[0].category == "credit"

    assert txns[1].description == "EMI PROCESSING FEE, REF# 62879041"
    assert txns[1].debit == Decimal("4695.15")
    assert txns[1].ref_no == "62879041"

    assert txns[2].description == "GST"
    assert txns[2].debit == Decimal("845.13")

    assert txns[4].description == "BLINKIT COMMERCE PVT LTD"
    assert txns[4].debit == Decimal("216.00")

    bbps = next(t for t in txns if t.category == "credit" and t.ref_no is not None)
    assert bbps.description == "BBPS PAYMENT RECEIVED - DP015260124108QGW66E"
    assert bbps.credit == Decimal("14816.00")
    assert bbps.ref_no == "DP015260124108QGW66E"

    assert txns[7].description == "GST"
    assert txns[7].debit == Decimal("2009.03")


def test_credit_card_2025_metadata():
    text, _ = _load("axis_credit-sep-2025.txt")
    parser = AxisCreditCardParser("")
    statement = parser._parse_statement(text.split("=== PAGE ==="), text)
    assert statement.account_number == "552137******8132"
    assert statement.account_type == "Credit Card"
    assert statement.statement_period_start == date(2025, 8, 23)
    assert statement.statement_period_end == date(2025, 9, 21)
    assert statement.opening_balance is None
    assert statement.closing_balance is None


# ---------------------------------------------------------------------------
# Auto-detection
# ---------------------------------------------------------------------------


def test_axis_parser_detects_credit_card_text():
    text, _ = _load("axis_credit-sep-2025.txt")
    assert AxisParser("")._looks_like_credit_card(text) is True


def test_axis_parser_does_not_detect_savings_as_credit_card():
    text, _ = _load("axis_savings-jun-2026.txt")
    assert AxisParser("")._looks_like_credit_card(text) is False
