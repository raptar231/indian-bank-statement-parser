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
Shared parsing engine for the SBI netbanking statement family (2016-2023+).

The netbanking PDF table has kept the same column layout for years:

    Txn Date  Value  Description  Ref No./Cheque  Debit  Credit  Balance

Dates are ``dd MMM`` and the transaction year is printed on a separate
line as ``2016 2016`` below the two date columns. Depending on how the
PDF was text-extracted, the year may instead appear inline (``1 Nov 2017``)
or glued at the end of a row (``... 295.00 1,454.52 / 2017 2017 ...``).

This engine handles all three placements plus:
- two or three trailing amount slots (empty columns shown as ``-``/``0.00``)
- reference numbers on continuation lines (``IMPS/P2A/...``, ``NEFT*...``,
  UTRs like ``JSBI5800496343I`` or ``szyrfG8E9BEfdEy``)
- an inline numeric reference between the description and the amounts
  (e.g. ``ATM WDL-ATM CASH 5815 500.00 41,696.52``)
"""

import re

from bank_parser.banks.sbi_versions import SBIBaseParser
from bank_parser.models import Transaction


class SBIStandardParser(SBIBaseParser):
    """Shared engine for SBI netbanking 'standard' statements."""

    version = "standard"
    year_range = (2016, 2026)

    header_patterns = [
        r"Txn\s+Date\s+Value\s+Date\s+Description\s+Ref\s+No\./Cheque\s+No\.\s+Debit\s+Credit\s+Balance",
        r"Txn\s+Date\s+Value\s+Description\s+Ref\s+No\./Cheque\s+No\.\s+Debit\s+Credit\s+Balance",
        r"Txn\s+Date\s+Value\s+Description\s+Ref\s+No\./Cheque\s+Debit\s+Credit\s+Balance",
    ]

    identifier_keywords = [
        "Txn Date",
        "Value Date",
        "Ref No./Cheque No.",
        "Debit Credit Balance",
        "STATE BANK OF INDIA",
        "REGULAR SB CHQ",
    ]

    row_start_re = re.compile(
        r"^(\d{1,2}\s+[A-Za-z]{3}(?:\s+(\d{4}))?)"
        r"(?:\s+\d{1,2}\s+[A-Za-z]{3}(?:\s+\d{4})?)?\s*(.*)$"
    )
    year_line_re = re.compile(r"^(\d{4})\s+(\d{4})\s*(.*)")
    glued_year_re = re.compile(r"/\s*(\d{4})\s+(\d{4})\s*")
    amounts_re = re.compile(
        r"((?<!\w)-|[\d,]+\.\d{2})\s+" r"((?<!\w)-|[\d,]+\.\d{2})(?:\s+((?<!\w)-|[\d,]+\.\d{2}))?"
    )
    ref_re = re.compile(
        r"(?:UTR|Ref|Chq|Cheque|IMPS|P2A|NEFT)\s*(?:No|#)?[:\s/]+([\w/.*-]+)",
        re.IGNORECASE,
    )
    utr_re = re.compile(r"\b(?:[A-Z]{2,4}\d{8,}[A-Za-z0-9]*|NEFT\*[A-Z0-9*]+|[A-Za-z0-9]{12,})\b")
    inline_ref_re = re.compile(r"(\d{3,6})$")

    def _is_credit(self, desc: str) -> bool:
        """Heuristically classify a two-column (amount, balance) row."""
        d = desc.upper()
        if d.startswith("TO"):
            return False
        # Explicit DEBIT at start = debit
        if d.startswith("DEBIT"):
            return False
        if re.search(r"TRANSFER[- ]?INB", d):
            return True
        if any(
            kw in d
            for kw in ("CREDIT", "DEPOSIT", "SALARY", "INTEREST", "REFUND", "INWARD", "ACHC")
        ):
            return True
        if d.endswith("CR"):
            return True
        # Only specific "BY" patterns are credits, not "by debit card" etc.
        if re.search(r"^BY\s+(TRANSFER|CLEARING|CASH|CHEQUE|NEFT|RTGS|IMPS|UPI)", d):
            return True
        return False

    def _extract_ref_no(self, line: str) -> str | None:
        match = self.ref_re.search(line)
        if match:
            return match.group(1)
        match = self.utr_re.search(line)
        if match:
            return match.group(0)
        return None

    def _parse_transaction_lines(self, text: str) -> list[Transaction]:
        transactions: list[Transaction] = []
        lines = text.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            row_match = self.row_start_re.match(line)
            if not row_match:
                i += 1
                continue

            date_str = row_match.group(1).strip()
            inline_year_str = row_match.group(2)
            rest = row_match.group(3).strip()

            # Strip a glued "/ yyyy yyyy ..." year-line tail (extraction artifact).
            tail_desc = ""
            glued_year = None
            glued_match = self.glued_year_re.search(rest)
            if glued_match:
                glued_year = int(glued_match.group(1))
                tail_desc = rest[glued_match.end() :].strip()
                rest = rest[: glued_match.start()].strip()

            # Amounts are the last two/three amount-looking tokens on the row.
            amount_matches = list(self.amounts_re.finditer(rest))
            amounts = None
            inline_ref = None
            if amount_matches:
                last = amount_matches[-1]
                amounts = last.groups()
                desc_before = rest[: last.start()].strip()
                desc_after = rest[last.end() :].strip()
                ref_match = self.inline_ref_re.search(desc_before)
                if ref_match:
                    inline_ref = ref_match.group(1)
                    desc_before = desc_before[: ref_match.start()].strip()
                desc = " ".join(p for p in (desc_before, desc_after, tail_desc) if p)
            else:
                desc = " ".join(p for p in (rest, tail_desc) if p)

            # Resolve the transaction year.
            year = None
            if inline_year_str:
                year = int(inline_year_str)
            elif glued_year:
                year = glued_year
            elif i + 1 < len(lines):
                year_match = self.year_line_re.match(lines[i + 1].strip())
                if year_match:
                    year = int(year_match.group(1))
                    year_desc = year_match.group(3).strip()
                    if year_desc:
                        desc = f"{desc} {year_desc}".strip()
                    i += 1
            if year is None:
                year = self._extract_year(text, lines, i)

            txn_date = self._parse_date(date_str, year)
            if txn_date is None:
                i += 1
                continue

            # Scan continuation lines for a reference number and advance past them.
            ref_no = inline_ref
            if ref_no is None:
                ref_no = self._extract_ref_no(desc)
            j = i + 1
            while j < len(lines) and ref_no is None:
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue
                if self.row_start_re.match(next_line) or self.year_line_re.match(next_line):
                    break
                ref_no = self._extract_ref_no(next_line)
                j += 1
            i = j

            if amounts is None or len(amounts) < 2:
                continue

            if amounts[2] is not None:
                # Three slots: Debit Credit Balance.
                # Handle empty columns marked as "-"
                slot0 = amounts[0].strip() if amounts[0] else ""
                slot1 = amounts[1].strip() if amounts[1] else ""

                # Check if description explicitly indicates debit/credit
                desc_upper = desc.upper()
                explicit_debit = desc_upper.startswith("DEBIT")
                explicit_credit = (
                    any(
                        kw in desc_upper
                        for kw in (
                            "CREDIT",
                            "DEPOSIT",
                            "SALARY",
                            "INTEREST",
                            "REFUND",
                            "INWARD",
                            "ACHC",
                        )
                    )
                    or re.search(
                        r"^BY\s+(TRANSFER|CLEARING|CASH|CHEQUE|NEFT|RTGS|IMPS|UPI)", desc_upper
                    )
                    or re.search(r"TRANSFER[- ]?INB", desc_upper)
                )

                if slot0 == "-" and slot1 != "-":
                    # Debit column empty, credit column has value
                    if explicit_debit:
                        # Description says debit but amount in credit column -> it's a debit
                        debit = self.parse_amount(amounts[1])
                        credit = None
                    else:
                        debit = None
                        credit = self.parse_amount(amounts[1])
                elif slot1 == "-" and slot0 != "-":
                    # Credit column empty, debit column has value
                    if explicit_credit:
                        # Description says credit but amount in debit column -> it's a credit
                        credit = self.parse_amount(amounts[0])
                        debit = None
                    else:
                        debit = self.parse_amount(amounts[0])
                        credit = None
                else:
                    # Both present or both empty - use both, but respect explicit indicators
                    if explicit_debit and not explicit_credit:
                        debit = self.parse_amount(amounts[0]) or self.parse_amount(amounts[1])
                        credit = None
                    elif explicit_credit and not explicit_debit:
                        credit = self.parse_amount(amounts[1]) or self.parse_amount(amounts[0])
                        debit = None
                    else:
                        debit = self.parse_amount(amounts[0])
                        credit = self.parse_amount(amounts[1])
                balance = self.parse_amount(amounts[2])
            else:
                # Two slots: Amount Balance (one of debit/credit is blank).
                amount = self.parse_amount(amounts[0])
                balance = self.parse_amount(amounts[1])
                if self._is_credit(desc):
                    credit, debit = amount, None
                else:
                    debit, credit = amount, None

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
