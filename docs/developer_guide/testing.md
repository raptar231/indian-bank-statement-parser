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

# Testing

## Overview

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=bank_parser --cov-report=term-missing

# Specific test file
pytest tests/test_banks.py -v

# Specific test
pytest tests/test_models.py::test_transaction_creation -v
```

## Test Structure

```
tests/
├── test_models.py       # Pydantic model validation
├── test_banks.py        # Parser instantiation
└── fixtures/            # Sample PDFs (gitignored)
    ├── hdfc/
    ├── icici/
    ├── sbi/
    └── axis/
```

## Test Categories

### 1. Model Tests (`test_models.py`)

Tests for Pydantic models:

```python
def test_transaction_creation():
    txn = Transaction(
        date=date(2024, 1, 15),
        description="UPI-PAYMENT",
        debit=Decimal("500.00"),
        credit=None,
        balance=Decimal("45000.00"),
        ref_no="UPI123",
        category="debit",
    )
    assert txn.category == "debit"

def test_transaction_to_dict():
    txn = Transaction(...)
    d = txn.to_dict()
    assert d["date"] == "2024-01-15"
    assert d["debit"] == 500.0
```

### 2. Bank Parser Tests (`test_banks.py`)

Tests for parser instantiation:

```python
def test_hdfc_parser_instantiation():
    parser = HDFCParser("dummy.pdf")
    assert parser.bank_code == "hdfc"
    assert parser.bank_name == "HDFC Bank"
```

### 3. Integration Tests (Future)

```python
def test_hdfc_parsing():
    # Requires sample PDF in fixtures
    parser = HDFCParser("tests/fixtures/hdfc/savings.pdf")
    statement = parser.parse()
    assert len(statement.transactions) > 0
    assert all(isinstance(t, Transaction) for t in statement.transactions)
```

## Running Tests

### Local Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all
pytest tests/ -v

# With coverage
pytest tests/ --cov=bank_parser --cov-report=html

# Watch mode
ptw tests/ -- -v
```

### CI Pipeline

```yaml
# .github/workflows/ci.yml
- name: Run tests
  run: |
    pytest tests/ -v --cov=bank_parser --cov-report=xml
```

## Adding Tests for New Bank

1. Add sample PDFs to `tests/fixtures/yourbank/` (anonymized)
2. Create `tests/test_yourbank.py`:

```python
from bank_parser.banks.yourbank import YourBankParser


def test_yourbank_parser_instantiation():
    parser = YourBankParser("dummy.pdf")
    assert parser.bank_code == "yourbank"
    assert parser.bank_name == "Your Bank Name"


def test_yourbank_savings_parsing():
    # Requires fixture
    parser = YourBankParser("tests/fixtures/yourbank/savings.pdf")
    statement = parser.parse()
    assert statement.bank == "yourbank"
    assert len(statement.transactions) > 0
```

3. Add anonymized PDF fixtures (or skip if unavailable)

## Test Utilities

### Base Parser Helpers

```python
from bank_parser.banks.base import BaseBankParser

# Test date parsing
parser = HDFCParser("")
assert parser.parse_date("15/01/2024").date() == date(2024, 1, 15)

# Test amount parsing
assert parser.parse_amount("1,000.00") == Decimal("1000.00")
assert parser.parse_amount("") is None
```

### Fixture Management

```python
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def get_fixture_path(bank: str, name: str) -> Path:
    return FIXTURES_DIR / bank / f"{name}.pdf"
```

## Mocking PDF Extraction

```python
from unittest.mock import patch, MagicMock

@patch("pdfplumber.open")
def test_parse_with_mock(mock_open):
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "15/01/2024 UPI Payment 500.00 45000.00"
    mock_pdf.pages = [mock_page]
    mock_open.return_value.__enter__.return_value = mock_pdf

    parser = HDFCParser("dummy.pdf")
    statement = parser.parse()
    assert len(statement.transactions) == 1
```

## Coverage Goals

| Component | Target |
|-----------|--------|
| Models | 100% |
| Core API | 90%+ |
| Bank Parsers | 80%+ |
| CLI | 70%+ |

## Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
  - repo: https://github.com/psf/black
    rev: 24.0.0
    hooks:
      - id: black
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
```

Run: `pre-commit run --all-files`

## See Also

- [Architecture](./architecture.md)
- [Adding a Bank Parser](./adding_bank.md)