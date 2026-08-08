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