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

# Why not just use Bank CSV?

> **TL;DR:** Bank CSVs are inconsistent, limited, and missing GST fields. This tool gives you one schema for all banks, full history, and GSTR-2A reconciliation.

## The Problem with Bank CSVs

Most Indian banks offer CSV downloads, but they're designed for human viewing — not for automated processing at scale.

| Aspect | Bank CSV | This Tool |
|--------|----------|-----------|
| **Schema** | Different per bank (HDFC/ICICI/SBI/Axis all differ) | **One unified schema** for all banks |
| **Date format** | `DD/MM/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD`, `DD MMM YYYY` | Normalized to `YYYY-MM-DD` |
| **Amounts** | `1,000.00`, `1000.00`, signed/unsigned, debit/credit mixed | Decimal, separate `debit`/`credit` columns |
| **History** | Usually 90–180 days | **Full statement period** (years via PDF) |
| **Credit cards** | Many banks **don't offer CSV** for cards | Parses card PDFs |
| **GSTR-2A** | No GSTIN, invoice numbers, place of supply, HSN | **GSTR-2A ready** CSV with all required fields |
| **Bulk processing** | Manual download per account | `parse-bank-statements --input-dir ./clients --bank hdfc` |
| **Offline/air-gapped** | Requires login + download | Works on **PDFs only**, no network |
| **Regional variants** | SBI has 20+ regional formats | Handles all via regex patterns |

## Real-World Scenarios

### CA Firm (50+ clients/month)
```bash
# Without tool: Manual download, open each CSV, fix columns, merge
# With tool:
parse-bank-statements --input-dir ./client-statements --bank hdfc --output-dir ./parsed
```

### Lender (Income verification)
```bash
# Need standardized income data from multiple banks
df = parse_statements(input_dir="./borrower-statements", bank="sbi")
# All transactions in same schema, ready for analysis
```

### GST Practitioner
```bash
# Generate GSTR-2A upload format
df = parse_statements(
    input_dir="./client-statements",
    bank="icici",
    reconcile_gstr2a=True,
    gstin="29ABCDE1234F1Z5"
)
df.to_csv("gstr2a_upload.csv", index=False)
```

## When Bank CSV is Fine

- Personal finance (1-2 accounts)
- Occasional manual review
- No GST reconciliation needed
- Recent transactions only (last 90 days)

## When You Need This Tool

- **Scale**: Processing 10+ statements/month
- **Multi-bank**: HDFC + ICICI + SBI in same workflow
- **GST**: GSTR-2A reconciliation required
- **History**: Need full year+ of transactions
- **Credit cards**: Banks don't offer CSV for cards
- **Automation**: CI/CD pipelines, scheduled jobs
- **Offline**: Air-gapped environments, no bank login

## The Unified Output Schema

```csv
date,description,debit,credit,balance,ref_no,category
2024-01-15,"UPI-PAYMENT TO MERCHANT",500.00,,45000.00,UPI123456789,debit
2024-01-16,"SALARY CREDIT",,120000.00,165000.00,SAL987654321,credit
```

| Column | Type | Description |
|--------|------|-------------|
| `date` | date | Transaction date (YYYY-MM-DD) |
| `description` | string | Raw transaction narration |
| `debit` | float | Debit amount (empty if credit) |
| `credit` | float | Credit amount (empty if debit) |
| `balance` | float | Running balance after transaction |
| `ref_no` | string | Bank reference/UTR number |
| `category` | string | `debit` or `credit` |

---

**Bottom line:** If you process statements at scale, need GST reconciliation, or want one schema for all banks — this tool saves hours of manual cleanup every month.