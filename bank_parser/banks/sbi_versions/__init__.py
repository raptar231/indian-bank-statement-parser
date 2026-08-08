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

"""
SBI Versioned Parsers Registry - Base class and registry for versioned SBI statement parsers.
"""

import re
from abc import abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, cast

from bank_parser.banks.base import BaseBankParser
from bank_parser.models import Statement, Transaction


class SBIBaseParser(BaseBankParser):
    """Base class for versioned SBI parsers."""

    version: str = "base"
    year_range: tuple[int, int] = (2010, 2030)  # Default range

    # Patterns that identify this version
    header_patterns: list[str] = []
    identifier_keywords: list[str] = []

    # Column layout for this version
    has_value_date_column: bool = True
    has_cheque_no_column: bool = True
    date_format: str = "%d %b %Y"
    require_header: bool = True  # If False, parser can work without table header

    @classmethod
    def matches(cls, text: str) -> bool:
        """Check if this parser version matches the given text.
        Requires header pattern AND at least 2 identifier keywords (unless require_header=False)."""
        header_match = False
        for pattern in cls.header_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                header_match = True
                break

        if cls.require_header and not header_match:
            return False

        # Check for identifying keywords
        matches = sum(1 for kw in cls.identifier_keywords if kw.lower() in text.lower())
        return matches >= 2  # At least 2 keywords must match

    @classmethod
    def get_year_range(cls) -> tuple[int, int]:
        """Get the year range this parser version supports."""
        return cls.year_range

    def _parse_page_transactions(self, page_text: str) -> list[Transaction]:
        transactions: list[Transaction] = []

        # Try each header pattern
        header_match = None
        for pattern in self.header_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                header_match = match
                break

        if self.require_header and not header_match:
            return transactions

        table_text = page_text[header_match.end() :] if header_match else page_text

        # Remove footer
        footer_patterns = [
            r"Please\s+do\s+not\s+share",
            r"This\s+is\s+a\s+computer\s+generated",
            r"\*\*This\s+is\s+a\s+computer",
        ]
        for fp in footer_patterns:
            match = re.search(fp, table_text, re.IGNORECASE)
            if match:
                table_text = table_text[: match.start()]
                break

        return self._parse_transaction_lines(table_text)

    @abstractmethod
    def _parse_transaction_lines(self, text: str) -> list[Transaction]:
        """Parse transaction lines for this specific version."""
        pass

    def _extract_year(self, text: str, lines: list[str], idx: int) -> int:
        """Extract year from statement text."""
        # Try to find year in nearby lines
        for offset in [-2, -1, 0, 1, 2]:
            check_idx = idx + offset
            if 0 <= check_idx < len(lines):
                line = lines[check_idx]
                year_match = re.search(r"(\d{4})", line)
                if year_match:
                    year = int(year_match.group(1))
                    if 2000 <= year <= 2030:
                        return year

        # Fallback to statement period
        period_match = re.search(
            r"(?:from|from\s+)\s*(\d{1,2}\s+\w{3}\s+(\d{4}))\s+(?:to|-)\s+(\d{1,2}\s+\w{3}\s+(\d{4}))",
            text,
            re.IGNORECASE,
        )
        if period_match:
            return int(period_match.group(2))

        return datetime.now().year

    def _parse_date(self, date_str: str, year: int | None = None) -> datetime | None:
        """Parse date string with various formats."""
        if year is not None and not re.search(r"\d{4}", date_str):
            date_str = f"{date_str} {year}"

        formats = [
            "%d %b %Y",
            "%d-%b-%Y",
            "%d %b %y",
            "%d/%m/%Y",
            "%d/%m/%y",
            "%d-%m-%Y",
            "%d-%m-%y",
            "%d.%m.%Y",
            "%d.%m.%y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
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

    def clean_description(self, desc: str) -> str:
        desc = re.sub(r"\s+", " ", desc).strip()
        desc = re.sub(r"^[-\s:;]+|[-\s:;]+$", "", desc)
        return desc

    def parse(self) -> Statement:
        """Default parse implementation using version-specific transaction parsing."""
        pages_text = self.extract_text()
        full_text = "\n".join(pages_text)

        self.statement.account_number = self._extract_account_number(full_text)
        self.statement.account_type = self._extract_account_type(full_text)
        self.statement.statement_period_start, self.statement.statement_period_end = (
            self.detect_statement_period(full_text)
        )
        self.statement.opening_balance = self._extract_opening_balance(full_text)
        self.statement.closing_balance = self._extract_closing_balance(full_text)

        self.statement.transactions = self._parse_transactions(self.extract_text())

        return self.statement

    def _parse_transactions(self, pages_text: list[str]) -> list[Transaction]:
        transactions: list[Transaction] = []
        for page_text in pages_text:
            transactions.extend(self._parse_page_transactions(page_text))
        return transactions

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


def _statement_year_span(text: str) -> tuple[int, int] | None:
    """Best-effort year span of the statement period from the text."""
    match = re.search(
        r"Account\s+Statement\s+from\s+\d{1,2}\s+\w{3}\s+(\d{4})\s+to\s+"
        r"\d{1,2}\s+\w{3}\s+(\d{4})",
        text,
        re.IGNORECASE,
    )
    if match:
        return int(match.group(1)), int(match.group(2))

    opening = re.search(r"Your\s+Opening\s+Balance\s+on\s+\d{2}-\d{2}-(\d{2})", text)
    closing = re.search(r"Your\s+Closing\s+Balance\s+on\s+\d{2}-\d{2}-(\d{2})", text)
    if opening and closing:
        return 2000 + int(opening.group(1)), 2000 + int(closing.group(1))
    if opening:
        return 2000 + int(opening.group(1)), 2000 + int(opening.group(1))
    if closing:
        return 2000 + int(closing.group(1)), 2000 + int(closing.group(1))
    return None

    as_of = re.search(r"\bAs\s+on\s+\d{2}-\d{2}-(\d{2})", text)
    if as_of:
        year = 2000 + int(as_of.group(1))
        return year, year

    return None


class SBIParserRegistry:
    """Registry for versioned SBI parsers with auto-detection."""

    _parsers: list[type["SBIBaseParser"]] = []
    _initialized = False

    @classmethod
    def _ensure_registered(cls) -> None:
        """Lazily import and register all available parser versions."""
        if cls._initialized:
            return
        from bank_parser.banks.sbi_versions.v2016_a import SBIParser2016A
        from bank_parser.banks.sbi_versions.v2017_b import SBIParser2017B
        from bank_parser.banks.sbi_versions.v2019_c import SBIParser2019C
        from bank_parser.banks.sbi_versions.v2021_d import SBIParser2021D
        from bank_parser.banks.sbi_versions.v2023_e import SBIParser2023E

        for parser_cls in (
            SBIParser2016A,
            SBIParser2017B,
            SBIParser2019C,
            SBIParser2021D,
            SBIParser2023E,
        ):
            cls.register(parser_cls)
        cls._initialized = True

    @classmethod
    def register(cls, parser_class: type["SBIBaseParser"]) -> None:
        """Register a parser version."""
        if parser_class not in cls._parsers:
            cls._parsers.append(parser_class)
            # Sort by year range (newest first)
            cls._parsers.sort(key=lambda p: p.year_range[1], reverse=True)

    @classmethod
    def get_parser_by_version(cls, version: str) -> type["SBIBaseParser"]:
        """Get a registered parser class by version name."""
        cls._ensure_registered()
        for parser_cls in cls._parsers:
            if parser_cls.version == version:
                return parser_cls
        raise ValueError(f"Unknown SBI parser version: {version}")

    @classmethod
    def detect(cls, text: str) -> type["SBIBaseParser"]:
        """Auto-detect the appropriate parser version for the given text."""
        cls._ensure_registered()

        if not cls._parsers:
            # Fallback to the legacy wrapper parser
            from bank_parser.banks.sbi import SBIParser

            return cast(type["SBIBaseParser"], SBIParser)

        span = _statement_year_span(text)

        # 1. The statement period (when known) picks the most specific version.
        if span:
            for parser_cls in cls._parsers:
                start, end = parser_cls.year_range
                if start <= span[0] and span[1] <= end:
                    return parser_cls

        # 2. Content signature, narrowed by the statement year when available.
        matched = [p for p in cls._parsers if p.matches(text)]
        if matched:
            if span:
                for parser_cls in matched:
                    start, end = parser_cls.year_range
                    if start <= span[0] and span[1] <= end:
                        return parser_cls
            return matched[0]

        # 3. Looser fallback: any version whose range covers the statement year.
        if span:
            for parser_cls in cls._parsers:
                start, end = parser_cls.year_range
                if start <= span[0] <= end:
                    return parser_cls

        # Default to latest version
        return cls._parsers[0]

    @classmethod
    def get_all_versions(cls) -> list[dict[str, Any]]:
        """Get info about all registered versions."""
        cls._ensure_registered()
        return [
            {
                "version": p.version,
                "year_range": p.year_range,
                "header_patterns": p.header_patterns,
                "keywords": p.identifier_keywords,
            }
            for p in cls._parsers
        ]


# Export symbols
__all__ = [
    "SBIBaseParser",
    "SBIParserRegistry",
]
