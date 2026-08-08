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

from bank_parser.banks.icici import ICICICreditCardParser, ICICIParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "icici"


def _load(name: str) -> tuple[str, list[str]]:
    text = (FIXTURES_DIR / name).read_text(encoding="utf-8")
    return text, text.split("=== PAGE ===")


def _txns(parser: ICICIParser, name: str):
    _, pages = _load(name)
    return parser._parse_transactions(pages)


# ---------------------------------------------------------------------------
# Legacy (pre-2020) savings layout
# ---------------------------------------------------------------------------


def test_savings_legacy_2019_transactions():
    txns = _txns(ICICIParser(""), "icici_savings-apr-2019.txt")
    assert len(txns) == 16

    assert txns[0].date == date(2019, 4, 2)
    assert txns[0].description == "UPI/909144468033/NA/8008998080@payt/State Bank Of India"
    assert txns[0].debit == Decimal("100.00")
    assert txns[0].credit is None
    assert txns[0].balance == Decimal("204659.22")
    assert txns[0].ref_no == "909144468033"
    assert txns[0].category == "debit"

    assert txns[1].description == "ICICI DIRECT EBA/NSEMRGNPIPO/20190401223241"
    assert txns[1].credit == Decimal("38320.00")
    assert txns[1].balance == Decimal("242979.22")
    assert txns[1].ref_no == "20190401223241"
    assert txns[1].category == "credit"

    assert txns[3].description == "BIL/ONL/001676539074/IRCTC/ChgRs10 GSTRs1.80/10000"
    assert txns[3].debit == Decimal("1722.29")
    assert txns[3].ref_no == "001676539074"

    assert txns[7].description == "MOBILE BANKING MMT/IMPS/909335029016/venkatesh/Paytm Payments"
    assert txns[7].debit == Decimal("1.00")
    assert txns[7].ref_no == "909335029016"

    assert txns[10].description == "BIL/INFT/001681146371/NA/Niranjan S/ICICI BANK"
    assert txns[10].credit == Decimal("1105.00")
    assert txns[10].ref_no == "001681146371"

    assert txns[11].description == (
        "MOBILE BANKING MMT/IMPS/909715291625/April Rent/Puja Dadwa/SBIN000084"
    )
    assert txns[11].debit == Decimal("16000.00")
    assert txns[11].ref_no == "909715291625"

    assert txns[12].description == "NEFT-N108190804966636-BHARTI INFRATEL LTD-53110304"
    assert txns[12].credit == Decimal("19432.59")
    assert txns[12].balance == Decimal("72648.77")
    assert txns[12].ref_no == "N108190804966636"

    assert txns[15].date == date(2019, 4, 30)
    assert txns[15].description == "UPI/912046941209/Oid8115742852@paytm Payments"
    assert txns[15].debit == Decimal("399.00")
    assert txns[15].balance == Decimal("69503.77")
    assert txns[15].ref_no == "912046941209"


def test_savings_legacy_2019_metadata():
    text, _ = _load("icici_savings-apr-2019.txt")
    parser = ICICIParser("")
    assert parser._extract_account_number(text) == "XXXXXXXX3090"
    assert parser._extract_account_type(text) == "Savings"
    assert parser._extract_period(text) == (date(2019, 4, 1), date(2019, 4, 30))
    assert parser._extract_balances(text) == (Decimal("204759.22"), Decimal("69503.77"))


# ---------------------------------------------------------------------------
# Modern (2026) savings layout
# ---------------------------------------------------------------------------


