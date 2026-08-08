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

from bank_parser.banks.pnb import PNBParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "pnb"


def _load(name: str) -> tuple[str, list[str]]:
    text = (FIXTURES_DIR / name).read_text(encoding="utf-8")
    return text, text.split("=== PAGE ===")


def _txns(parser: PNBParser, name: str):
    text, pages = _load(name)
    opening = parser._extract_balances(text)[0]
    return parser._parse_transactions(pages, opening)


def test_savings_2023_transactions():
    txns = _txns(PNBParser(""), "pnb_savings-may-2023.txt")
    assert len(txns) == 7

    assert txns[0].date == date(2023, 4, 27)
    assert txns[0].description == "ATM WDL 123456 DELHI JUNCTION 27APR"
    assert txns[0].debit == Decimal("25000.00")
    assert txns[0].credit is None
    assert txns[0].balance == Decimal("20000.00")
    assert txns[0].ref_no is None
    assert txns[0].category == "debit"

    assert txns[1].description == "NEFT/INWARD/CR-HDFC/AMIT KUMAR/N042718362538143"
    assert txns[1].credit == Decimal("40000.00")
    assert txns[1].ref_no == "N042718362538143"
    assert txns[1].category == "credit"

    assert txns[2].debit == Decimal("2000.00")
    assert txns[2].ref_no == "426784531012"

    assert txns[3].description == "SALARY CREDIT PNB SALARY APR23"
    assert txns[3].credit == Decimal("59500.00")
    assert txns[3].balance == Decimal("117500.00")

    assert txns[4].description == "CHQ PAID"
    assert txns[4].debit == Decimal("8500.00")
    assert txns[4].ref_no is None

    assert txns[5].credit == Decimal("16200.00")
    assert txns[5].ref_no == "N042718369927155"

    assert txns[6].date == date(2023, 5, 3)
    assert txns[6].debit == Decimal("66700.00")
    assert txns[6].balance == Decimal("58500.00")
    assert txns[6].ref_no == "B042718367821034"
    assert txns[6].category == "debit"


def test_savings_2023_metadata():
    text, _ = _load("pnb_savings-may-2023.txt")
    parser = PNBParser("")
    assert parser._extract_account_number(text) == "4613000100051407"
    assert parser._extract_account_type(text) == "Savings"
    assert parser._extract_period(text) == (date(2023, 4, 27), date(2023, 5, 3))
    assert parser._extract_balances(text) == (Decimal("45000.00"), Decimal("58500.00"))


def test_savings_2023_statement():
    text, pages = _load("pnb_savings-may-2023.txt")
    statement = PNBParser("")._parse_statement(pages, text)
    assert statement.account_number == "4613000100051407"
    assert statement.account_type == "Savings"
    assert statement.statement_period_start == date(2023, 4, 27)
    assert statement.statement_period_end == date(2023, 5, 3)
    assert statement.opening_balance == Decimal("45000.00")
    assert statement.closing_balance == Decimal("58500.00")
    assert len(statement.transactions) == 7
