# indian-bank-statement-parser

[![CI](https://github.com/raptar231/indian-bank-statement-parser/actions/workflows/ci.yml/badge.svg)](https://github.com/raptar231/indian-bank-statement-parser/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-ghcr.io-2496ED?logo=docker&logoColor=white)](https://github.com/raptar231/indian-bank-statement-parser/pkgs/container/indian-bank-statement-parser)
[![PyPI](https://img.shields.io/pypi/v/indian-bank-statement-parser)](https://pypi.org/project/indian-bank-statement-parser/)
[![License](https://img.shields.io/github/license/raptar231/indian-bank-statement-parser)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/indian-bank-statement-parser)](https://pypi.org/project/indian-bank-statement-parser/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Docs](https://img.shields.io/badge/docs-raptar231.github.io-blue)](https://raptar231.github.io/indian-bank-statement-parser/)

**Offline-first CLI & Python library to convert Indian bank statement PDFs (HDFC, ICICI, SBI, Axis) into standardized CSV/JSON for GST reconciliation, accounting, and lending workflows.**

## Quick Start

```bash
# pip
pip install indian-bank-statement-parser

# Poetry
poetry add indian-bank-statement-parser

# UV (fast)
uv add indian-bank-statement-parser

# Docker
docker pull ghcr.io/raptar231/indian-bank-statement-parser:latest
```

```bash
# Parse directory
parse-bank-statements --input-dir ./statements --output-dir ./parsed --bank hdfc

# Parse single file
parse-bank-statements --input-file ./stmt.pdf --output-file ./out.csv --bank icici

# GSTR-2A reconciliation
parse-bank-statements --input-dir ./stmts --output-dir ./gstr2a --bank sbi --reconcile-gstr2a --gstin 29ABCDE1234F1Z5

# Parse netbanking CSV/Excel exports (not PDFs)
parse-bank-statements --input-file ./export.csv --bank hdfc --format xlsx --output-file ./out.xlsx --input-format csv
parse-bank-statements --input-dir ./exports --bank icici --format yaml --input-format csv

# Web UI / API server (http://localhost:8000)
parse-bank-statements --serve
```

## Output Formats

| Format | Flag | Description |
|--------|------|-------------|
| CSV | `--format csv` | Flat transaction rows (default) |
| JSON | `--format json` | Structured JSON array |
| Excel | `--format xlsx` | Multi-sheet workbook (Transactions + Summary) |
| YAML | `--format yaml` | Human-readable YAML |
| DataFrame | `--format dataframe` | In-memory pandas DataFrame (Python API) |

**Excel workbook** includes:
- `Transactions` sheet — all parsed transactions
- `Summary` sheet — bank, account, period, balances, validation status

**YAML output** is ideal for config pipelines and diffing.

## Input Formats

| Format | Flag | Description |
|--------|------|-------------|
| PDF | `--input-format pdf` | Bank statement PDFs (default) |
| CSV | `--input-format csv` | Netbanking CSV exports |
| Excel | `--input-format xlsx` | Netbanking Excel exports |

```bash
# Parse a directory of CSV exports
parse-bank-statements --input-dir ./csv_exports --bank hdfc --format xlsx --output-dir ./parsed --input-format csv
```

## Web UI & API

Run the same parsing engine as a web application with `--serve`:

```bash
parse-bank-statements --serve                 # http://localhost:8000 (binds 0.0.0.0)
parse-bank-statements --serve --host 127.0.0.1 --port 9000
```

The built-in UI can upload a PDF and parse it, parse everything in the input
directory, unlock password-protected PDFs, and run GSTR-2A reconciliation.
The REST API (also browsable at `/docs`) exposes the same operations:

| Endpoint | Purpose |
|----------|---------|
| `GET /api/banks` | List supported banks |
| `GET /api/dirs` | Show the data directories in use |
| `POST /api/parse` | Parse an uploaded PDF |
| `GET /api/parse-dir` | Parse every PDF in the input directory |
| `POST /api/unlock` | Unlock one or more uploaded PDFs sharing one password (multipart `files`) |
| `POST /api/unlock-dir` | Unlock every PDF in the input directory with one password |
| `GET /api/unlock.zip` | Download unlocked PDFs as a ZIP (comma-separated `files` query) |
| `GET /api/download/{file}` | Download a generated file |

The unlock UI accepts multiple files at once; unlocked PDFs are stored in both
`data/output` and `data/unlocked` and can be downloaded individually or as a ZIP.

Web server logs go to the same `logs.txt` (with password redaction) as the
rest of the tool.

### Data directories

All file input/output flows through a `data` root:

- On a normal machine: `./data` is created if missing, containing
  `data/input`, `data/output` and `data/unlocked`.
- In Docker: the root is `/data`, mounted as a volume (see below).
- Override with the `BANK_PARSER_DATA_DIR` environment variable.

Without `--input-dir`, the CLI falls back to `data/input`; `--unlock`
writes to `data/unlocked` by default.

```bash
# Docker web server: mount a directory as /data
docker run --rm -p 8000:8000 -v "$PWD:/data" ghcr.io/raptar231/indian-bank-statement-parser:latest --serve
```

## Why this exists

| Problem with Bank CSVs | This Tool |
|------------------------|-----------|
| Different schema per bank | **One unified schema** |
| Inconsistent date formats | Normalized to `YYYY-MM-DD` |
| Mixed debit/credit amounts | Separate `debit`/`credit` columns |
| Limited history (90-180 days) | **Full statement period** via PDF |
| No CSV for credit cards | Parses card PDFs |
| No GSTR-2A fields | **GSTR-2A ready** CSV |
| Manual per-account download | `parse-bank-statements --input-dir ./clients` |

**Use this if:** You process 10+ statements/month, need GST reconciliation, multi-bank standardization, or full history.

**Skip if:** Occasional personal statements — bank CSV is fine.

## Documentation

**Full docs:** [raptar231.github.io/indian-bank-statement-parser](https://raptar231.github.io/indian-bank-statement-parser/)

- [Quickstart](https://raptar231.github.io/indian-bank-statement-parser/getting_started/quickstart/)
- [CLI Reference](https://raptar231.github.io/indian-bank-statement-parser/user_guide/cli/)
- [Python API](https://raptar231.github.io/indian-bank-statement-parser/user_guide/python_api/)
- [Supported Banks](https://raptar231.github.io/indian-bank-statement-parser/user_guide/banks/)
- [GSTR-2A Reconciliation](https://raptar231.github.io/indian-bank-statement-parser/user_guide/gstr2a/)
- [Adding a Bank](https://raptar231.github.io/indian-bank-statement-parser/developer_guide/adding_bank/)
- [Docker](https://raptar231.github.io/indian-bank-statement-parser/deployment/docker/)
- [PyPI Release](https://raptar231.github.io/indian-bank-statement-parser/deployment/pypi_release/)

## Supported Banks

| Bank | Code | Status |
|------|------|--------|
| HDFC | `hdfc`, `hdfc_cc` | ✅ Production |
| ICICI | `icici`, `icici_cc` | ✅ Production |
| SBI | `sbi`, `sbi_cc` | ✅ Production |
| Axis | `axis`, `axis_cc` | ✅ Production |

## Don't see your bank or statement format?

Open an issue or drop an email with details so support can be added:

- 🐛 **Report an unsupported document**: [Open an issue](https://github.com/raptar231/indian-bank-statement-parser/issues/new) and attach an anonymized sample PDF/CSV
- 🏦 **Request a new bank**: [Open an issue](https://github.com/raptar231/indian-bank-statement-parser/issues/new) with the bank name, statement type (savings/current/credit card), and an anonymized sample
- 📧 **Email**: [mondalsonu4@gmail.com](mailto:mondalsonu4@gmail.com)

Please make sure to **anonymize** your statement (mask account numbers, names, and amounts) before sharing.

## Install & Run

```bash
# Development
git clone https://github.com/raptar231/indian-bank-statement-parser
cd indian-bank-statement-parser
pip install -e ".[dev]"

# Tests
pytest tests/ -v

# Code quality
ruff check bank_parser/ tests/
mypy bank_parser/
black --check bank_parser/ tests/
```

## License

Apache-2.0 — see [LICENSE](LICENSE).

---

## Support

If this tool saves you time, consider supporting development:

- ☕ **Buy Me a Coffee**: [buymeacoffee.com/raptar231](https://buymeacoffee.com/raptar231)
- ❤️ **GitHub Sponsors**: [github.com/sponsors/raptar231](https://github.com/sponsors/raptar231)
- 📧 **Contact**: mondalsonu4@gmail.com

---

Built for CA firms, lenders, and fintechs processing Indian bank statements at scale.