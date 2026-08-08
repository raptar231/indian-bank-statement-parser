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

# Copyright 2024-2026 Koushik Mondal (github.com/raptar231)
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

from bank_parser.banks.dbs import DBSParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "dbs"


def _load(name: str) -> tuple[str, list[str]]:
    text = (FIXTURES_DIR / name).read_text(encoding="utf-8")
    return text, text.split("=== PAGE ===")


def _txns(parser: DBSParser, name: str):
    text, pages = _load(name)
    opening = parser._extract_balances(text)[0]
    return parser._parse_transactions(pages, opening)


def test_savings_2019_transactions():
    txns = _txns(DBSParser(""), "dbs_savings-may-2019.txt")
    assert len(txns) == 10

    assert txns[0].date == date(2019, 5, 1)
    assert txns[0].description == "UPI/DR/426784531012/ZOMATO PAYMENTS"
    assert txns[0].credit == Decimal("350.00")
    assert txns[0].debit is None
    assert txns[0].balance == Decimal("3785.89")
    assert txns[0].ref_no == "426784531012"
    assert txns[0].category == "credit"

    assert txns[1].description == "ATM WDL 123456 DELHI"
    assert txns[1].debit == Decimal("2000.00")
    assert txns[1].ref_no is None

    assert txns[3].debit == Decimal("1500.00")
    assert txns[3].ref_no == "536409876321"

    assert txns[4].debit == Decimal("4500.00")
    assert txns[4].ref_no == "B042718367821034"

    assert txns[6].description == ("UPI/CR/789012345678/RAHUL MEHTA/REFUND FROM FLIPKART ORDER")
    assert txns[6].credit == Decimal("500.00")
    assert txns[6].balance == Decimal("16400.89")
    assert txns[6].ref_no == "789012345678"
    assert txns[6].category == "credit"

    assert txns[8].credit == Decimal("18000.00")
    assert txns[8].ref_no == "N042718369927155"

    assert txns[9].date == date(2019, 5, 31)
    assert txns[9].debit == Decimal("205.00")
    assert txns[9].balance == Decimal("27995.89")
    assert txns[9].ref_no == "987654321012"


def test_savings_2019_metadata():
    text, _ = _load("dbs_savings-may-2019.txt")
    parser = DBSParser("")
    assert parser._extract_account_number(text) == "123456789012"
    assert parser._extract_account_type(text) == "Savings"
    assert parser._extract_period(text) == (date(2019, 5, 1), date(2019, 5, 31))
    assert parser._extract_balances(text) == (Decimal("3435.89"), Decimal("27995.89"))


def test_savings_2019_statement():
    text, pages = _load("dbs_savings-may-2019.txt")
    statement = DBSParser("")._parse_statement(pages, text)
    assert statement.account_number == "123456789012"
    assert statement.account_type == "Savings"
    assert statement.statement_period_start == date(2019, 5, 1)
    assert statement.statement_period_end == date(2019, 5, 31)
    assert statement.opening_balance == Decimal("3435.89")
    assert statement.closing_balance == Decimal("27995.89")
    assert len(statement.transactions) == 10
