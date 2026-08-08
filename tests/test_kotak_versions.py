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

from bank_parser.banks.kotak import KotakParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "kotak"


def _load(name: str) -> tuple[str, list[str]]:
    text = (FIXTURES_DIR / name).read_text(encoding="utf-8")
    return text, text.split("=== PAGE ===")


def _txns(parser: KotakParser, name: str):
    text, pages = _load(name)
    opening = parser._extract_balances(text)[0]
    return parser._parse_transactions(pages, opening)


def test_savings_2025_transactions():
    txns = _txns(KotakParser(""), "kotak_savings-jul-2025.txt")
    assert len(txns) == 10

    assert txns[0].date == date(2025, 7, 1)
    assert txns[0].description == (
        "UPI/DR/426784531012/ZOMATO PAYMENTS/ZOMATO@ICICI/FOOD ORDER 01JUL"
    )
    assert txns[0].debit == Decimal("347.00")
    assert txns[0].credit is None
    assert txns[0].balance == Decimal("9653.00")
    assert txns[0].ref_no == "426784531012"
    assert txns[0].category == "debit"

    assert txns[1].description == "NEFT/INWARD/CR-HDFC/INFOSYS BPO LTD/SAL JUL25/N042718362538143"
    assert txns[1].credit == Decimal("35000.00")
    assert txns[1].ref_no == "N042718362538143"
    assert txns[1].category == "credit"

    assert txns[2].credit == Decimal("2000.00")
    assert txns[2].ref_no == "789012345678"

    assert txns[3].description == "ATM-WDL 987654 SWIGGY RESTAURANT PAYMENT"
    assert txns[3].debit == Decimal("1250.00")
    assert txns[3].ref_no is None

    assert txns[4].debit == Decimal("4500.00")
    assert txns[4].ref_no == "B042718367821034"

    # Narration continues on the following line.
    assert txns[6].description == ("NEFT/INWARD/CR-ICICI/INTEREST CREDIT SB-A/1234567890/INT JUL25")
    assert txns[6].credit == Decimal("125.00")
    assert txns[6].balance == Decimal("40461.00")
    assert txns[6].category == "credit"

    assert txns[9].date == date(2025, 7, 31)
    assert txns[9].debit == Decimal("205.00")
    assert txns[9].balance == Decimal("55056.00")
    assert txns[9].ref_no == "987654321012"


def test_savings_2025_metadata():
    text, _ = _load("kotak_savings-jul-2025.txt")
    parser = KotakParser("")
    assert parser._extract_account_number(text) == "10115678912"
    assert parser._extract_account_type(text) == "Savings"
    assert parser._extract_period(text) == (date(2025, 7, 1), date(2025, 7, 31))
    assert parser._extract_balances(text) == (Decimal("10000.00"), Decimal("55056.00"))


def test_savings_2025_statement():
    text, pages = _load("kotak_savings-jul-2025.txt")
    statement = KotakParser("")._parse_statement(pages, text)
    assert statement.account_number == "10115678912"
    assert statement.account_type == "Savings"
    assert statement.statement_period_start == date(2025, 7, 1)
    assert statement.statement_period_end == date(2025, 7, 31)
    assert statement.opening_balance == Decimal("10000.00")
    assert statement.closing_balance == Decimal("55056.00")
    assert len(statement.transactions) == 10
