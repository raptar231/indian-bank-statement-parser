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

import re
from datetime import date, datetime
from decimal import Decimal

from bank_parser.banks.base import BaseBankParser
from bank_parser.banks.sbi_versions import SBIBaseParser, SBIParserRegistry
from bank_parser.models import Statement, Transaction

# --- SBI credit card layout -------------------------------------------------

# The transaction table starts on a header line that names both columns.
CC_HEADER_RE = re.compile(r"\bDATE\b[^\n]*\bAMOUNT\b", re.IGNORECASE)

# Date | narration | amount | optional "Cr" marker for refunds/payments.
# Credits are printed either with the trailing marker or as a negative amount.
CC_ROW_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?[\d,]+\.\d{2})\s*(?:CR\.?)?\s*$",
    re.IGNORECASE,
)

CC_PERIOD_RE = re.compile(
    r"Statement\s+Period\s*[:\s]*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)

CC_CARD_NO_RE = re.compile(r"Card\s*(?:No|Number)\.?\s*:?\s*([0-9X*\s]{12,})", re.IGNORECASE)

CC_FOOTER_RE = re.compile(r"^(?:End\s+of\s+Statement|This\s+is\s+a\s+computer)", re.IGNORECASE)


class SBIParser(BaseBankParser):
    """SBI Parser with auto-detection of statement format version."""

    bank_code = "sbi"
    bank_name = "State Bank of India"

    def __init__(self, pdf_path: str, version: str | None = None):
        super().__init__(pdf_path)
        self._parser: SBIBaseParser | None = None
        self._version = version

    def _get_parser(self) -> SBIBaseParser:
        if self._parser is None:
            if self._version:
                # Use specific version
                self._parser = SBIParserRegistry.get_parser_by_version(self._version)(self.pdf_path)
            else:
                # Auto-detect
                pages_text = self.extract_text()
                full_text = "\n".join(pages_text)
                parser_cls = SBIParserRegistry.detect(full_text)
                self._parser = parser_cls(self.pdf_path)
        assert self._parser is not None
        return self._parser

    @staticmethod
    def _looks_like_credit_card(text: str) -> bool:
        """Check if text appears to be an SBI credit card statement."""
        credit_card_markers = [
            r"Credit\s+Card\s+Statement",
            r"Card\s+No\.?\s*:",
            r"Statement\s+Period\s+\d{2}/\d{2}/\d{4}\s*-\s*\d{2}/\d{2}/\d{4}",
            r"Total\s+Amount\s+Due",
            r"Minimum\s+Amount\s+Due",
            r"Payment\s+Due\s+Date",
            r"Credit\s+Limit",
            r"Available\s+Credit",
        ]
        return any(re.search(marker, text, re.IGNORECASE) for marker in credit_card_markers)

    def parse(self) -> Statement:
        pages_text = self.extract_text()
        full_text = "\n".join(pages_text)

        # Auto-detect credit card vs savings
        if self._looks_like_credit_card(full_text):
            cc_parser = SBICreditCardParser(self.pdf_path)
            return cc_parser._parse_statement(pages_text, full_text)

        parser = self._get_parser()

        self.statement.account_number = parser._extract_account_number(full_text)
        self.statement.account_type = parser._extract_account_type(full_text)
        self.statement.statement_period_start, self.statement.statement_period_end = (
            parser.detect_statement_period(full_text)
        )
        self.statement.opening_balance = parser._extract_opening_balance(full_text)
        self.statement.closing_balance = parser._extract_closing_balance(full_text)

        # Use already-extracted pages_text instead of re-extracting
        self.statement.transactions = parser._parse_transactions(pages_text)

        return self.statement

    def _extract_account_number(self, text: str) -> str | None:
        patterns = [
            r"Account\s*Number[:\s]+(\d{11,})",
            r"A/c\s*No[.:]\s*(\d{11,})",
            r"(\d{11})",
        ]
        for pat in patterns:
            match = re.search(pat, text)
            if match:
                return match.group(1)
        return None

    def _extract_account_type(self, text: str) -> str | None:
        if "Savings" in text or "SAVINGS" in text:
            return "Savings"
        if "Current" in text or "CURRENT" in text:
            return "Current"
        # Fallback: if it has account statement header, assume Savings
        if re.search(r"Account\s+Statement", text, re.IGNORECASE):
            return "Savings"
        return None

    def _extract_opening_balance(self, text: str) -> Decimal | None:
        patterns = [
            r"Opening\s*Balance[:\s]+([\d,]+\.?\d*)",
            r"B/F[:\s]+([\d,]+\.?\d*)",
            r"Balance\s+as\s+on\s+\d{1,2}\s+\w{3}\s+\d{4}\s*:\s*([\d,]+\.?\d*)",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return self.parse_amount(match.group(1))
        return None

    def _extract_closing_balance(self, text: str) -> Decimal | None:
        patterns = [
            r"Closing\s*Balance[:\s]+([\d,]+\.?\d*)",
            r"C/F[:\s]+([\d,]+\.?\d*)",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return self.parse_amount(match.group(1))
        return None

    def parse_amount(self, amount_str: str) -> Decimal | None:
        if not amount_str:
            return None
        cleaned = amount_str.replace(",", "").replace(" ", "").strip()
        if cleaned in ("", "-", "0.00", "0"):
            return None
        try:
            return Decimal(cleaned)
        except Exception:
            return None

    def parse_date(self, date_str: str) -> datetime | None:
        formats = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d.%m.%Y",
            "%d/%m/%y",
            "%d-%m-%y",
            "%d.%m.%y",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d %b %Y",
            "%d %B %Y",
            "%b %d, %Y",
            "%B %d, %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None


class SBICreditCardParser(SBIParser):
    bank_code = "sbi_cc"
    bank_name = "SBI Credit Card"

    def parse(self) -> Statement:
        pages_text = self.extract_text()
        full_text = "\n".join(pages_text)
        return self._parse_statement(pages_text, full_text)

    def _parse_statement(self, pages_text: list[str], full_text: str) -> Statement:
        self.statement.account_number = self._extract_cc_account_number(full_text)
        self.statement.account_type = "Credit Card"
        self.statement.statement_period_start, self.statement.statement_period_end = (
            self._extract_cc_period(full_text)
        )
        self.statement.opening_balance = None
        self.statement.closing_balance = None
        self.statement.transactions = self._parse_transactions(pages_text)
        return self.statement

    def _extract_cc_account_number(self, text: str) -> str | None:
        match = CC_CARD_NO_RE.search(text)
        if not match:
            return None
        return " ".join(match.group(1).split())

    def _extract_cc_period(self, text: str) -> tuple[date | None, date | None]:
        match = CC_PERIOD_RE.search(text)
        if not match:
            return None, None
        start = self.parse_date(match.group(1))
        end = self.parse_date(match.group(2))
        if start and end:
            return start.date(), end.date()
        return None, None

    def _parse_transactions(self, pages_text: list[str]) -> list[Transaction]:
        transactions: list[Transaction] = []
        for page_text in pages_text:
            header = CC_HEADER_RE.search(page_text)
            lines = page_text[header.end() :].split("\n") if header else page_text.split("\n")
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if CC_FOOTER_RE.match(stripped):
                    break
                row = CC_ROW_RE.match(stripped)
                if not row:
                    continue
                txn_date_dt = self.parse_date(row.group(1))
                amount = self.parse_amount(row.group(3))
                if txn_date_dt is None or amount is None:
                    continue
                # Credits print as a negative amount or with a trailing "Cr" marker.
                is_credit = amount < 0 or (
                    re.search(r"\bCR\.?$", stripped, re.IGNORECASE) is not None
                )
                if is_credit and amount < 0:
                    amount = -amount
                if amount == 0:
                    continue
                description = self.clean_description(row.group(2))
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

    def _extract_ref(self, description: str) -> str | None:
        match = re.search(r"REF(?:\s|#)*\s*([A-Z0-9]{4,})", description, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r"UPI[:\s/]*(\d{10,})", description, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r"[A-Z]?\d{12,}", description)
        if match:
            return match.group(0)
        return None
