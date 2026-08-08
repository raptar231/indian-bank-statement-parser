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

# indian-bank-statement-parser

**Offline-first CLI & Python library to convert Indian bank statement PDFs (HDFC, ICICI, SBI, Axis) into standardized CSV/JSON for GST reconciliation, accounting, and lending workflows.**

[![CI](https://github.com/raptar231/indian-bank-statement-parser/actions/workflows/ci.yml/badge.svg)](https://github.com/raptar231/indian-bank-statement-parser/actions/workflows/ci.yml)
[![Docker](https://github.com/raptar231/indian-bank-statement-parser/actions/workflows/docker.yml/badge.svg)](https://github.com/raptar231/indian-bank-statement-parser/actions/workflows/docker.yml)
[![PyPI](https://img.shields.io/pypi/v/indian-bank-statement-parser)](https://pypi.org/project/indian-bank-statement-parser/)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue)](https://github.com/raptar231/indian-bank-statement-parser/pkgs/container/indian-bank-statement-parser)
[![License](https://img.shields.io/github/license/raptar231/indian-bank-statement-parser)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/indian-bank-statement-parser)](https://pypi.org/project/indian-bank-statement-parser/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

---

## Why this exists

- 🔒 **100% local** — bank data never leaves your machine/server
- 🏦 **4 major banks, production-ready** — HDFC, ICICI, SBI, Axis (covering ~70% of retail statements)
- 📊 **Standardized output** — same schema across all banks (`date`, `description`, `debit`, `credit`, `balance`, `ref_no`, `category`)
- ⚙️ **Plugin architecture** — add custom bank parsers in ~50 lines
- 🐳 **Docker + PyPI** — `pip install` or `docker pull`, runs anywhere
- 🧾 **GST-ready** — optional GSTR-2A reconciliation output
- 🤖 **CI/CD friendly** — GitHub Action template included

## Quick start

### Install

```bash
# pip (standard)
pip install indian-bank-statement-parser

# Poetry
poetry add indian-bank-statement-parser

# UV (fast)
uv add indian-bank-statement-parser

# Docker (no Python needed)
docker pull ghcr.io/raptar231/indian-bank-statement-parser:latest
```

### CLI

```bash
# Parse all PDFs in a directory
parse-bank-statements \
  --input-dir ./statements \
  --output-dir ./parsed \
  --bank hdfc \
  --format csv

# Parse single file
parse-bank-statements \
  --input-file ./statement.pdf \
  --output-file ./parsed.csv \
  --bank icici

# With GST reconciliation (GSTR-2A format)
parse-bank-statements \
  --input-dir ./statements \
  --output-dir ./parsed \
  --bank sbi \
  --reconcile-gstr2a \
  --gstin 29ABCDE1234F1Z5

# List supported banks
parse-bank-statements --list-banks
```

### Python API

```python
from bank_parser import parse_statements, parse_file, list_banks
import pandas as pd

# Parse all PDFs in directory
df = parse_statements(
    input_dir="./statements",
    bank="hdfc",
    output_format="dataframe"
)

# Parse single file
df = parse_file("./statement.pdf", bank="icici")

# With GST reconciliation
df = parse_statements(
    input_dir="./statements",
    bank="sbi",
    reconcile_gstr2a=True,
    gstin="29ABCDE1234F1Z5"
)

# Save to CSV
df.to_csv("parsed.csv", index=False)

# List supported banks
print(list_banks())
# ['hdfc', 'icici', 'sbi', 'axis']
```

---

## Documentation

- [Quickstart](getting_started/quickstart.md) — Get running in 5 minutes
- [Installation](getting_started/installation.md) — Detailed install options
- [Why not Bank CSV?](getting_started/why-not-bank-csv.md) — Comparison with bank CSVs
- [CLI Reference](user_guide/cli.md) — All commands and flags
- [Python API](user_guide/python_api.md) — `parse_statements`, `parse_file`, models
- [Supported Banks](user_guide/banks.md) — HDFC, ICICI, SBI, Axis details
- [Output Schema](user_guide/schema.md) — Standardized columns
- [GSTR-2A Reconciliation](user_guide/gstr2a.md) — GST workflow
- [Adding a Bank Parser](developer_guide/adding_bank.md) — Step-by-step guide
- [Architecture](developer_guide/architecture.md) — Internal design
- [Testing](developer_guide/testing.md) — Test patterns
- [Docker](deployment/docker.md) — Build, run, CI/CD
- [GitHub Actions](deployment/github_actions.md) — CI/CD workflows
- [PyPI Release](deployment/pypi_release.md) — Release process

---

## Supported banks

| Bank | Status | Statement types |
|------|--------|-----------------|
| HDFC | ✅ Production | Savings, Current, Credit Card |
| ICICI | ✅ Production | Savings, Current, Credit Card |
| SBI | ✅ Production | Savings, Current (all regional variants) |
| Axis | ✅ Production | Savings, Current, Credit Card |

Missing your bank? [Add a parser](developer_guide/adding_bank.md) in ~50 lines or [request it](https://github.com/raptar231/indian-bank-statement-parser/issues/new).

---

## License

Apache-2.0 — see [LICENSE](https://github.com/raptar231/indian-bank-statement-parser/blob/main/LICENSE).

---

Built for CA firms, lenders, and fintechs processing Indian bank statements at scale.

[Report a bank format issue](https://github.com/raptar231/indian-bank-statement-parser/issues/new) • [Request a feature](https://github.com/raptar231/indian-bank-statement-parser/issues/new) • [Request a bank](https://github.com/raptar231/indian-bank-statement-parser/issues/new)