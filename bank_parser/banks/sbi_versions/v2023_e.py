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

"""
SBI Parser Version 2023E (2023+ format)

Dispatches between two statement families used in this era:

1. Netbanking statements - same table as the earlier versions (handled by
   the shared ``SBIStandardParser`` engine).

2. YONO "E-account statement" PDFs. These have a ``TRANSACTION DETAILS``
   section per account with a masked account number (``XXXXXXX0000``) and
   rows in the layout::

       Date  Transaction Reference  Ref.No./Chq.No.  Credit  Debit  Balance
       04-12-25
       APY_DEC25_Mont_1000_99999999999999999_999999999999
       - - 90.00 236.21
       25-12-25 INTEREST CREDIT - 3.00 - 239.21

   Dates are ``dd-mm-yy`` and every amount column uses ``-`` for empty.
"""

import re
from datetime import date, datetime
from decimal import Decimal

from bank_parser.banks.sbi_versions.sbi_standard import SBIStandardParser
from bank_parser.models import Transaction

_YONO_MARKER = re.compile(r"TRANSACTION\s+DETAILS", re.IGNORECASE)
_YONO_HEADER = re.compile(r"^Date\s+Transaction\s+Reference", re.IGNORECASE)
_YONO_DATE = re.compile(r"^(\d{2}-\d{2}-\d{2})\b")
_YONO_AMOUNTS = re.compile(
    r"(-|[\d,]+\.\d{2})\s+(-|[\d,]+\.\d{2})\s+(-|[\d,]+\.\d{2})\s+(-|[\d,]+\.\d{2})\s*$"
)


