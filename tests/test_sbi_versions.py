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

from bank_parser.banks.sbi import SBICreditCardParser, SBIParser
from bank_parser.banks.sbi_versions import SBIParserRegistry
from bank_parser.banks.sbi_versions.v2017_b import SBIParser2017B
from bank_parser.banks.sbi_versions.v2021_d import SBIParser2021D
from bank_parser.banks.sbi_versions.v2023_e import SBIParser2023E

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "sbi"


def _load(name: str) -> tuple[str, list[str]]:
    text = (FIXTURES_DIR / name).read_text(encoding="utf-8")
    return text, text.split("=== PAGE ===")


def _row(txn) -> tuple[date, Decimal, Decimal, Decimal]:
    return txn.date, txn.debit, txn.credit, txn.balance


def test_detect_netbanking_2017_18():
    text, _ = _load("netbanking_2017_18.txt")
    assert SBIParserRegistry.detect(text).version == "2017B"


def test_detect_netbanking_2018_19():
    text, _ = _load("netbanking_2018_19.txt")
    assert SBIParserRegistry.detect(text).version == "2017B"


def test_detect_netbanking_2021_22():
    text, _ = _load("netbanking_2021_22.txt")
    assert SBIParserRegistry.detect(text).version == "2021D"


def test_detect_yono_multi():
    text, _ = _load("yono_savings_multi_jan_2026.txt")
    assert SBIParserRegistry.detect(text).version == "2023E"


def test_detect_yono_combined():
    text, _ = _load("yono_savings_combined_sep_2025.txt")
    assert SBIParserRegistry.detect(text).version == "2023E"


def test_detect_yono_empty():
    text, _ = _load("yono_savings_empty_jun_2026.txt")
    assert SBIParserRegistry.detect(text).version == "2023E"


def test_netbanking_2017_18_transactions():
    text, pages = _load("netbanking_2017_18.txt")
    txns = SBIParser2017B("")._parse_transactions(pages)
    assert len(txns) == 5

    assert txns[0].date == date(2017, 10, 13)
    assert txns[0].debit is None
    assert txns[0].credit == Decimal("7500.00")
    assert txns[0].balance == Decimal("10298.02")
    assert txns[0].ref_no == "NEFT*HDFC0000240*N286170"
    assert txns[0].category == "credit"

    assert _row(txns[1]) == (date(2017, 11, 1), Decimal("500.00"), None, Decimal("41696.52"))
    assert txns[1].ref_no == "5815"
    assert txns[1].category == "debit"

    assert _row(txns[2]) == (date(2017, 11, 9), Decimal("398.00"), None, Decimal("38498.52"))
    assert txns[2].ref_no == "JSBI5800496343I"
    assert txns[2].category == "debit"

    assert _row(txns[3]) == (date(2017, 12, 13), Decimal("295.00"), None, Decimal("1454.52"))
    assert txns[3].ref_no == "szyrfG8E9BEfdEy"
    assert txns[3].category == "debit"

    assert _row(txns[4]) == (date(2017, 12, 16), None, Decimal("12.50"), Decimal("10310.52"))
    assert txns[4].ref_no is None
    assert txns[4].category == "credit"


def test_netbanking_2018_19_transactions():
    text, pages = _load("netbanking_2018_19.txt")
    txns = SBIParser2017B("")._parse_transactions(pages)
    assert len(txns) == 5

    assert _row(txns[0]) == (date(2018, 4, 18), None, Decimal("25000.00"), Decimal("35000.00"))
    assert txns[0].ref_no is None
    assert txns[0].category == "credit"

    assert _row(txns[1]) == (date(2018, 4, 19), Decimal("2000.00"), None, Decimal("33000.00"))
    assert txns[1].category == "debit"

    assert _row(txns[2]) == (date(2018, 4, 22), None, Decimal("1500.00"), Decimal("34500.00"))
    assert txns[2].ref_no == "P2A/708521222222/XXX"
    assert txns[2].category == "credit"

    assert _row(txns[3]) == (date(2018, 4, 25), Decimal("1200.00"), None, Decimal("33300.00"))
    assert txns[3].ref_no == "NEFT*HDFC0000240*N286170"
    assert txns[3].category == "debit"

    assert _row(txns[4]) == (date(2018, 4, 30), None, Decimal("15.00"), Decimal("33315.00"))
    assert txns[4].category == "credit"


def test_netbanking_2021_22_transactions():
    text, pages = _load("netbanking_2021_22.txt")
    txns = SBIParser2021D("")._parse_transactions(pages)
    assert len(txns) == 5

    assert _row(txns[0]) == (date(2021, 4, 1), None, Decimal("4000.00"), Decimal("12000.00"))
    assert txns[0].ref_no == "412345678901"
    assert txns[0].category == "credit"

    assert _row(txns[1]) == (date(2021, 4, 5), Decimal("2500.00"), None, Decimal("9500.00"))
    assert txns[1].ref_no == "210000000000"
    assert txns[1].category == "debit"

    assert _row(txns[2]) == (date(2021, 4, 10), Decimal("1000.00"), None, Decimal("8500.00"))
    assert txns[2].ref_no == "N286170387881124"
    assert txns[2].category == "debit"

    assert _row(txns[3]) == (date(2021, 4, 15), None, Decimal("5000.00"), Decimal("13500.00"))
    assert txns[3].ref_no == "P2A/705111111111/XXX"
    assert txns[3].category == "credit"

    assert _row(txns[4]) == (date(2021, 4, 20), Decimal("3000.00"), None, Decimal("10500.00"))
    assert txns[4].ref_no is None
    assert txns[4].category == "debit"


