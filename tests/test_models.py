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

from bank_parser.models import GSTR2AEntry, Statement, Transaction


def test_transaction_creation():
    txn = Transaction(
        date=date(2024, 1, 15),
        description="UPI-PAYMENT TO MERCHANT",
        debit=Decimal("500.00"),
        credit=None,
        balance=Decimal("45000.00"),
        ref_no="UPI123456789",
        category="debit",
    )
    assert txn.date == date(2024, 1, 15)
    assert txn.debit == Decimal("500.00")
    assert txn.category == "debit"


def test_transaction_credit():
    txn = Transaction(
        date=date(2024, 1, 16),
        description="SALARY CREDIT",
        debit=None,
        credit=Decimal("120000.00"),
        balance=Decimal("165000.00"),
        ref_no="SAL987654321",
        category="credit",
    )
    assert txn.credit == Decimal("120000.00")
    assert txn.category == "credit"


def test_transaction_to_dict():
    txn = Transaction(
        date=date(2024, 1, 15),
        description="UPI-PAYMENT TO MERCHANT",
        debit=Decimal("500.00"),
        credit=None,
        balance=Decimal("45000.00"),
        ref_no="UPI123456789",
        category="debit",
    )
    d = txn.to_dict()
    assert d["date"] == "2024-01-15"
    assert d["debit"] == 500.0
    assert d["credit"] == ""
    assert d["balance"] == 45000.0


def test_statement_to_dataframe():
    txns = [
        Transaction(
            date=date(2024, 1, 15),
            description="UPI-PAYMENT",
            debit=Decimal("500.00"),
            credit=None,
            balance=Decimal("45000.00"),
            ref_no="UPI123",
            category="debit",
        ),
        Transaction(
            date=date(2024, 1, 16),
            description="SALARY",
            debit=None,
            credit=Decimal("120000.00"),
            balance=Decimal("165000.00"),
            ref_no="SAL456",
            category="credit",
        ),
    ]
    stmt = Statement(bank="hdfc", transactions=txns)
    df = stmt.to_dataframe()
    assert len(df) == 2
    assert list(df.columns) == [
        "date",
        "description",
        "debit",
        "credit",
        "balance",
        "ref_no",
        "category",
    ]


def test_gstr2a_entry():
    entry = GSTR2AEntry(
        gstin="29ABCDE1234F1Z5",
        invoice_date=date(2024, 1, 15),
        invoice_number="INV001",
        invoice_value=Decimal("11800.00"),
        place_of_supply="29",
        rate=Decimal("18"),
        taxable_value=Decimal("10000.00"),
        igst=Decimal("1800.00"),
    )
    d = entry.to_dict()
    assert d["GSTIN"] == "29ABCDE1234F1Z5"
    assert d["Invoice Date"] == "15-01-2024"
    assert d["Invoice Value"] == 11800.0


def test_parse_amount():
    from bank_parser.banks.hdfc import HDFCParser

    parser = HDFCParser("")
    assert parser.parse_amount("1,000.00") == Decimal("1000.00")
    assert parser.parse_amount("500") == Decimal("500")
    assert parser.parse_amount("") is None
    assert parser.parse_amount("-") is None
    assert parser.parse_amount("0.00") is None


def test_parse_date():
    from bank_parser.banks.hdfc import HDFCParser

    parser = HDFCParser("")
    assert parser.parse_date("15/01/2024").date() == date(2024, 1, 15)
    assert parser.parse_date("15-01-2024").date() == date(2024, 1, 15)
    assert parser.parse_date("2024-01-15").date() == date(2024, 1, 15)
    assert parser.parse_date("15 Jan 2024").date() == date(2024, 1, 15)
    assert parser.parse_date("invalid") is None


def _txn(d: str, debit=None, credit=None, balance=None):
    return Transaction(
        date=date.fromisoformat(d),
        description="test",
        debit=debit,
        credit=credit,
        balance=balance or Decimal("0"),
        category="debit" if debit is not None else "credit",
    )


def test_validate_balances_ok():
    stmt = Statement(
        bank="hdfc",
        opening_balance=Decimal("1000.00"),
        closing_balance=Decimal("1500.00"),
        transactions=[
            _txn("2024-01-01", credit=Decimal("1000.00"), balance=Decimal("2000.00")),
            _txn("2024-01-02", debit=Decimal("500.00"), balance=Decimal("1500.00")),
        ],
    )
    result = stmt.validate_balances()
    assert result.status == "ok"
    assert result.ok is True
    assert result.expected_closing == Decimal("1500.00")
    assert result.calculated_closing == Decimal("1500.00")
    assert result.difference == Decimal("0")
    assert result.total_debits == Decimal("500.00")
    assert result.total_credits == Decimal("1000.00")
    assert stmt.validation is result


def test_validate_balances_failed_reports_difference():
    stmt = Statement(
        bank="hdfc",
        opening_balance=Decimal("1000.00"),
        closing_balance=Decimal("1600.00"),
        transactions=[
            _txn("2024-01-01", credit=Decimal("1000.00"), balance=Decimal("2000.00")),
            _txn("2024-01-02", debit=Decimal("500.00"), balance=Decimal("1500.00")),
        ],
    )
    result = stmt.validate_balances()
    assert result.status == "failed"
    assert result.ok is False
    assert result.expected_closing == Decimal("1600.00")
    assert result.calculated_closing == Decimal("1500.00")
    assert result.difference == Decimal("-100.00")


def test_validate_balances_skipped_when_balances_missing():
    stmt = Statement(
        bank="axis_cc",
        opening_balance=None,
        closing_balance=None,
        transactions=[_txn("2024-01-01", debit=Decimal("50.00"))],
    )
    result = stmt.validate_balances()
    assert result.status == "skipped"
    assert "not extracted" in (result.reason or "")


def test_validate_balances_skipped_when_no_transactions():
    stmt = Statement(
        bank="hdfc",
        opening_balance=Decimal("100.00"),
        closing_balance=Decimal("100.00"),
        transactions=[],
    )
    result = stmt.validate_balances()
    assert result.status == "skipped"
    assert "no transactions" in (result.reason or "")
