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

# Copyright 2024 Koushik Mondal (github.com/komo0225)
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

from bank_parser.banks.hdfc import HDFCCreditCardParser, HDFCParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "hdfc"


def _load(name: str) -> tuple[str, list[str]]:
    text = (FIXTURES_DIR / name).read_text(encoding="utf-8")
    return text, text.split("=== PAGE ===")


def _txns(parser: HDFCParser, name: str):
    _, pages = _load(name)
    return parser._parse_transactions(pages)


# ---------------------------------------------------------------------------
# Old 2019 savings layout
# ---------------------------------------------------------------------------


def test_savings_old_2019_transactions():
    txns = _txns(HDFCParser(""), "hdfc_savings-old-mar-2019.txt")
    assert len(txns) == 5

    assert txns[0].date == date(2019, 3, 1)
    assert txns[0].description == "ATW-436278XXXXXX9521-S1ANCN32-CHENNAI"
    assert txns[0].debit == Decimal("15000.00")
    assert txns[0].credit is None
    assert txns[0].balance == Decimal("410300.00")
    assert txns[0].ref_no == "7253"
    assert txns[0].category == "debit"

    assert txns[1].date == date(2019, 3, 9)
    assert txns[1].description == "IB SS FUNDS TRANSFER DR-55000009876543"
    assert txns[1].debit == Decimal("45000.00")
    assert txns[1].ref_no is None

    assert txns[2].date == date(2019, 3, 22)
    assert txns[2].description == (
        "IMPS-908117234567-SAMPLE JEWELLERS-BKDN-X XXXXXXX0077-SAMPLE JEWELLERS"
    )
    assert txns[2].debit == Decimal("18000.00")
    assert txns[2].balance == Decimal("347300.00")
    assert txns[2].ref_no == "908117234567"

    assert txns[3].ref_no == "908412345678"
    assert txns[3].debit == Decimal("22000.00")

    assert txns[4].date == date(2019, 3, 29)
    assert txns[4].description == "SALARY ACME TECHNOLOGIES PVT LTD"
    assert txns[4].debit is None
    assert txns[4].credit == Decimal("52750.00")
    assert txns[4].balance == Decimal("378050.00")
    assert txns[4].ref_no == "903286789012"
    assert txns[4].category == "credit"


def test_savings_old_2019_metadata():
    text, _ = _load("hdfc_savings-old-mar-2019.txt")
    parser = HDFCParser("")
    assert parser._extract_account_number(text) == "50100387621480"
    assert parser._extract_opening_balance(text) == Decimal("425300.00")
    assert parser._extract_closing_balance(text) == Decimal("378050.00")
    assert parser._extract_period(text) == (date(2019, 3, 1), date(2019, 3, 29))


# ---------------------------------------------------------------------------
# 2024 savings layout (combined-style header, inline Value Dt/Ref)
# ---------------------------------------------------------------------------


def test_savings_new_2024_transactions():
    txns = _txns(HDFCParser(""), "hdfc_savings-new-apr-2024.txt")
    assert len(txns) == 19

    assert txns[0].date == date(2024, 4, 1)
    assert txns[0].description == "00487230005612 NET BANKING SI -Priya HDFC"
    assert txns[0].debit == Decimal("12000.00")
    assert txns[0].credit is None
    assert txns[0].balance == Decimal("1413000.00")
    assert txns[0].ref_no is None

    assert txns[2].description == (
        "UPI-Rahul Vikram Sharma-fakeuser@ fifederal-FDRL0005556-409876543210-U PI"
    )
    assert txns[2].ref_no == "409876543210"

    assert txns[3].description == (
        "NEFT Dr-SBIN0002288-SBI HOME LOAN-ACMECORP- MUM-N098765432112345-NET "
        "BANKING SI -SBI Home Loan"
    )
    assert txns[3].ref_no == "N098765432112345"
    assert txns[3].debit == Decimal("78000.00")

    assert txns[5].description == "ACH D- RACPC CHENNAI-NCACDOSYM2404050001Val ue Dt"
    assert txns[5].ref_no == "2876543219"
    assert txns[5].debit == Decimal("38000.00")

    # Blank-narration row: amount only.
    assert txns[10].description == ""
    assert txns[10].date == date(2024, 4, 15)
    assert txns[10].debit == Decimal("45350.00")
    assert txns[10].balance == Decimal("1220803.00")
    assert txns[10].ref_no is None

    # Salary credit with inline ref.
    salary = next(t for t in txns if t.category == "credit" and t.credit == Decimal("235000.00"))
    assert salary.description == (
        "NEFT Cr-CITI0000004-GLOBEX-1608-SALARY PAYMENT-Rahul Vikram Sharma-"
        "CITIN24998877665 Salary Transfer April 2024"
    )
    assert salary.ref_no == "CITIN24998877665"

    # Small UPI cashback credit.
    cashback = next(t for t in txns if t.credit == Decimal("3.00"))
    assert cashback.ref_no == "447876543210"

    assert all(t.balance is not None for t in txns)


