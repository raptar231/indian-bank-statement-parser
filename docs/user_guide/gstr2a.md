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

# GSTR-2A Reconciliation

Generate GSTR-2A compatible CSV for GST portal upload.

## Overview

The tool extracts **credit transactions** (inflows) from bank statements and converts them to GSTR-2A format assuming 18% GST.

## Usage

### CLI

```bash
parse-bank-statements \
  --input-dir ./statements \
  --output-dir ./gstr2a \
  --bank hdfc \
  --reconcile-gstr2a \
  --gstin 29ABCDE1234F1Z5
```

### Python

```python
from bank_parser import parse_statements

df = parse_statements(
    input_dir="./statements",
    bank="icici",
    reconcile_gstr2a=True,
    gstin="29ABCDE1234F1Z5"
)

df.to_csv("gstr2a_upload.csv", index=False)
```

## How It Works

1. **Filters credit transactions** — Only inflows (salary, refunds, deposits)
2. **Calculates GST breakdown** — Assumes 18% GST rate
3. **Generates invoice numbers** — Uses `ref_no` or generates `TXN{YYYYMMDD}`
4. **Outputs GSTR-2A columns** — Compatible with offline tool

## GST Calculation

```
Invoice Value = Credit Amount
Taxable Value = Invoice Value / 1.18
IGST = Invoice Value - Taxable Value  (for interstate)
CGST + SGST = IGST / 2  (for intrastate)
```

Default: 18% GST, Place of Supply = 29 (Karnataka), Invoice Type = B2B

## Output Columns

| Column | Description |
|--------|-------------|
| `GSTIN` | Your GSTIN |
| `Invoice Date` | Transaction date (DD-MM-YYYY) |
| `Invoice Number` | From `ref_no` or `TXN{YYYYMMDD}` |
| `Invoice Value` | Credit amount (with GST) |
| `Place of Supply` | State code (default: 29) |
| `Reverse Charge` | `N` |
| `Invoice Type` | `B2B` |
| `Rate` | 18 |
| `Taxable Value` | Invoice Value / 1.18 |
| `IGST` | Interstate tax |
| `CGST` | Central GST |
| `SGST` | State GST |
| `CESS` | 0 |

## Example Output

```csv
GSTIN,Invoice Date,Invoice Number,Invoice Value,Place of Supply,Reverse Charge,Invoice Type,Rate,Taxable Value,IGST,CGST,SGST,CESS
29ABCDE1234F1Z5,15-01-2024,UPI123456789,11800.00,29,N,B2B,18,10000.00,1800.00,0.00,0.00,0.00
29ABCDE1234F1Z5,16-01-2024,SAL987654321,118000.00,29,N,B2B,18,100000.00,18000.00,0.00,0.00,0.00
```

## Limitations

- **Assumes 18% GST** — May need adjustment for 5%, 12%, 28% items
- **Place of Supply** — Defaults to 29 (Karnataka), update for other states
- **Interstate vs Intrastate** — Currently outputs IGST only; split CGST/SGST for intrastate
- **Invoice Type** — Defaults to B2B; B2C not supported
- **HSN/SAC** — Not included (add manually if required)

## Customization

Modify `bank_parser/gstr2a.py` to adjust:
- Default GST rate
- Place of supply
- Invoice type
- CGST/SGST split logic

## Upload to GST Portal

1. Generate CSV: `parse-bank-statements --reconcile-gstr2a --gstin YOUR_GSTIN`
2. Open [GST Offline Tool](https://www.gst.gov.in/download/returns)
3. Import CSV → Validate → Upload

## See Also

- [Output Schema](./schema.md)
- [Python API](../user_guide/python_api.md)
- [CLI Reference](./cli.md)