def test_yono_multi_transactions():
    text, pages = _load("yono_savings_multi_jan_2026.txt")
    txns = SBIParser2023E("")._parse_transactions(pages)
    assert len(txns) == 2

    assert txns[0].date == date(2025, 12, 4)
    assert txns[0].description == "APY_DEC25_Mont_1000_99999999999999999_999999999999"
    assert txns[0].debit == Decimal("90.00")
    assert txns[0].credit is None
    assert txns[0].balance == Decimal("236.21")
    assert txns[0].category == "debit"

    assert txns[1].date == date(2025, 12, 25)
    assert txns[1].description == "INTEREST CREDIT"
    assert txns[1].debit is None
    assert txns[1].credit == Decimal("3.00")
    assert txns[1].balance == Decimal("239.21")
    assert txns[1].category == "credit"


def test_yono_combined_skips_loan_section():
    text, pages = _load("yono_savings_combined_sep_2025.txt")
    txns = SBIParser2023E("")._parse_transactions(pages)
    assert len(txns) == 1
    assert txns[0].date == date(2025, 8, 4)
    assert txns[0].debit == Decimal("90.00")
    assert txns[0].balance == Decimal("1184.21")


def test_yono_empty_no_transactions():
    text, pages = _load("yono_savings_empty_jun_2026.txt")
    txns = SBIParser2023E("")._parse_transactions(pages)
    assert txns == []


def test_yono_metadata():
    parser = SBIParser2023E("")
    text, _ = _load("yono_savings_multi_jan_2026.txt")
    assert parser._extract_account_number(text) == "XXXXXXX0000"
    assert parser._extract_account_type(text) == "Savings"
    assert parser._extract_opening_balance(text) == Decimal("326.21")
    assert parser._extract_closing_balance(text) == Decimal("239.21")
    assert parser.detect_statement_period(text) == (date(2025, 12, 1), date(2025, 12, 31))


def test_yono_combined_metadata_uses_savings_balances():
    parser = SBIParser2023E("")
    text, _ = _load("yono_savings_combined_sep_2025.txt")
    assert parser._extract_opening_balance(text) == Decimal("1274.21")
    assert parser._extract_closing_balance(text) == Decimal("1184.21")


def test_yono_empty_metadata_falls_back_to_available_balance():
    parser = SBIParser2023E("")
    text, _ = _load("yono_savings_empty_jun_2026.txt")
    assert parser._extract_opening_balance(text) is None
    assert parser._extract_closing_balance(text) == Decimal("35481.14")
    assert parser.detect_statement_period(text) == (date(2026, 5, 31), date(2026, 5, 31))


def test_netbanking_metadata():
    parser = SBIParser2017B("")
    text, _ = _load("netbanking_2017_18.txt")
    assert parser._extract_account_number(text) == "0000001111111111"
    assert parser.detect_statement_period(text) == (date(2017, 4, 1), date(2018, 3, 31))


# ---------------------------------------------------------------------------
# Credit card layout
# ---------------------------------------------------------------------------


def test_sbi_parser_detects_credit_card_text():
    text, _ = _load("sbi_credit-jan-2025.txt")
    assert SBIParser("")._looks_like_credit_card(text) is True


def test_sbi_parser_does_not_detect_savings_as_credit_card():
    text, _ = _load("netbanking_2021_22.txt")
    assert SBIParser("")._looks_like_credit_card(text) is False


def test_sbi_credit_card_transactions():
    _, pages = _load("sbi_credit-jan-2025.txt")
    txns = SBICreditCardParser("")._parse_transactions(pages)
    assert len(txns) == 8

    assert txns[0].date == date(2024, 12, 26)
    assert txns[0].description == "UPI/GOOGLE PAY/MERCHANT STORE"
    assert txns[0].debit == Decimal("1234.56")
    assert txns[0].credit is None
    assert txns[0].balance == Decimal("0")
    assert txns[0].category == "debit"

    assert txns[1].description == "DEBIT CARD PURCHASE - SWIGGY"
    assert txns[1].debit == Decimal("456.00")

    assert txns[2].ref_no == "123456789012"
    assert txns[2].debit == Decimal("2345.67")

    assert txns[3].description == "PAYMENT RECEIVED - THANKS"
    assert txns[3].credit == Decimal("5000.00")
    assert txns[3].debit is None
    assert txns[3].category == "credit"

    assert txns[4].description == "REFUND FROM MERCHANT"
    assert txns[4].credit == Decimal("1234.56")
    assert txns[4].category == "credit"

    assert txns[5].description == "EMI PROCESSING FEE, REF 765432"
    assert txns[5].debit == Decimal("299.00")
    assert txns[5].ref_no == "765432"

    assert txns[6].description == "FINANCE CHARGE"
    assert txns[6].debit == Decimal("922.00")

    assert txns[7].description == "GST"
    assert txns[7].debit == Decimal("53.82")


def test_sbi_credit_card_metadata():
    text, _ = _load("sbi_credit-jan-2025.txt")
    parser = SBICreditCardParser("")
    statement = parser._parse_statement(text.split("=== PAGE ==="), text)
    assert statement.account_number == "5245 XXXX XXXX 1234"
    assert statement.account_type == "Credit Card"
    assert statement.statement_period_start == date(2024, 12, 26)
    assert statement.statement_period_end == date(2025, 1, 25)
    assert statement.opening_balance is None
    assert statement.closing_balance is None


def test_sbi_credit_card_parser_overrides_parse():
    # The credit-card parser must override parse() so the inherited
    # auto-detect path (which routes credit-card text back here) can
    # never re-enter itself and recurse.
    assert "parse" in SBICreditCardParser.__dict__