def test_savings_new_2024_metadata():
    text, _ = _load("hdfc_savings-new-apr-2024.txt")
    parser = HDFCParser("")
    assert parser._extract_account_number(text) == "50100000004567"
    assert parser._extract_opening_balance(text) == Decimal("1425000.00")
    assert parser._extract_closing_balance(text) == Decimal("1265803.00")
    assert parser._extract_period(text) == (date(2024, 4, 1), date(2024, 4, 30))


# ---------------------------------------------------------------------------
# Current 2026 savings layout (two amount columns, continuation lines)
# ---------------------------------------------------------------------------


def test_savings_2026_transactions():
    txns = _txns(HDFCParser(""), "hdfc_savings-april-2026.txt")
    assert len(txns) == 15

    assert txns[0].date == date(2026, 4, 1)
    assert txns[0].description == "00482730009812 NET BANKING SI -HDFC247 7ABCDE123"
    assert txns[0].debit == Decimal("12000.00")
    assert txns[0].credit is None
    assert txns[0].balance == Decimal("388000.00")
    assert txns[0].ref_no is None

    # Multi-line narration with chq/ref in the column.
    assert txns[2].description == ("UPI-RAJESH KUMAR-9812345678@YBL-HDFC 0000314-120555000001-UPI")
    assert txns[2].ref_no == "120555000001"
    assert txns[2].debit == Decimal("25000.00")

    # ACH credits classified via "C-" marker.
    ach = next(t for t in txns if t.description.startswith("ACH C-"))
    assert ach.credit == Decimal("1800.00")
    assert ach.debit is None
    assert ach.ref_no == "2100000051"
    assert ach.category == "credit"

    # NEFT salary credit.
    neft = next(t for t in txns if t.category == "credit" and t.credit == Decimal("250.00"))
    assert neft.description.startswith("NEFT CR-CITI0000004-GLOBEX-1608-SALARY")

    # Continuation lines kept, ref from the chq/ref column.
    flipkart = next(t for t in txns if "FLIPKART" in t.description)
    assert flipkart.ref_no == "648000012345"
    assert flipkart.debit == Decimal("8500.00")
    assert flipkart.balance == Decimal("301899.50")

    # The last row (page 2 continuation page) is parsed too.
    assert txns[-1].description.startswith("NEFT CR-CITI0000004-GLOBEX-1608-SALARY")
    assert txns[-1].credit == Decimal("175000.00")
    assert txns[-1].balance == Decimal("476899.50")

    assert txns[-2].date == date(2026, 4, 27)


def test_savings_2026_metadata():
    text, _ = _load("hdfc_savings-april-2026.txt")
    parser = HDFCParser("")
    assert parser._extract_account_number(text) == "50100000001234"
    assert parser._extract_account_type(text) == "SAVINGS - RESIDENTS"
    assert parser._extract_opening_balance(text) == Decimal("400000.00")
    assert parser._extract_closing_balance(text) == Decimal("476899.50")
    assert parser._extract_period(text) == (date(2026, 4, 1), date(2026, 4, 30))


# ---------------------------------------------------------------------------
# Credit card statements
# ---------------------------------------------------------------------------


