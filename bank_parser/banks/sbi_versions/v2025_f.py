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

"""
SBI Parser Version 2025F (2025+ "Statement of Account" format)

This format uses a tabular layout with columns:
    Txn Date | Value Date | Description | Ref No./Cheque No. | Debit | Credit | Balance

Dates are in dd/mm/yyyy format. Amounts use "-" for empty cells.
The table is extracted via pdfplumber's extract_table() to avoid
description lines getting clubbed together in text extraction.
"""

import re
from datetime import date
from decimal import Decimal

import pdfplumber

from bank_parser.banks.sbi_versions import SBIBaseParser
from bank_parser.models import Transaction


class SBIParser2025F(SBIBaseParser):
    """SBI Parser for 2025+ 'Statement of Account' PDF format."""

    version = "2025F"
    year_range = (2026, 2030)
    require_header = True

    header_patterns = [
        r"STATEMENT\s+OF\s+ACCOUNT",
    ]

    identifier_keywords = [
        "STATEMENT OF ACCOUNT",
        "Statement From",
        "Clear Balance",
        "Account Summary",
    ]

    has_value_date_column = True
    has_cheque_no_column = True

    _TABLE_HEADER_RE = re.compile(r"^Txn\s+Date", re.IGNORECASE)

    def _parse_transaction_lines(self, text: str) -> list[Transaction]:
        """Required by base class but not used for this format."""
        return []

    def _parse_transactions(self, pages_text: list[str]) -> list[Transaction]:
        """Parse transactions using pdfplumber's table extraction."""
        transactions: list[Transaction] = []

        try:
            with pdfplumber.open(self.pdf_path, password=self.password) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if not table:
                        continue
                    transactions.extend(self._parse_table_rows(table))
        except Exception:
            pass

        return transactions

    def _parse_table_rows(self, table: list[list[str | None]]) -> list[Transaction]:
        """Parse rows from a single page's extracted table."""
        transactions: list[Transaction] = []

        for row in table:
            if not row or len(row) < 7:
                continue

            txn_date_str = (row[0] or "").strip()
            if not re.match(r"^\d{2}/\d{2}/\d{4}$", txn_date_str):
                continue

            description = (row[2] or "").strip()
            ref_no_raw = (row[3] or "").strip()
            debit_str = (row[4] or "").strip()
            credit_str = (row[5] or "").strip()
            balance_str = (row[6] or "").strip()

            if not description or description == "-":
                continue

            txn_date = self._parse_date(txn_date_str)
            if txn_date is None:
                continue

            debit = self.parse_amount(debit_str)
            credit = self.parse_amount(credit_str)
            balance = self.parse_amount(balance_str)

            if balance is None or (debit is None and credit is None):
                continue

            ref_no: str | None = None
            if ref_no_raw not in ("", "-"):
                ref_no = ref_no_raw

            transactions.append(
                Transaction(
                    date=txn_date.date(),
                    description=self.clean_description(description.replace("\n", " ")),
                    debit=debit,
                    credit=credit,
                    balance=balance,
                    ref_no=ref_no,
                    category="credit" if credit else "debit",
                )
            )

        return transactions

    def detect_statement_period(self, text: str) -> tuple[date | None, date | None]:
        """Extract period from 'Statement From :dd-mm-yyyy to dd-mm-yyyy'."""
        match = re.search(
            r"Statement\s+From\s*:\s*(\d{2}-\d{2}-\d{4})\s+to\s+(\d{2}-\d{2}-\d{4})",
            text,
            re.IGNORECASE,
        )
        if match:
            start = self._parse_date(match.group(1))
            end = self._parse_date(match.group(2))
            if start and end:
                return start.date(), end.date()
        return super().detect_statement_period(text)

    def _extract_opening_balance(self, text: str) -> Decimal | None:
        """Extract opening balance from the first transaction's running balance."""
        try:
            with pdfplumber.open(self.pdf_path, password=self.password) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if not table:
                        continue
                    for row in table:
                        if not row or len(row) < 7:
                            continue
                        txn_date_str = (row[0] or "").strip()
                        if not re.match(r"^\d{2}/\d{2}/\d{4}$", txn_date_str):
                            continue
                        balance_str = (row[6] or "").strip()
                        debit_str = (row[4] or "").strip()
                        credit_str = (row[5] or "").strip()
                        first_balance = self.parse_amount(balance_str)
                        first_debit = self.parse_amount(debit_str)
                        first_credit = self.parse_amount(credit_str)
                        if first_balance is not None:
                            opening = first_balance
                            if first_credit:
                                opening -= first_credit
                            if first_debit:
                                opening += first_debit
                            return opening
        except Exception:
            pass
        return super()._extract_opening_balance(text)

    def _extract_closing_balance(self, text: str) -> Decimal | None:
        """Extract closing balance from the last transaction's running balance."""
        last_balance: Decimal | None = None
        try:
            with pdfplumber.open(self.pdf_path, password=self.password) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if not table:
                        continue
                    for row in table:
                        if not row or len(row) < 7:
                            continue
                        txn_date_str = (row[0] or "").strip()
                        if not re.match(r"^\d{2}/\d{2}/\d{4}$", txn_date_str):
                            continue
                        balance_str = (row[6] or "").strip()
                        bal = self.parse_amount(balance_str)
                        if bal is not None:
                            last_balance = bal
        except Exception:
            pass
        if last_balance is not None:
            return last_balance
        return super()._extract_closing_balance(text)
