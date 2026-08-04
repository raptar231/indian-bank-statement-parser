# Contributing to Indian Bank Statement Parser

Thank you for your interest in contributing! This project aims to provide a robust, offline-first solution for parsing Indian bank statements.

## Getting Started

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourname/indian-bank-statement-parser
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
pytest tests/test_hdfc.py -v
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
from bank_parser.banks.base import BaseBankParser
from bank_parser.models import Transaction, Statement
from typing import List
from decimal import Decimal
import re

class YourBankParser(BaseBankParser):
    bank_code = "yourbank"
    bank_name = "Your Bank Name"
    
    def parse(self) -> Statement:
        pages_text = self.extract_text()
        full_text = "\n".join(pages_text)
        
        # Extract account info
        self.statement.account_number = self._extract_account_number(full_text)
        self.statement.account_type = self._extract_account_type(full_text)
        self.statement.statement_period_start, self.statement.statement_period_end = self.detect_statement_period(full_text)
        
        # Parse transactions
        self.statement.transactions = self._parse_transactions(pages_text)
        
        return self.statement
    
    def _extract_account_number(self, text: str) -> str:
        # Implement regex for your bank's account number format
        pass
    
    def _extract_account_type(self, text: str) -> str:
        # Implement
        pass
    
    def _parse_transactions(self, pages_text: List[str]) -> List[Transaction]:
        transactions = []
        for page_text in pages_text:
            for line in page_text.split("\n"):
                txn = self._parse_transaction_line(line)
                if txn:
                    transactions.append(txn)
        return transactions
    
    def _parse_transaction_line(self, line: str) -> Transaction:
        # Parse a single transaction line
        # Return Transaction object or None
        pass
```

### 2. Register the Parser

Add to `bank_parser/banks/__init__.py`:

```python
from .yourbank import YourBankParser

BANK_PARSERS = {
    # ... existing parsers
    "yourbank": YourBankParser,
}
```

### 3. Add Tests

Create `tests/test_yourbank.py`:

```python
import pytest
from bank_parser.banks.yourbank import YourBankParser

def test_yourbank_parser_instantiation():
    parser = YourBankParser("dummy.pdf")
    assert parser.bank_code == "yourbank"
    assert parser.bank_name == "Your Bank Name"
```

### 4. Add Sample PDFs

Place sample PDF statements in `tests/fixtures/yourbank/` (these should be gitignored if they contain real data).

### 5. Update Documentation

- Add the bank to the supported banks table in README.md
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
- [ ] Documentation updated (README.md)
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