def test_savings_modern_2026_transactions():
    txns = _txns(ICICIParser(""), "icici_savings-modern-jun-2026.txt")
    assert len(txns) == 12

    assert txns[0].date == date(2026, 4, 2)
    assert txns[0].description == (
        "BIL/NUCL/001182507869/Recharge/NUCLEI service KANNAN Bil Payment"
    )
    assert txns[0].debit == Decimal("199.00")
    assert txns[0].balance == Decimal("40718.24")
    assert txns[0].ref_no == "001182507869"

    assert txns[3].credit == Decimal("499.20")
    assert txns[3].balance == Decimal("35967.44")
    assert txns[3].ref_no == "820667900936"

    assert txns[5].description == "NFS/CASH WDL/609519430140/MCRM1774/PARAMAKUD/05-04-26 ATM trxn"
    assert txns[5].debit == Decimal("10000.00")
    assert txns[5].ref_no == "609519430140"

    # Salary credit carries a misleading "Debit trxn" label; sign is decided
    # by the running-balance arithmetic.
    assert txns[7].credit == Decimal("50567.00")
    assert txns[7].balance == Decimal("84534.44")
    assert "SALARY MAY 2026" in txns[7].description
    assert "Debit trxn" in txns[7].description
    assert txns[7].ref_no == "50200007377194"

    # Short UPI VPA ids are not treated as reference numbers.
    assert txns[8].debit == Decimal("1000.00")
    assert txns[8].ref_no is None

    assert txns[11].date == date(2026, 4, 20)
    assert txns[11].debit == Decimal("30350.00")
    assert txns[11].balance == Decimal("50834.44")
    assert txns[11].ref_no == "370339030956"


def test_savings_modern_2026_metadata():
    text, _ = _load("icici_savings-modern-jun-2026.txt")
    parser = ICICIParser("")
    assert parser._extract_account_number(text) == "155401510482"
    assert parser._extract_account_type(text) == "Savings"
    assert parser._extract_period(text) == (date(2026, 4, 1), date(2026, 6, 30))
    assert parser._extract_balances(text) == (None, None)


# ---------------------------------------------------------------------------
# Credit card layout
# ---------------------------------------------------------------------------


def test_credit_card_2024_transactions():
    txns = _txns(ICICICreditCardParser(""), "icici_credit-jun-2024.txt")
    assert len(txns) == 15

    assert txns[0].date == date(2024, 6, 15)
    assert txns[0].description == "Edelweiss Tokio Life Insu Mumbai IN"
    assert txns[0].debit == Decimal("6941.00")
    assert txns[0].credit is None
    assert txns[0].balance == Decimal("0")
    assert txns[0].ref_no == "9360859921"
    assert txns[0].category == "debit"

    # A 0.00 informational row is skipped, and the refund + card payment are
    # credits via the trailing CR marker.
    assert all((t.debit or Decimal("0")) + (t.credit or Decimal("0")) != 0 for t in txns)

    refund = next(t for t in txns if t.ref_no == "93940541056")
    assert refund.description == "PEPPERFRYCOM MUMBAI IN"
    assert refund.credit == Decimal("25617.63")
    assert refund.category == "credit"

    payment = next(t for t in txns if t.description == "CLICK TO PAY PAYMENT RECEIVED")
    assert payment.credit == Decimal("711250.79")
    assert payment.ref_no == "9457869603"
    assert payment.category == "credit"

    # Reward points between narration and amount must not leak into the amount.
    assert txns[2].debit == Decimal("25617.63")
    assert txns[2].ref_no == "9381139205"

    assert txns[4].description == "Processing Fee 199 : 0%"
    assert txns[4].debit == Decimal("199.00")

    assert txns[9].description == "NALA HOTELS PVT LTD NAMAKKAL IN"
    assert txns[9].debit == Decimal("8515.00")
    assert txns[9].ref_no == "9430389161"


def test_credit_card_2024_metadata():
    text, _ = _load("icici_credit-jun-2024.txt")
    parser = ICICICreditCardParser("")
    statement = parser._parse_statement(text.split("=== PAGE ==="), text)
    assert statement.account_number is None
    assert statement.account_type == "Credit Card"
    assert statement.statement_period_start is None
    assert statement.statement_period_end is None
    assert statement.opening_balance is None
    assert statement.closing_balance is None


# ---------------------------------------------------------------------------
# Auto-detection
# ---------------------------------------------------------------------------


def test_icici_parser_detects_credit_card_text():
    text, _ = _load("icici_credit-jun-2024.txt")
    assert ICICIParser("")._looks_like_credit_card(text) is True


def test_icici_parser_does_not_detect_savings_as_credit_card():
    text, _ = _load("icici_savings-modern-jun-2026.txt")
    assert ICICIParser("")._looks_like_credit_card(text) is False
