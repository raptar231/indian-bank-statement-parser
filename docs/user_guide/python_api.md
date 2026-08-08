# Python API

Programmatic usage for integration into applications.

## Quick Reference

```python
from bank_parser import parse_statements, parse_file, list_banks
import pandas as pd
```

## Functions

### `parse_file()`

Parse a single PDF statement.

```python
from bank_parser import parse_file

# Returns pandas DataFrame
df = parse_file(
    "./statement.pdf",
    bank="hdfc",
    output_format="dataframe"  # or "csv", "json"
)

# With GSTR-2A reconciliation
df = parse_file(
    "./statement.pdf",
    bank="icici",
    reconcile_gstr2a=True,
    gstin="29ABCDE1234F1Z5"
)

# Save
df.to_csv("parsed.csv", index=False)
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `pdf_path` | `str \| Path` | Yes | — | Path to PDF file |
| `bank` | `str` | Yes | — | Bank code |
| `output_format` | `str` | No | `"dataframe"` | `"dataframe"`, `"csv"`, `"json"` |
| `reconcile_gstr2a` | `bool` | No | `False` | Generate GSTR-2A output |
| `gstin` | `str \| None` | With GSTR-2A | `None` | GSTIN for reconciliation |

**Returns:** `pd.DataFrame` \| `list[dict]` \| `str` (JSON)

---

### `parse_statements()`

Parse all PDFs in a directory.

```python
from bank_parser import parse_statements

# Returns pandas DataFrame with all transactions combined
df = parse_statements(
    input_dir="./statements",
    bank="hdfc",
    output_format="dataframe"
)

# With output directory (saves CSV automatically)
df = parse_statements(
    input_dir="./statements",
    bank="icici",
    output_dir="./parsed",
    output_format="csv"
)

# GSTR-2A reconciliation
df = parse_statements(
    input_dir="./statements",
    bank="sbi",
    reconcile_gstr2a=True,
    gstin="29ABCDE1234F1Z5"
)
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `input_dir` | `str \| Path` | Yes | — | Directory with PDFs |
| `bank` | `str` | Yes | — | Bank code |
| `output_format` | `str` | No | `"dataframe"` | `"dataframe"`, `"csv"`, `"json"` |
| `output_dir` | `str \| Path \| None` | No | `None` | Save output to directory |
| `reconcile_gstr2a` | `bool` | No | `False` | Generate GSTR-2A output |
| `gstin` | `str \| None` | With GSTR-2A | `None` | GSTIN for reconciliation |
| `file_pattern` | `str` | No | `"*.pdf"` | Glob pattern for PDFs |

**Returns:** `pd.DataFrame` \| `list[dict]` \| `str` (JSON)

---

### `list_banks()`

List all supported bank codes.

```python
from bank_parser import list_banks

print(list_banks())
# ['hdfc', 'hdfc_cc', 'icici', 'icici_cc', 'sbi', 'sbi_cc', 'axis', 'axis_cc']
```

**Returns:** `list[str]`

---

## Models

### `Transaction`

```python
from bank_parser import Transaction
from datetime import date
from decimal import Decimal

txn = Transaction(
    date=date(2024, 1, 15),
    description="UPI-PAYMENT TO MERCHANT",
    debit=Decimal("500.00"),
    credit=None,
    balance=Decimal("45000.00"),
    ref_no="UPI123456789",
    category="debit"
)

# Convert to dict
txn.to_dict()
# {'date': '2024-01-15', 'description': '...', 'debit': 500.0, ...}
```

### `Statement`

```python
from bank_parser import Statement

stmt = Statement(
    bank="hdfc",
    account_number="12345678901234",
    account_type="Savings",
    transactions=[txn1, txn2]
)

# Convert to DataFrame
df = stmt.to_dataframe()

# Save
stmt.to_csv("output.csv")
stmt.to_json("output.json")
```

### `GSTR2AEntry`

```python
from bank_parser import GSTR2AEntry
from datetime import date
from decimal import Decimal

entry = GSTR2AEntry(
    gstin="29ABCDE1234F1Z5",
    invoice_date=date(2024, 1, 15),
    invoice_number="INV001",
    invoice_value=Decimal("11800.00"),
    place_of_supply="29",
    rate=Decimal("18"),
    taxable_value=Decimal("10000.00"),
    igst=Decimal("1800.00"),
)

entry.to_dict()
# {'GSTIN': '29ABCDE1234F1Z5', 'Invoice Date': '15-01-2024', ...}
```

## Output Formats

| Format | Return Type | Use Case |
|--------|-------------|----------|
| `"dataframe"` | `pd.DataFrame` | Data analysis, ML |
| `"csv"` | `list[dict]` | Serialization |
| `"json"` | `str` (JSON) | API responses |

## Error Handling

```python
from bank_parser import parse_file

try:
    df = parse_file("statement.pdf", bank="hdfc")
except ValueError as e:
    # Invalid bank, missing file, parse error
    print(f"Error: {e}")
except Exception as e:
    # Unexpected error
    print(f"Unexpected: {e}")
```

## Type Hints

Full type annotations provided for IDE support:

```python
from bank_parser import parse_statements
import pandas as pd

df: pd.DataFrame = parse_statements(
    input_dir="./statements",
    bank="hdfc",
    output_format="dataframe"
)
```

## See Also

- [CLI Reference](./cli.md)
- [Models](./schema.md)
- [GSTR-2A Reconciliation](./gstr2a.md)