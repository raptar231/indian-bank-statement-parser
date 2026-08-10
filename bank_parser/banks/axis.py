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
Axis Bank statement parsers.

Savings account statements use ``## Tran Date | Chq No | Particulars |
Debit | Credit | Balance | Init.`` tables with ``dd-mm-yyyy`` rows. Because
the debit/credit column that is blank collapses out of the extracted text,
every row shows the transaction amount followed by the running balance and
a trailing branch/init code; the debit/credit sign is recovered from the
running-balance arithmetic against ``## OPENING BALANCE``. Narration that is
too long to fit a row continues on the following lines.

Credit card statements use ``DATE | TRANSACTION DETAILS | MERCHANT CATEGORY |
AMOUNT (Rs.)`` rows with ``dd/mm/yyyy`` dates and a trailing ``Dr``/``Cr``
marker; the statement period lives in the Payment Summary row.
"""

import re
from datetime import date
from decimal import Decimal

from bank_parser.banks.base import BaseBankParser
from bank_parser.models import Statement, Transaction

# --- Savings account layout -------------------------------------------------

# A transaction row starts with a dd-mm-yyyy date; narration follows.
SAVINGS_ROW_RE = re.compile(r"^(\d{2}-\d{2}-\d{4})(?:\s+(.*))?$")

# Summary, header and balance rows start with "##".
AXIS_SUMMARY_RE = re.compile(r"^##", re.IGNORECASE)

# Rows that terminate the transaction section even without the "##" prefix
# (older Axis layouts): the transaction-total row, the closing balance and
# the statement footer. They must never be absorbed as transaction narration.
SECTION_END_RE = re.compile(
    r"^.*?\bTOTAL\b\s+[\d,]+\.\d{2}" r"|^(?:##\s*)?CLOSING\s*BALANCE\b" r"|End\s*of\s*Statement\b",
    re.IGNORECASE,
)

# The opening/closing balance rows seed the running balance for sign recovery.
OPENING_ROW_RE = re.compile(r"^(?:##\s*)?OPENING\s*BALANCE\s+([\d,]+\.\d{2})", re.IGNORECASE)

# Amount + running balance (+ optional trailing init code) at the end of a row.
SAVINGS_AMOUNTS_RE = re.compile(r"([\d,]+\.\d{2})\s+([\d,]+\.\d{2})(?:\s+(\d+))?\s*$")

# --- Credit card layout -----------------------------------------------------

CC_HEADER_RE = re.compile(r"\bDATE\b[^\n]*\bTRANSACTION\s*DETAILS\b", re.IGNORECASE)

# Date | narration | amount | trailing Dr/Cr marker.
CC_ROW_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s+(Dr|Cr)\s*$", re.IGNORECASE
)

# --- Shared helpers ---------------------------------------------------------

PERIOD_RE = re.compile(r"From\s*:\s*(\d{2}-\d{2}-\d{4})\s*To\s*:\s*(\d{2}-\d{2}-\d{4})")

PERIOD_RANGE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})")

# Narration-embedded references: a "Ref#" tag, a "NEFT/UTR" token, or a
# 12+ digit run with an optional single-letter prefix.
REF_PATTERNS = [
    r"Ref#\s*(\S+)",
    r"NEFT/([A-Z0-9]+)",
    r"[A-Z]?\d{12,}",
]

ACCOUNT_PATTERNS = [
    r"Account\s*(?:Number|No\.?)\s*:?\s*(\d{15})",
    r"A/c\s*No[.:]\s*(\d{15})",
    r"(\d{15})",
]


class AxisParser(BaseBankParser):
    bank_code = "axis"
    bank_name = "Axis Bank"

    def parse(self) -> Statement:
        pages_text = self.extract_text()
        full_text = "\n".join(pages_text)
        if self._looks_like_credit_card(full_text):
            cc_parser = AxisCreditCardParser(self.pdf_path, password=self.password)
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
        return re.search(r"Credit\s+Card", text, re.IGNORECASE) is not None

    def _extract_account_number(self, text: str) -> str | None:
        for pat in ACCOUNT_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_account_type(self, text: str) -> str | None:
        lowered = text.lower()
        if "credit card" in lowered:
            return "Credit Card"
        if "saving" in lowered:
            return "Savings"
        if "current" in lowered:
            return "Current"
        return None

    def _extract_period(self, text: str) -> tuple[date | None, date | None]:
        for pat in (PERIOD_RE, PERIOD_RANGE_RE):
            match = pat.search(text)
            if not match:
                continue
            start = self.parse_date(match.group(1))
            end = self.parse_date(match.group(2))
            if start and end:
                return start.date(), end.date()
        return None, None

    def _extract_balances(self, text: str) -> tuple[Decimal | None, Decimal | None]:
        opening = None
        closing = None
        opening_match = re.search(
            r"(?:##\s*)?OPENING\s*BALANCE\s+([\d,]+\.\d{2})", text, re.IGNORECASE
        )
        if opening_match:
            opening = self.parse_amount(opening_match.group(1))
        closing_match = re.search(
            r"(?:##\s*)?CLOSING\s*BALANCE\s+([\d,]+\.\d{2})", text, re.IGNORECASE
        )
        if closing_match:
            closing = self.parse_amount(closing_match.group(1))
        return opening, closing

    def _parse_transactions(self, pages_text: list[str]) -> list[Transaction]:
        transactions: list[Transaction] = []
        prev_balance: Decimal | None = None
        # Buffer for narration lines that appear BEFORE their date line
        pending_narration: list[str] = []
        for page_text in pages_text:
            block: list[str] = []
            for line in page_text.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                opening_match = OPENING_ROW_RE.match(stripped)
                if opening_match:
                    prev_balance = self.parse_amount(opening_match.group(1))
                    continue
                if AXIS_SUMMARY_RE.match(stripped) or SECTION_END_RE.search(stripped):
                    if pending_narration:
                        block.extend(pending_narration)
                        pending_narration = []
                    txn = self._flush_block(block, prev_balance)
                    if txn:
                        transactions.append(txn)
                        prev_balance = txn.balance
                    block = []
                    continue
                row_start = SAVINGS_ROW_RE.match(stripped)
                if row_start:
                    # Flush previous block
                    txn = self._flush_block(block, prev_balance)
                    if txn:
                        transactions.append(txn)
                        prev_balance = txn.balance
                    # Start new block with date line
                    block = [stripped]
                    # Add any pending narration AFTER the date line
                    if pending_narration:
                        block.extend(pending_narration)
                        pending_narration = []
                elif self._looks_like_pending_narration(stripped):
                    # If we're in the middle of a transaction (block non-empty),
                    # this is a continuation of the current transaction.
                    # If block is empty (between transactions), it's pending for next.
                    if block:
                        block.append(stripped)
                    else:
                        pending_narration.append(stripped)
                elif block:
                    block.append(stripped)
            # End of page
            if pending_narration:
                block.extend(pending_narration)
                pending_narration = []
            txn = self._flush_block(block, prev_balance)
            if txn:
                transactions.append(txn)
        return transactions

    def _looks_like_pending_narration(self, line: str) -> bool:
        """Check if a line looks like a narration for the NEXT transaction.
        These are lines without a date that describe the following transaction.
        Common patterns: 'Int.Pd:...', 'Interest paid...', 'to 31-', 'to 30-', etc."""
        if not line:
            return False
        # Skip lines that look like they belong to current transaction (continuation)
        if re.match(r"^(?:UPI|NEFT|IMPS|ACH|RTGS|NACH|ECS|ATM|POS|CHQ)", line, re.IGNORECASE):
            return False
        # Lines that look like interest/narration for NEXT period
        patterns = [
            r"Int\.?\s*P[da]\b",  # Int.Pd, Int Paid, Interest Paid
            r"Interest\s+(?:Paid|Received|Credit)",
            r"to\s+\d{1,2}\s*-",  # "to 31-", "to 30-"
            r"for\s+period\b",
            r"SB[:]\s*\w+",  # "SB:XXXXXXXXXXXXXXX:..."
        ]
        return any(re.search(pat, line, re.IGNORECASE) for pat in patterns)

    def _flush_block(self, block: list[str], prev_balance: Decimal | None) -> Transaction | None:
        if not block:
            return None
        return self._parse_savings_block(block, prev_balance)

    def _parse_savings_block(
        self, block: list[str], prev_balance: Decimal | None
    ) -> Transaction | None:
        row_start = SAVINGS_ROW_RE.match(block[0])
        if not row_start:
            return None
        txn_date_dt = self.parse_date(row_start.group(1))
        if txn_date_dt is None:
            return None
        txn_date = txn_date_dt.date()

        amounts_line_idx: int | None = None
        amounts_match = None
        for idx in range(len(block) - 1, -1, -1):
            match = SAVINGS_AMOUNTS_RE.search(block[idx])
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
            if balance < prev_balance:
                return amount, None
            if balance > prev_balance:
                return None, amount
        if re.search(r"\bCr\b|REFUND|SALARY|DEPOSIT|INWARD", description, re.IGNORECASE):
            return None, amount
        return amount, None

    def _extract_ref(self, description: str) -> str | None:
        for pat in REF_PATTERNS:
            match = re.search(pat, description, re.IGNORECASE)
            if match:
                return match.group(1) if match.lastindex else match.group(0)
        return None


class AxisCreditCardParser(AxisParser):
    bank_code = "axis_cc"
    bank_name = "Axis Bank Credit Card"

    def _parse_statement(self, pages_text: list[str], full_text: str) -> Statement:
        self.statement.account_number = self._extract_cc_account_number(full_text)
        self.statement.account_type = "Credit Card"
        self.statement.statement_period_start, self.statement.statement_period_end = (
            self._extract_period(full_text)
        )
        self.statement.opening_balance = None
        self.statement.closing_balance = None
        self.statement.transactions = self._parse_transactions(pages_text)
        return self.statement

    def _extract_cc_account_number(self, text: str) -> str | None:
        match = re.search(r"Card\s*No\.?\s*:?\s*(\S+)", text, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_ref(self, description: str) -> str | None:
        match = re.search(r"Ref#\s*(\S+)", description, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r"BBPS\s+PAYMENT\s+RECEIVED\s*-\s*(\S+)", description, re.IGNORECASE)
        if match:
            return match.group(1)
        return super()._extract_ref(description)

    def _parse_transactions(self, pages_text: list[str]) -> list[Transaction]:
        transactions: list[Transaction] = []
        for page_text in pages_text:
            header = CC_HEADER_RE.search(page_text)
            lines = page_text[header.end() :].split("\n") if header else page_text.split("\n")
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                row = CC_ROW_RE.match(stripped)
                if not row:
                    continue
                txn_date_dt = self.parse_date(row.group(1))
                amount = self.parse_amount(row.group(3))
                if txn_date_dt is None or amount is None or amount == 0:
                    continue
                description = self.clean_description(row.group(2))
                is_credit = row.group(4).upper() == "CR"
                transactions.append(
                    Transaction(
                        date=txn_date_dt.date(),
                        description=description,
                        debit=None if is_credit else amount,
                        credit=amount if is_credit else None,
                        balance=Decimal("0"),
                        ref_no=self._extract_ref(description),
                        category="credit" if is_credit else "debit",
                    )
                )
        return transactions
