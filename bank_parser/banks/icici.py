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

"""
ICICI Bank statement parsers.

Savings account statements ship in two layouts:

- Legacy (pre-2020): ``DATE MODE DEPOSITS WITHDRAWALS BALANCE`` with
  ``dd-mm-yyyy`` rows and the narration *before* the amounts; the statement
  opens with a ``B/F`` row and ends with a ``Total:`` line. Because the
  debit/credit column that is blank collapses out of the extracted text,
  every row shows exactly two amounts (transaction + running balance) and
  the debit/credit sign is recovered from the balance arithmetic.
- Modern (2026): ``S No. | Cheque Number | Transaction Remarks | Date |
  Withdrawal Amount (INR) | Deposit Amount (INR) | Balance (INR)`` with
  ``dd.mm.yyyy`` dates. The amounts precede the narration on each row; the
  trailing ``Debit trxn`` / ``Credit trxn`` labels in the narration are
  unreliable (a salary credit can carry a ``Debit trxn`` label), so the sign
  is also decided by the running balance arithmetic.

Credit card statements use ``Date | Reference No. | Transaction Details |
Reward Points | Amount (INR)`` rows where refunds and card payments carry a
trailing ``CR`` marker; the reward-points column is an optional integer that
sits between the narration and the amount.
"""

import re
from datetime import date
from decimal import Decimal

from bank_parser.banks.base import BaseBankParser
from bank_parser.models import Statement, Transaction

# --- Legacy (pre-2020) savings layout --------------------------------------

# A transaction row starts with a dd-mm-yyyy date; narration follows.
LEGACY_ROW_RE = re.compile(r"^(\d{2}-\d{2}-\d{4})(?:\s+(.*))?$")

LEGACY_HEADER_RE = re.compile(
    r"\bDEPOSITS?\b[^\n]*\bWITHDRAWALS?\b[^\n]*\bBALANCE\b", re.IGNORECASE
)

# The opening "B/F <balance>" row seeds the running balance for sign recovery.
OPENING_ROW_RE = re.compile(r"^\d{2}-\d{2}-\d{4}\s+B/F\s+([\d,]+\.\d{2})$", re.IGNORECASE)

# Amount + running balance at the end of a row.
LEGACY_AMOUNTS_RE = re.compile(r"([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$")

LEGACY_SUMMARY_RE = re.compile(r"^(?:Total:|Page\b)", re.IGNORECASE)

# --- Modern (2026) savings layout ------------------------------------------

# S No. | dd.mm.yyyy | amount | balance | narration (rest of the line).
MODERN_ROW_RE = re.compile(
    r"^(\d{1,3})\s+(\d{2}\.\d{2}\.\d{4})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*(.*)$"
)

MODERN_HEADER_RE = re.compile(
    r"\bS\s*No\.?[^\n]*\bWithdrawal\w*[^\n]*\bDeposit\w*[^\n]*\bBalance\b",
    re.IGNORECASE,
)

# --- Credit card layout -----------------------------------------------------

CC_HEADER_RE = re.compile(r"\bReference\s*No\.?\b[^\n]*\bAmount\b", re.IGNORECASE)

# Date | reference (10-12 digits) | narration | optional reward points |
# amount | optional "CR" marker for refunds and card payments.
CC_ROW_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(\d{10,})\s+(.+?)\s+(?:(-?\d+)\s+)?([\d,]+\.\d{2})\s*(CR)?\s*$",
    re.IGNORECASE,
)

# --- Shared helpers ---------------------------------------------------------

PERIOD_RE = re.compile(
    r"for\s+the\s+period\s+([A-Za-z]+\s+\d{1,2},\s*\d{4})\s*-\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})"
)

# Narration-embedded IMPS/UPI/NEFT/BIL references: a 12+ digit run with an
# optional single-letter prefix (e.g. NEFT UTR "N108190804966636").
REF_IN_NARRATION_RE = re.compile(r"[A-Z]?\d{12,}")

ACCOUNT_PATTERNS = [
    r"Saving\w*\s+Account\s+no\.\s*(\d{10,})",
    r"Saving\w*\s+Account\s+(\S{8,})",
]