def test_credit_card_april_2026_transactions():
    _, pages = _load("hdfc_credit-april-2026.txt")
    txns = HDFCCreditCardParser("")._parse_cc_transactions(pages)
    assert len(txns) == 10

    assert txns[0].date == date(2026, 4, 2)
    assert txns[0].description == "AMAZON PAY INDIA PVT LTD"
    assert txns[0].debit == Decimal("4299.00")
    assert txns[0].credit is None
    assert txns[0].balance == Decimal("0")
    assert txns[0].category == "debit"

    # Multi-line row.
    assert txns[2].description == "NETFLIX INDIA SUBSCRIPTION RENEWAL APR 2026"
    assert txns[2].debit == Decimal("649.00")

    # Cashback is a credit.
    assert txns[4].description == "CASHBACK REWARD APRIL"
    assert txns[4].credit == Decimal("500.00")
    assert txns[4].category == "credit"

    # Refund is a credit.
    assert txns[8].description == "AMAZON REFUND CR"
    assert txns[8].credit == Decimal("1499.00")
    assert txns[8].category == "credit"

    # "CRED RZP PAYMENT" is a debit (payment made, not received).
    assert txns[9].description == "CRED RZP PAYMENT"
    assert txns[9].debit == Decimal("15000.00")
    assert txns[9].category == "debit"


def test_credit_card_april_2026_metadata():
    text, _ = _load("hdfc_credit-april-2026.txt")
    parser = HDFCCreditCardParser("")
    assert parser._extract_cc_account_number(text) == "4329XXXXXXXX4567"
    assert parser._extract_period(text) == (date(2026, 4, 1), date(2026, 4, 30))


def test_credit_card_may_2026_transactions():
    _, pages = _load("hdfc_credit-may-2026.txt")
    txns = HDFCCreditCardParser("")._parse_cc_transactions(pages)
    assert len(txns) == 13

    # Card bill payment received -> credit, with Ref# extracted.
    assert txns[0].description == (
        "BPPY CC PAYMENT AB098765432109xPq7R (Ref# ST261120083000098765432)"
    )
    assert txns[0].credit == Decimal("22450.00")
    assert txns[0].ref_no == "ST261120083000098765432"
    assert txns[0].category == "credit"

    assert txns[1].description == "WWW FOODAPP COMGURGAON"
    assert txns[1].debit == Decimal("387.00")

    assert txns[-1].description == "SCREENMAX NEXUS CENTRALBANGALORE"
    assert txns[-1].debit == Decimal("545.00")


def test_credit_card_may_2026_metadata():
    text, _ = _load("hdfc_credit-may-2026.txt")
    parser = HDFCCreditCardParser("")
    assert parser._extract_cc_account_number(text) == "00361010XXXX8912"
    assert parser._extract_period(text) == (date(2026, 4, 21), date(2026, 5, 20))


def test_credit_card_diners_2026_transactions():
    _, pages = _load("hdfc_credit-diners-jul-2026.txt")
    txns = HDFCCreditCardParser("")._parse_cc_transactions(pages)
    assert len(txns) == 13

    assert txns[0].description == "WWW SWIGGY COMGURGAON"
    assert txns[0].debit == Decimal("521.00")

    payment = next(t for t in txns if t.category == "credit")
    assert payment.description == (
        "BPPY CC PAYMENT AB012345CDEFGH67I (Ref# ST261990083000055667788)"
    )
    assert payment.credit == Decimal("3101.00")
    assert payment.ref_no == "ST261990083000055667788"

    # Rows without the "+" marker and without reward points.
    assert txns[4].description == "The Fusion Pizza and BBENGALURU UR"
    assert txns[4].debit == Decimal("125.00")

    assert txns[5].description == "KINO CINEMASBANGALORE"
    assert txns[5].debit == Decimal("300.00")


def test_credit_card_diners_2026_metadata():
    text, _ = _load("hdfc_credit-diners-jul-2026.txt")
    parser = HDFCCreditCardParser("")
    assert parser._extract_cc_account_number(text) == "00361010XXXX7788"
    assert parser._extract_period(text) == (date(2026, 6, 21), date(2026, 7, 20))


# ---------------------------------------------------------------------------
# Auto-detection
# ---------------------------------------------------------------------------


def test_hdfc_parser_detects_credit_card_text():
    text, _ = _load("hdfc_credit-may-2026.txt")
    assert HDFCParser("")._looks_like_credit_card(text) is True


def test_hdfc_parser_does_not_detect_savings_as_credit_card():
    text, _ = _load("hdfc_savings-april-2026.txt")
    assert HDFCParser("")._looks_like_credit_card(text) is False
