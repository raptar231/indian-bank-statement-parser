<!--
  ~ Copyright 2024-2026 Koushik Mondal (github.com/raptar231)
  ~
  ~ Licensed under the Apache License, Version 2.0 (the "License");
  ~ you may not use this file except in compliance with the License.
  ~ You may obtain a copy of the License at
  ~
  ~     http://www.apache.org/licenses/LICENSE-2.0
  ~
  ~ Unless required by applicable law or agreed to in writing, software
  ~ distributed under the License is distributed on an "AS IS" BASIS,
  ~ WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  ~ See the License for the specific language governing permissions and
  ~ limitations under the License.
-->

# Adding a Bank Parser

Step-by-step guide to add a new bank parser in ~50 lines.

## 1. Create Parser File

Create `bank_parser/banks/yourbank.py`:

```python

# you may not use this file except in compliance with the License.
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# limitations under the License.

import re
from decimal import Decimal
from typing import list, Optional

from bank_parser.banks.base import BaseBankParser
from bank_parser.models import Statement, Transaction


class YourBankParser(BaseBankParser):
    bank_code = "yourbank"
    bank_name = "Your Bank Name"

    def parse(self) -> Statement:
        pages_text = self.extract_text()
        full_text = "\n".join(pages_text)

        # Extract account info
        self.statement.account_number = self._extract_account_number(full_text)
        self.statement.account_type = self._extract_account_type(full_text)
        self.statement.statement_period_start, self.statement.statement_period_end = (
            self.detect_statement_period(full_text)
        )

        # Parse transactions
        self.statement.transactions = self._parse_transactions(pages_text)

        return self.statement

    def _extract_account_number(self, text: str) -> Optional[str]:
        # Add regex for your bank's account number format
        patterns = [
            r"Account\s*Number[:\s]+(\d{12,})",
            r"A/c\s*No[.:]\s*(\d{12,})",
        ]
        for pat in patterns:
            match = re.search(pat, text)
            if match:
                return match.group(1)
        return None

    def _extract_account_type(self, text: str) -> Optional[str]:
        if "Savings" in text:
            return "Savings"
        if "Current" in text:
            return "Current"
        if "Credit Card" in text:
            return "Credit Card"
        return None

    def _parse_transactions(self, pages_text: list[str]) -> list[Transaction]:
        transactions = []

        for page_text in pages_text:
            for line in page_text.split("\n"):
                txn = self._parse_transaction_line(line)
                if txn:
                    transactions.append(txn)

        return transactions

    def _parse_transaction_line(self, line: str) -> Optional[Transaction]:
        line = line.strip()
        if not line:
            return None

        # Match date at start of line
        date_match = re.match(r"^(\d{2}/\d{2}/\d{4})", line)
        if not date_match:
            return None

        date_str = date_match.group(1)
        txn_date = self.parse_date(date_str)
        if not txn_date:
            return None

        remaining = line[date_match.end():].strip()

        # Define regex patterns for your bank's transaction format
        # Example: "Date Description Debit Credit Balance"
        patterns = [
            r"^(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$",
            r"^(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$",
        ]

        for pat in patterns:
            match = re.search(pat, remaining)
            if match:
                groups = match.groups()
                description = self.clean_description(groups[0])

                if len(groups) == 3:
                    amount = self.parse_amount(groups[1])
                    balance = self.parse_amount(groups[2])

                    # Determine debit/credit from description
                    if "CR" in description.upper() or "CREDIT" in description.upper():
                        credit = amount
                        debit = None
                    else:
                        debit = amount
                        credit = None
                elif len(groups) == 4:
                    debit = self.parse_amount(groups[1]) if groups[1] else None
                    credit = self.parse_amount(groups[2]) if groups[2] else None
                    balance = self.parse_amount(groups[3])
                else:
                    continue

                category = "credit" if credit else "debit"

                return Transaction(
                    date=txn_date.date(),
                    description=description,
                    debit=debit,
                    credit=credit,
                    balance=balance or Decimal("0"),
                    ref_no=None,
                    category=category,
                )

        return None
```

## 2. Register Parser

Add to `bank_parser/banks/__init__.py`:

```python
from .yourbank import YourBankParser

BANK_PARSERS = {
    # ... existing parsers ...
    "yourbank": YourBankParser,
}
```

## 3. Add Tests

Create `tests/test_yourbank.py`:

```python

# you may not use this file except in compliance with the License.
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# limitations under the License.

from bank_parser.banks.yourbank import YourBankParser


def test_yourbank_parser_instantiation():
    parser = YourBankParser("dummy.pdf")
    assert parser.bank_code == "yourbank"
    assert parser.bank_name == "Your Bank Name"
```

Add sample PDFs to `tests/fixtures/yourbank/` (gitignored).

## 4. Run Tests

```bash
pytest tests/test_yourbank.py -v
pytest tests/ -v
```

## 5. Update Documentation

- Add to [Supported Banks](../user_guide/banks.md) table
- Add entry to `README.md` bank list

## Key Methods to Override

| Method | Purpose |
|--------|---------|
| `parse()` | Main entry point |
| `_extract_account_number()` | Regex for account number |
| `_extract_account_type()` | Savings/Current/Credit Card |
| `_parse_transactions()` | Iterate pages/lines |
| `_parse_transaction_line()` | Parse single line |

## Base Class Helpers

| Method | Description |
|--------|-------------|
| `extract_text()` | PDF text via pdfplumber/pymupdf |
| `parse_date(str)` | Multiple format support |
| `parse_amount(str)` | Handles commas, decimals |
| `clean_description(str)` | Normalize whitespace |
| `detect_statement_period(str)` | Extract date range |

## Tips

- Test with multiple statement formats (savings, current, credit card)
- Handle regional variants (SBI has 20+)
- Use `ref_no` extraction from narration
- Handle both debit/credit column formats
- Add `Credit Card` subclass if format differs

## Submit

1. Fork repo
2. Create feature branch
3. Add parser + tests
4. Update docs
5. Open PR

See [CONTRIBUTING.md](../contributing.md) for full guide.