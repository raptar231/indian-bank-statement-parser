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

raptar231)/raptar231)
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
Kotak Mahindra Bank statement parser.

Net banking e-statements use ``Date | Narration | Chq/Ref No | Withdrawal (DR) /
Deposit (CR) | Balance`` tables with ``DD-MMM-YYYY`` rows. The amount is printed
with a trailing ``Dr``/``Cr`` marker (some variants use separate debit/credit
columns instead); the running balance always follows. Row narrations continue
on the following lines and page-level sub-totals must be skipped.
"""

import re
from datetime import date
from decimal import Decimal

from bank_parser.banks.base import BaseBankParser
from bank_parser.models import Statement, Transaction

# A transaction row starts with a DD-MMM-YYYY (or DD/MM/YYYY) date.
SAVINGS_ROW_RE = re.compile(r"^(\d{1,2}-[A-Za-z]{3}-\d{4}|\d{2}/\d{2}/\d{4})(?:\s+(.*))?$")

# Amounts (e.g. 18,432.50) anywhere in a row/block.
AMOUNTS_RE = re.compile(r"([\d,]+\.\d{2})")

# Amount immediately followed by a Dr/Cr marker, e.g. "347.00 Dr".
MARKER_RE = re.compile(r"([\d,]+\.\d{2})\s*(Dr|Cr)\b", re.IGNORECASE)

# Lines that are not transaction narration and must not be appended to a block.
SKIP_RE = re.compile(
    r"^(?:Opening|Closing)\s+Balance|Sub\s*[- ]?Total|Total\b|Statement\s+Period|"
    r"A/C|Account\s+No|Branch|IFSC|Page\b|Date\s+Narration|Withdrawal",
    re.IGNORECASE,
)

PERIOD_RE = re.compile(
    r"(?:Statement\s+)?Period[.:\s]*"
    r"(\d{1,2}-[A-Za-z]{3}-\d{4}|\d{2}/\d{2}/\d{4})\s+to\s+"
    r"(\d{1,2}-[A-Za-z]{3}-\d{4}|\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)

ACCOUNT_RE = re.compile(r"(?:A/C|A/c|Account)\s*(?:No|Number)[.:\s]*([A-Z0-9X*]+)")

OPENING_BALANCE_RE = re.compile(r"Opening\s+Balance[.:\s]*([\d,]+\.\d{2})", re.IGNORECASE)
CLOSING_BALANCE_RE = re.compile(r"Closing\s+Balance[.:\s]*([\d,]+\.\d{2})", re.IGNORECASE)

# Narration-embedded references: a UPI reference, a UTR, or a 12+ digit run.
REF_PATTERNS = [
    r"UPI/(?:DR|CR)/(\d+)",
    r"\bUTR\s*(?:NO\.?)?[:]?\s*([A-Z0-9]+)",
    r"([A-Z]?\d{12,})",
]


class KotakParser(BaseBankParser):
    bank_code = "kotak"
    bank_name = "Kotak Mahindra Bank"

    def parse(self) -> Statement:
        pages_text = self.extract_text()
        full_text = "\n".join(pages_text)
        return self._parse_statement(pages_text, full_text)

    def _parse_statement(self, pages_text: list[str], full_text: str) -> Statement:
        self.statement.account_number = self._extract_account_number(full_text)
        self.statement.account_type = self._extract_account_type(full_text)
        self.statement.statement_period_start, self.statement.statement_period_end = (
            self._extract_period(full_text)
        )
        opening, closing = self._extract_balances(full_text)
        self.statement.transactions = self._parse_transactions(pages_text, opening)
        if opening is None and self.statement.transactions:
            first = self.statement.transactions[0]
            opening = first.balance + (first.debit or Decimal("0")) - (first.credit or Decimal("0"))
        if closing is None and self.statement.transactions:
            closing = self.statement.transactions[-1].balance
        self.statement.opening_balance = opening
        self.statement.closing_balance = closing
        return self.statement

    def _extract_account_number(self, text: str) -> str | None:
        match = ACCOUNT_RE.search(text)
        return match.group(1) if match else None

    def _extract_account_type(self, text: str) -> str | None:
        lowered = text.lower()
        if "credit card" in lowered:
            return "Credit Card"
        if "current" in lowered:
            return "Current"
        if "saving" in lowered:
            return "Savings"
        return None

    def _extract_period(self, text: str) -> tuple[date | None, date | None]:
        match = PERIOD_RE.search(text)
        if not match:
            return None, None
        start = self.parse_date(match.group(1))
        end = self.parse_date(match.group(2))
        if start and end:
            return start.date(), end.date()
        return None, None

    def _extract_balances(self, text: str) -> tuple[Decimal | None, Decimal | None]:
        opening = None
        closing = None
        opening_match = OPENING_BALANCE_RE.search(text)
        if opening_match:
            opening = self.parse_amount(opening_match.group(1))
        closing_match = CLOSING_BALANCE_RE.search(text)
        if closing_match:
            closing = self.parse_amount(closing_match.group(1))
        return opening, closing

    def _parse_transactions(
        self, pages_text: list[str], opening_balance: Decimal | None = None
    ) -> list[Transaction]:
        transactions: list[Transaction] = []
        prev_balance: Decimal | None = opening_balance
        for page_text in pages_text:
            block: list[str] = []
            for line in page_text.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                row_start = SAVINGS_ROW_RE.match(stripped)
                if row_start:
                    txn = self._flush_block(block, prev_balance)
                    if txn:
                        transactions.append(txn)
                        prev_balance = txn.balance
                    block = [stripped]
                elif block and not SKIP_RE.match(stripped):
                    block.append(stripped)
            txn = self._flush_block(block, prev_balance)
            if txn:
                transactions.append(txn)
        return transactions

    def _flush_block(self, block: list[str], prev_balance: Decimal | None) -> Transaction | None:
        if not block:
            return None
        return self._parse_block(block, prev_balance)

    def _parse_block(self, block: list[str], prev_balance: Decimal | None) -> Transaction | None:
        row_start = SAVINGS_ROW_RE.match(block[0])
        if not row_start:
            return None
        txn_date_dt = self.parse_date(row_start.group(1))
        if txn_date_dt is None:
            return None
        txn_date = txn_date_dt.date()

        amounts: list[tuple[str, int, int]] = []
        for line_idx, line in enumerate(block):
            for match in AMOUNTS_RE.finditer(line):
                amounts.append((match.group(1), match.start(), line_idx))
        if len(amounts) < 2:
            return None

        balance = self.parse_amount(amounts[-1][0])
        amount = self.parse_amount(amounts[-2][0])
        if balance is None or amount is None:
            return None

        description = self._build_description(block, row_start.end(1))
        if not description:
            return None

        debit, credit = self._classify_amount(block, prev_balance, amount, balance, description)
        if debit is None and credit is None:
            return None

        return Transaction(
            date=txn_date,
            description=description,
            debit=debit,
            credit=credit,
            balance=balance,
            ref_no=self._extract_ref(description),
            category="credit" if credit else "debit",
        )

    def _build_description(self, block: list[str], date_end: int) -> str:
        parts: list[str] = []
        for idx, line in enumerate(block):
            line = line.strip()
            if not line:
                continue
            first_amount = AMOUNTS_RE.search(line)
            if idx == 0:
                line = line[date_end : first_amount.start()] if first_amount else line[date_end:]
            elif first_amount:
                line = line[: first_amount.start()]
            line = line.strip()
            if line:
                parts.append(line)
        return self.clean_description(re.sub(r"\s+-\s+", " ", " ".join(parts)))

    def _classify_amount(
        self,
        block: list[str],
        prev_balance: Decimal | None,
        amount: Decimal,
        balance: Decimal,
        description: str,
    ) -> tuple[Decimal | None, Decimal | None]:
        block_text = " ".join(block)
        marker = MARKER_RE.search(block_text)
        if marker:
            is_credit = marker.group(2).upper() == "CR"
            return (None, amount) if is_credit else (amount, None)
        if prev_balance is not None:
            if prev_balance + amount == balance:
                return None, amount
            if prev_balance - amount == balance:
                return amount, None
        if re.search(r"\bCr\b|REFUND|SALARY|DEPOSIT|INWARD|NEFT|RTGS", description, re.IGNORECASE):
            return None, amount
        return amount, None

    def _extract_ref(self, description: str) -> str | None:
        for pat in REF_PATTERNS:
            match = re.search(pat, description, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