class SBIParser2023E(SBIStandardParser):
    """SBI Parser for 2023+ formats (netbanking + YONO e-statement)."""

    version = "2023E"
    year_range = (2023, 2026)

    header_patterns = [
        r"Txn\s+Date\s+Value\s+Date\s+Description\s+Ref\s+No\./Cheque\s+No\.\s+Debit\s+Credit\s+Balance",
        r"Txn\s+Date\s+Value\s+Description\s+Ref\s+No\./Cheque\s+No\.\s+Debit\s+Credit\s+Balance",
        r"Txn\s+Date\s+Value\s+Description\s+Ref\s+No\./Cheque\s+Debit\s+Credit\s+Balance",
        r"TRANSACTION\s+DETAILS",
    ]

    identifier_keywords = [
        "Txn Date",
        "Value Date",
        "Debit Credit Balance",
        "REGULAR SB CHQ",
        "STATE BANK OF INDIA",
        "TRANSACTION DETAILS",
        "Welcome",
        "As on",
        "Available Balance",
        "Multi-Option Deposit",
        "Your Closing Balance",
        "DD-MM-YY",
    ]

    has_value_date_column = True
    has_cheque_no_column = True

    def _is_yono(self, text: str) -> bool:
        return _YONO_MARKER.search(text) is not None

    def _parse_yono_date(self, date_str: str) -> datetime | None:
        try:
            return datetime.strptime(date_str, "%d-%m-%y")
        except ValueError:
            return None

    def _parse_transactions(self, pages_text: list[str]) -> list[Transaction]:
        if any(self._is_yono(page) for page in pages_text):
            return self._parse_yono_transactions(pages_text)
        return super()._parse_transactions(pages_text)

    def _parse_yono_transactions(self, pages_text: list[str]) -> list[Transaction]:
        transactions: list[Transaction] = []
        for page_text in pages_text:
            matches = list(_YONO_MARKER.finditer(page_text))
            if not matches:
                continue
            # Every page's navbar contains an adjacent "Transaction\nDetails"
            # that matches the marker too, so the real section header is the
            # last match on the page.
            match = matches[-1]
            section = page_text[match.end() :]
            for marker in (
                "*All dates are in DD-MM-YY",
                "TRANSACTION OVERVIEW",
                "Contents of this statement",
                "Visit https://sbi.co.in",
            ):
                cut = section.find(marker)
                if cut != -1:
                    section = section[:cut]
                    break
            first_line = section.lstrip().split("\n", 1)[0].strip()
            if not re.search(r"\bSAVING", first_line, re.IGNORECASE):
                continue
            transactions.extend(self._parse_yono_section(section))
        return transactions

    def _parse_yono_section(self, text: str) -> list[Transaction]:
        lines = text.split("\n")
        header_idx = None
        for idx, line in enumerate(lines):
            if _YONO_HEADER.match(line.strip()):
                header_idx = idx
                break
        if header_idx is None:
            return []

        transactions: list[Transaction] = []
        i = header_idx + 1
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            date_match = _YONO_DATE.match(line)
            if not date_match:
                i += 1
                continue

            date_str = date_match.group(1)
            txn_date = self._parse_yono_date(date_str)
            if txn_date is None:
                i += 1
                continue

            rest = line[date_match.end() :].strip()
            amount_match = _YONO_AMOUNTS.search(rest)

            if amount_match:
                desc = rest[: amount_match.start()].strip()
            else:
                desc_parts = [rest] if rest else []
                j = i + 1
                amount_match = None
                while j < len(lines):
                    next_line = lines[j].strip()
                    if not next_line:
                        j += 1
                        continue
                    amount_match = _YONO_AMOUNTS.search(next_line)
                    if amount_match:
                        desc_parts.append(next_line[: amount_match.start()].strip())
                        break
                    if _YONO_DATE.match(next_line):
                        break
                    desc_parts.append(next_line)
                    j += 1
                if amount_match is None:
                    i = j
                    continue
                i = j
                desc = " ".join(p for p in desc_parts if p)

            i += 1

            ref_str, credit_str, debit_str, balance_str = amount_match.groups()
            ref_no = None if ref_str in ("", "-") else ref_str
            credit = self.parse_amount(credit_str)
            debit = self.parse_amount(debit_str)
            balance = self.parse_amount(balance_str)

            if balance is None or (debit is None and credit is None):
                continue

            transactions.append(
                Transaction(
                    date=txn_date.date(),
                    description=self.clean_description(desc),
                    debit=debit,
                    credit=credit,
                    balance=balance,
                    ref_no=ref_no,
                    category="credit" if credit else "debit",
                )
            )

        return transactions

    def _extract_account_number(self, text: str) -> str | None:
        if self._is_yono(text):
            match = re.search(r"^[X*\d]{11}$", text, re.MULTILINE)
            if match:
                return match.group(0)
        return super()._extract_account_number(text)

    def _extract_account_type(self, text: str) -> str | None:
        if self._is_yono(text):
            if re.search(r"\bSAVING(S)?\s+ACCOUNT\b", text):
                return "Savings"
            if re.search(r"DL/TL\s+ACCOUNT", text):
                return "Loan"
        return super()._extract_account_type(text)

    def _extract_opening_balance(self, text: str) -> Decimal | None:
        if self._is_yono(text):
            matches = re.findall(
                r"Your\s+Opening\s+Balance\s+on\s+\d{2}-\d{2}-\d{2}\s*:\s*([\d,]+\.\d{2})",
                text,
            )
            if matches:
                return self.parse_amount(matches[-1])
        return super()._extract_opening_balance(text)

    def _extract_closing_balance(self, text: str) -> Decimal | None:
        if self._is_yono(text):
            matches = re.findall(
                r"Your\s+Closing\s+Balance\s+on\s+\d{2}-\d{2}-\d{2}\s*:\s*([\d,]+\.\d{2})",
                text,
            )
            if matches:
                return self.parse_amount(matches[-1])
            balance_matches = re.findall(r"Available\s+Balance\s+([\d,]+\.\d{2})", text)
            if balance_matches:
                return self.parse_amount(balance_matches[-1])
        return super()._extract_closing_balance(text)

    def detect_statement_period(self, text: str) -> tuple[date | None, date | None]:
        if self._is_yono(text):
            start_matches = re.findall(r"Your\s+Opening\s+Balance\s+on\s+(\d{2}-\d{2}-\d{2})", text)
            end_matches = re.findall(r"Your\s+Closing\s+Balance\s+on\s+(\d{2}-\d{2}-\d{2})", text)
            start = self._parse_yono_date(start_matches[-1]) if start_matches else None
            end = self._parse_yono_date(end_matches[-1]) if end_matches else None
            if start and end:
                return start.date(), end.date()
            as_of_matches = re.findall(r"\bAs\s+on\s+(\d{2}-\d{2}-\d{2})", text)
            if as_of_matches:
                parsed = self._parse_yono_date(as_of_matches[-1])
                if parsed:
                    return parsed.date(), parsed.date()
        return super().detect_statement_period(text)
