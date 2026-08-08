<!--
  ~ Copyright 2024-{{year}} Koushik Mondal (github.com/raptar231)
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

# Architecture

## Overview

```
indian-bank-statement-parser/
├── bank_parser/
│   ├── __init__.py          # Public API exports
│   ├── cli.py               # Typer CLI entry point
│   ├── core.py              # parse_file(), parse_statements()
│   ├── models.py            # Pydantic models (Transaction, Statement, GSTR2AEntry)
│   ├── gstr2a.py            # GST reconciliation logic
│   └── banks/
│       ├── __init__.py      # BANK_PARSERS registry
│       ├── base.py          # BaseBankParser (abstract)
│       ├── hdfc.py          # HDFC Bank parser
│       ├── icici.py         # ICICI Bank parser
│       ├── sbi.py           # SBI parser
│       └── axis.py          # Axis Bank parser
├── tests/
│   ├── test_models.py
│   └── test_banks.py
└── docs/
```

## Core Components

### 1. Models (`models.py`)

Pydantic v2 models with validation:

- **Transaction** — Single transaction with `date`, `description`, `debit`, `credit`, `balance`, `ref_no`, `category`
- **Statement** — Container with account info + list of transactions
- **GSTR2AEntry** — GST reconciliation output model

Key features:
- `Decimal` for monetary precision
- Custom validators for amounts, dates, categories
- `to_dict()`, `to_dataframe()`, `to_csv()`, `to_json()` methods

### 2. Base Parser (`banks/base.py`)

Abstract `BaseBankParser` with shared functionality:

```python
class BaseBankParser(ABC):
    bank_code: str = ""
    bank_name: str = ""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.statement = Statement(bank=self.bank_code)

    @abstractmethod
    def parse(self) -> Statement:
        pass

    # Shared helpers:
    def extract_text() -> list[str]          # pdfplumber + pymupdf fallback
    def parse_date(str) -> datetime          # 12+ formats
    def parse_amount(str) -> Decimal         # Handles commas, spaces
    def clean_description(str) -> str        # Normalize whitespace
    def detect_statement_period(str) -> tuple # Regex patterns
```

### 3. Bank Parsers (`banks/*.py`)

Each bank extends `BaseBankParser`:

```python
class HDFCParser(BaseBankParser):
    bank_code = "hdfc"
    bank_name = "HDFC Bank"

    def parse(self) -> Statement:
        # 1. Extract text from PDF
        # 2. Detect account info
        # 3. Parse transactions line by line
        # 4. Return Statement
```

Common pattern:
1. `extract_text()` → list of page texts
2. Join pages → full text for account detection
3. `_parse_transactions(pages_text)` → iterate lines
4. `_parse_transaction_line(line)` → regex matching
5. Return `Transaction` objects

### 4. Core API (`core.py`)

High-level functions:

- `list_banks()` → `list[str]`
- `parse_file(pdf_path, bank, ...)` → DataFrame/Statement/JSON
- `parse_statements(input_dir, bank, ...)` → Combined DataFrame
- `generate_gstr2a()` / `generate_gstr2a_from_transactions()` → GSTR-2A DataFrame

### 5. CLI (`cli.py`)

Typer-based CLI with:
- Single command `parse` with all options
- Rich output (tables, colors)
- Docker-compatible

## Data Flow

```
PDF File
    │
    ▼
BaseBankParser.extract_text()  (pdfplumber → pymupdf fallback)
    │
    ▼
BankParser.parse()              (bank-specific logic)
    │
    ▼
List[Transaction]               (validated Pydantic models)
    │
    ▼
Statement                       (container + metadata)
    │
    ▼
core.parse_file() / parse_statements()
    │
    ▼
Output: DataFrame / CSV / JSON / GSTR-2A DataFrame
```

## Plugin Architecture

New banks added via:

1. Create `bank_parser/banks/yourbank.py` with `YourBankParser(BaseBankParser)`
2. Register in `banks/__init__.py`: `BANK_PARSERS["yourbank"] = YourBankParser`
3. No core changes needed

## PDF Extraction

Dual-engine approach:
1. **pdfplumber** (primary) — better table/text extraction
2. **pymupdf** (fallback) — handles scanned/complex PDFs

```python
def extract_text(self) -> list[str]:
    try:
        return self.extract_text_pdfplumber()
    except Exception:
        return self.extract_text_pymupdf()
```

## Type Safety

- Full type annotations
- `mypy` strict mode passes
- Pydantic v2 for runtime validation
- `TYPE_CHECKING` for pandas imports

## Extensibility Points

| Extension | Location |
|-----------|----------|
| New bank | `banks/yourbank.py` + `banks/__init__.py` |
| New output format | `core.py` + `models.py` |
| New GST fields | `models.py` + `gstr2a.py` |
| New CLI flag | `cli.py` + `core.py` |
| New PDF engine | `base.py` |

## See Also

- [Adding a Bank Parser](./adding_bank.md)
- [Testing](./testing.md)