class ICICIParser(BaseBankParser):
    bank_code = "icici"
    bank_name = "ICICI Bank"

    def parse(self) -> Statement:
        pages_text = self.extract_text()
        full_text = "\n".join(pages_text)
        if self._looks_like_credit_card(full_text):
            cc_parser = ICICICreditCardParser(self.pdf_path)
            return cc_parser._parse_statement(pages_text, full_text)
        return self._parse_statement(pages_text, full_text)

    def _parse_statement(self, pages_text: list[str], full_text: str) -> Statement:
        self.statement.account_number = self._extract_account_number(full_text)
        self.statement.account_type = self._extract_account_type(full_text)
        self.statement.statement_period_start, self.statement.statement_period_end = (
            self._extract_period(full_text)
        )
        self.statement.opening_balance, self.statement.closing_balance = self._extract_balances(
            full_text
        )
        self.statement.transactions = self._parse_transactions(pages_text)
        return self.statement

    def _looks_like_credit_card(self, text: str) -> bool:
        return re.search(r"Credit\s+Card\s+Statement", text, re.IGNORECASE) is not None

    def _extract_account_number(self, text: str) -> str | None:
        for pat in ACCOUNT_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_account_type(self, text: str) -> str | None:
        if re.search(r"Credit\s+Card", text, re.IGNORECASE):
            return "Credit Card"
        if re.search(r"Saving\w*\s+Account", text, re.IGNORECASE):
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
        opening_match = re.search(r"\bB/F\s+([\d,]+\.\d{2})", text, re.IGNORECASE)
        if opening_match:
            opening = self.parse_amount(opening_match.group(1))
        total_match = re.search(
            r"^Total:\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        if total_match:
            closing = self.parse_amount(total_match.group(3))
        return opening, closing

    def _parse_transactions(self, pages_text: list[str]) -> list[Transaction]:
        if any(MODERN_HEADER_RE.search(page) for page in pages_text):
            return self._parse_modern(pages_text)
        return self._parse_legacy(pages_text)

    # --- Legacy savings rows ------------------------------------------------

    def _parse_legacy(self, pages_text: list[str]) -> list[Transaction]:
        transactions: list[Transaction] = []
        prev_balance: Decimal | None = None
        for page_text in pages_text:
            header = LEGACY_HEADER_RE.search(page_text)
            lines = page_text[header.end() :].split("\n") if header else page_text.split("\n")
            block: list[str] = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if LEGACY_SUMMARY_RE.match(stripped):
                    txn = self._flush_legacy_block(block, prev_balance)
                    if txn:
                        transactions.append(txn)
                        prev_balance = txn.balance
                    block = []
                    continue
                if OPENING_ROW_RE.match(stripped):
                    opening_match = OPENING_ROW_RE.match(stripped)
                    if opening_match:
                        prev_balance = self.parse_amount(opening_match.group(1))
                    continue
                row_start = LEGACY_ROW_RE.match(stripped)
                if row_start:
                    txn = self._flush_legacy_block(block, prev_balance)
                    if txn:
                        transactions.append(txn)
                        prev_balance = txn.balance
                    block = [stripped]
                elif block:
                    block.append(stripped)
            txn = self._flush_legacy_block(block, prev_balance)
            if txn:
                transactions.append(txn)
        return transactions

    def _flush_legacy_block(
        self, block: list[str], prev_balance: Decimal | None
    ) -> Transaction | None:
        if not block:
            return None
        return self._parse_legacy_block(block, prev_balance)

    def _parse_legacy_block(
        self, block: list[str], prev_balance: Decimal | None
    ) -> Transaction | None:
        row_start = LEGACY_ROW_RE.match(block[0])
        if not row_start:
            return None
        txn_date_dt = self.parse_date(row_start.group(1))
        if txn_date_dt is None:
            return None
        txn_date = txn_date_dt.date()

        amounts_line_idx: int | None = None
        amounts_match = None
        for idx in range(len(block) - 1, -1, -1):
            match = LEGACY_AMOUNTS_RE.search(block[idx])
            if match:
                amounts_line_idx = idx
                amounts_match = match
                break
        if amounts_match is None or amounts_line_idx is None:
            return None

        amount = self.parse_amount(amounts_match.group(1))
        balance = self.parse_amount(amounts_match.group(2))
        if amount is None or balance is None:
            return None

        parts: list[str] = []
        for idx, line in enumerate(block):
            if idx == amounts_line_idx:
                if idx == 0:
                    tail = block[0][row_start.end(1) : amounts_match.start()]
                else:
                    tail = line[: amounts_match.start()]
                tail = tail.strip()
                if tail:
                    parts.append(tail)
                continue
            if idx == 0:
                line = row_start.group(2) or ""
            line = line.strip()
            if line:
                parts.append(line)
        description = self.clean_description(" ".join(parts))

        debit, credit = self._classify_amount(prev_balance, amount, balance, description)
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

    # --- Modern savings rows ------------------------------------------------

    def _parse_modern(self, pages_text: list[str]) -> list[Transaction]:
        transactions: list[Transaction] = []
        prev_balance: Decimal | None = None
        for page_text in pages_text:
            lines = page_text.split("\n")
            i = 0
            while i < len(lines):
                stripped = lines[i].strip()
                i += 1
                if not stripped:
                    continue
                row = MODERN_ROW_RE.match(stripped)
                if not row:
                    continue
                txn_date_dt = self.parse_date(row.group(2))
                amount = self.parse_amount(row.group(3))
                balance = self.parse_amount(row.group(4))
                if txn_date_dt is None or amount is None or balance is None:
                    continue
                narration = (row.group(5) or "").strip()
                while i < len(lines):
                    nxt = lines[i].strip()
                    if not nxt or MODERN_ROW_RE.match(nxt):
                        break
                    narration += " " + nxt
                    i += 1
                description = self.clean_description(narration)

                debit, credit = self._classify_amount(prev_balance, amount, balance, description)
                prev_balance = balance
                if debit is None and credit is None:
                    continue

                transactions.append(
                    Transaction(
                        date=txn_date_dt.date(),
                        description=description,
                        debit=debit,
                        credit=credit,
                        balance=balance,
                        ref_no=self._extract_ref(description),
                        category="credit" if credit else "debit",
                    )
                )
        return transactions

    # --- Shared helpers -----------------------------------------------------

    def _classify_amount(
        self,
        prev_balance: Decimal | None,
        amount: Decimal,
        balance: Decimal,
        description: str,
    ) -> tuple[Decimal | None, Decimal | None]:
        if prev_balance is not None:
            if prev_balance + amount == balance:
                return None, amount
            if prev_balance - amount == balance:
                return amount, None
        if re.search(
            r"\bCredit\s+trxn\b|\bCr\b|REFUND|SALARY|DEPOSIT|INWARD",
            description,
            re.IGNORECASE,
        ):
            return None, amount
        return amount, None

    def _extract_ref(self, description: str) -> str | None:
        match = REF_IN_NARRATION_RE.search(description)
        return match.group(0) if match else None


class ICICICreditCardParser(ICICIParser):
    bank_code = "icici_cc"
    bank_name = "ICICI Bank Credit Card"

    def _parse_statement(self, pages_text: list[str], full_text: str) -> Statement:
        self.statement.account_number = None
        self.statement.account_type = "Credit Card"
        self.statement.statement_period_start, self.statement.statement_period_end = (
            None,
            None,
        )
        self.statement.opening_balance = None
        self.statement.closing_balance = None
        self.statement.transactions = self._parse_transactions(pages_text)
        return self.statement

    def _parse_transactions(self, pages_text: list[str]) -> list[Transaction]:
        transactions: list[Transaction] = []
        for page_text in pages_text:
            for line in page_text.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                row = CC_ROW_RE.match(stripped)
                if not row:
                    continue
                txn_date_dt = self.parse_date(row.group(1))
                amount = self.parse_amount(row.group(5))
                if txn_date_dt is None or amount is None or amount == 0:
                    continue
                description = self.clean_description(row.group(3))
                is_credit = (row.group(6) or "").upper() == "CR"
                transactions.append(
                    Transaction(
                        date=txn_date_dt.date(),
                        description=description,
                        debit=None if is_credit else amount,
                        credit=amount if is_credit else None,
                        balance=Decimal("0"),
                        ref_no=row.group(2),
                        category="credit" if is_credit else "debit",
                    )
                )
        return transactions
