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

# Contributing

Thank you for your interest in contributing! This project aims to provide a robust, offline-first solution for parsing Indian bank statements.

## Getting Started

### Development Setup

```bash
# Clone the repository
git clone https://github.com/raptar231/indian-bank-statement-parser
cd indian-bank-statement-parser

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=bank_parser --cov-report=html

# Run specific test file
pytest tests/test_banks.py -v
```

### Code Quality

```bash
# Format code
black bank_parser/ tests/

# Lint
ruff check bank_parser/ tests/

# Type check
mypy bank_parser/
```

## Adding a New Bank Parser

### 1. Create the Parser

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

        date_match = re.match(r"^(\d{2}/\d{2}/\d{4})", line)
        if not date_match:
            return None

        date_str = date_match.group(1)
        txn_date = self.parse_date(date_str)
        if not txn_date:
            return None

        remaining = line[date_match.end():].strip()

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

### 2. Register the Parser

Add to `bank_parser/banks/__init__.py`:

```python
from .yourbank import YourBankParser

BANK_PARSERS = {
    # ... existing parsers ...
    "yourbank": YourBankParser,
}
```

### 3. Add Tests

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

### 4. Add Sample PDFs

Place sample PDF statements in `tests/fixtures/yourbank/` (these should be gitignored if they contain real data).

### 5. Update Documentation

- Add the bank to the supported banks table in [Supported Banks](user_guide/banks.md)
- Update the list of supported banks in CLI help text

## Guidelines

### Code Style

- Follow PEP 8 (enforced by black and ruff)
- Use type hints for all functions
- Write docstrings for public methods
- Keep functions small and focused

### Testing

- Aim for >80% coverage
- Test edge cases (empty lines, malformed dates, missing amounts)
- Use real PDF samples when possible (anonymized)

### Transaction Parsing

- Always return `Transaction` objects with all required fields
- Handle both debit and credit transactions
- Extract reference numbers when available
- Set `category` correctly ("debit" or "credit")

### Amount Parsing

- Use `parse_amount()` from base class (handles commas, decimals)
- Return `Decimal` for precision
- Handle negative amounts correctly

### Date Parsing

- Use `parse_date()` from base class (supports multiple formats)
- Return `datetime.date` objects

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/yourbank-parser`)
3. Make your changes
4. Run tests and linting
5. Commit with clear messages
6. Push to your fork
7. Open a Pull Request

### PR Checklist

- [ ] New parser follows the base class pattern
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Code formatted (`black bank_parser/ tests/`)
- [ ] Linting passes (`ruff check bank_parser/ tests/`)
- [ ] Type checking passes (`mypy bank_parser/`)
- [ ] Documentation updated ([Supported Banks](user_guide/banks.md))
- [ ] Sample PDFs added to fixtures (or note if not available)

## Reporting Issues

When reporting a bank format issue:

1. Include the bank name and statement type (savings/current/credit card)
2. Describe the issue (missing transactions, wrong amounts, etc.)
3. If possible, share an anonymized sample PDF
4. Mention the parser version

## Feature Requests

Open an issue with:
- Clear description of the feature
- Use case / motivation
- Any implementation ideas

## Code of Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold this code.