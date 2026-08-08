# Output Schema

All parsers produce the same standardized columns.

## Transaction Schema

```csv
date,description,debit,credit,balance,ref_no,category
2024-01-15,"UPI-PAYMENT TO MERCHANT",500.00,,45000.00,UPI123456789,debit
2024-01-16,"SALARY CREDIT",,120000.00,165000.00,SAL987654321,credit
2024-01-17,"ATM WITHDRAWAL",2000.00,,163000.00,ATM456789123,debit
```

## Columns

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `date` | `date` (YYYY-MM-DD) | ✅ | Transaction date |
| `description` | `string` | ✅ | Raw transaction narration |
| `debit` | `float` | ❌ | Debit amount (empty if credit) |
| `credit` | `float` | ❌ | Credit amount (empty if debit) |
| `balance` | `float` | ✅ | Running balance after transaction |
| `ref_no` | `string` | ❌ | Bank reference/UTR number |
| `category` | `string` | ✅ | `debit` or `credit` |

## Rules

- **Exactly one** of `debit` or `credit` is populated per row
- `balance` reflects running balance **after** the transaction
- `ref_no` extracted from narration (UTR, Cheque No, Ref No)
- `category` derived: `debit` if amount is outflow, `credit` if inflow
- Dates normalized to ISO format `YYYY-MM-DD`
- Amounts as `Decimal` for precision, exported as `float` in CSV/JSON

## Example Rows

### Debit (Outflow)
```json
{
  "date": "2024-01-15",
  "description": "UPI-PAYMENT TO MERCHANT",
  "debit": 500.00,
  "credit": "",
  "balance": 45000.00,
  "ref_no": "UPI123456789",
  "category": "debit"
}
```

### Credit (Inflow)
```json
{
  "date": "2024-01-16",
  "description": "SALARY CREDIT",
  "debit": "",
  "credit": 120000.00,
  "balance": 165000.00,
  "ref_no": "SAL987654321",
  "category": "credit"
}
```

## Pandas DataFrame Types

```python
df.dtypes
# date             datetime64[ns]
# description      object
# debit            float64
# credit           float64
# balance          float64
# ref_no           object
# category         object
```

## GSTR-2A Output Schema

When using `--reconcile-gstr2a`, different columns:

| Column | Type | Description |
|--------|------|-------------|
| `GSTIN` | string | Supplier GSTIN |
| `Invoice Date` | date | DD-MM-YYYY |
| `Invoice Number` | string | From ref_no or generated |
| `Invoice Value` | float | Total with GST |
| `Place of Supply` | string | State code (default: 29) |
| `Reverse Charge` | string | `N` |
| `Invoice Type` | string | `B2B` |
| `Rate` | float | GST rate (default: 18) |
| `Taxable Value` | float | Invoice Value / 1.18 |
| `IGST` | float | Interstate GST |
| `CGST` | float | Central GST |
| `SGST` | float | State GST |
| `CESS` | float | Cess (default: 0) |

See [GSTR-2A Reconciliation](./gstr2a.md) for details.