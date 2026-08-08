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

# Supported Banks

## Overview

| Bank | Code | Credit Card Code | Status | Statement Types Tested |
|------|------|------------------|--------|------------------------|
| HDFC Bank | `hdfc` | `hdfc_cc` | ✅ Production | Savings, Current, Credit Card |
| ICICI Bank | `icici` | `icici_cc` | ✅ Production | Savings, Current, Credit Card |
| State Bank of India | `sbi` | `sbi_cc` | ✅ Production | Savings, Current (all regional variants) |
| Axis Bank | `axis` | `axis_cc` | ✅ Production | Savings, Current, Credit Card |
| Punjab National Bank | `pnb` | – | ✅ Production | Savings |
| Kotak Mahindra Bank | `kotak` | – | ✅ Production | Savings |
| DBS Bank India | `dbs` | – | ✅ Production | Savings |

## Usage

```python
from bank_parser import parse_file

# Savings/Current accounts
df = parse_file("statement.pdf", bank="hdfc")
df = parse_file("statement.pdf", bank="icici")
df = parse_file("statement.pdf", bank="sbi")
df = parse_file("statement.pdf", bank="axis")
df = parse_file("statement.pdf", bank="pnb")
df = parse_file("statement.pdf", bank="kotak")
df = parse_file("statement.pdf", bank="dbs")

# Credit Cards
df = parse_file("cc_statement.pdf", bank="hdfc_cc")
df = parse_file("cc_statement.pdf", bank="icici_cc")
df = parse_file("cc_statement.pdf", bank="sbi_cc")
df = parse_file("cc_statement.pdf", bank="axis_cc")

# CLI
parse-bank-statements --bank hdfc --input-file stmt.pdf
parse-bank-statements --bank sbi_cc --input-file cc_stmt.pdf
```

## Statement Formats Supported

| Bank | Savings | Current | Credit Card | Regional Variants |
|------|---------|---------|-------------|-------------------|
| HDFC | ✅ | ✅ | ✅ | Standard |
| ICICI | ✅ | ✅ | ✅ | Standard |
| SBI | ✅ | ✅ | ✅ | ✅ (20+ regions) |
| Axis | ✅ | ✅ | ✅ | Standard |
| PNB | ✅ | – | – | Standard |
| Kotak | ✅ | – | – | Standard |
| DBS | ✅ | – | – | Standard |

## SBI Regional Variants

SBI has 20+ regional statement formats. The parser handles:
- Different date formats (`DD/MM/YYYY`, `DD-MM-YYYY`)
- Different column orders
- Hindi/English mixed narrations
- B/F (Brought Forward) / C/F (Carried Forward) balance labels

## Bank-Specific Notes

### HDFC
- Date format: `DD/MM/YYYY`
- Columns: Date, Narration, Withdrawal, Deposit, Balance, Ref No
- Credit cards: `Cr`/`Dr` indicator column

### ICICI
- Date format: `DD-MM-YYYY`
- Columns: Date, Description, Debit, Credit, Balance
- UTR/Ref numbers in narration

### SBI
- Date format: `DD/MM/YYYY` (varies by region)
- Labels: B/F (Brought Forward), C/F (Carried Forward)
- Credit cards: Separate format with `Cr`/`Dr`

### Axis
- Date format: `DD/MM/YYYY`
- Columns: Date, Description, Debit, Credit, Balance
- Salary/Deposit detection via keywords

### PNB
- Date format: `YYYY/MM/DD`
- Columns: Transaction Date, Cheque Number, Withdrawal, Deposit, Balance, Narration
- Blank withdrawal/deposit columns collapse in extracted text; the sign is recovered from running-balance arithmetic

### Kotak
- Date format: `DD-MMM-YYYY`
- Columns: Date, Narration, Chq/Ref No, Withdrawal (DR) / Deposit (CR), Balance
- Amounts carry a trailing `Dr`/`Cr` marker (some variants use separate debit/credit columns)

### DBS
- Date format: `DD/MM/YYYY`
- Columns: Date, Transaction Details, Withdrawal, Deposit, Balance
- Blank withdrawal/deposit columns collapse in extracted text; the sign is recovered from running-balance arithmetic

## Adding a New Bank

See [Adding a Bank Parser](../developer_guide/adding_bank.md) for step-by-step guide.

## Request a Bank

Missing your bank? [Open an issue](https://github.com/raptar231/indian-bank-statement-parser/issues/new) with:
- Bank name
- Statement type (savings/current/credit card)
- Sample PDF (anonymized)
- CSV export if available