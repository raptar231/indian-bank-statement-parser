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

# Quickstart

Get running in 5 minutes.

## Prerequisites

- Python 3.10+
- PDF statements from HDFC, ICICI, SBI, or Axis Bank

## Install

```bash
# pip (standard)
pip install indian-bank-statement-parser

# Poetry
poetry add indian-bank-statement-parser

# UV (fastest)
uv add indian-bank-statement-parser
```

## Parse your first statement

### CLI

```bash
# Parse single PDF
parse-bank-statements \
  --input-file ./hdfc_statement.pdf \
  --output-file ./parsed.csv \
  --bank hdfc

# Parse directory of PDFs
parse-bank-statements \
  --input-dir ./statements \
  --output-dir ./parsed \
  --bank icici \
  --format csv
```

### Python

```python
from bank_parser import parse_file

df = parse_file("./statement.pdf", bank="hdfc")
df.to_csv("parsed.csv", index=False)
print(df.head())
```

## Output

```csv
date,description,debit,credit,balance,ref_no,category
2024-01-15,"UPI-PAYMENT TO MERCHANT",500.00,,45000.00,UPI123456789,debit
2024-01-16,"SALARY CREDIT",,120000.00,165000.00,SAL987654321,credit
```

## Next steps

- [Installation](installation.md) — Poetry, UV, Docker, pre-commit
- [CLI Reference](../user_guide/cli.md) — All flags and options
- [Python API](../user_guide/python_api.md) — Programmatic usage
- [GSTR-2A Reconciliation](../user_guide/gstr2a.md) — GST workflow