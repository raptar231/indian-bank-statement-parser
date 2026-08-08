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

# CLI Reference

Complete command reference for `parse-bank-statements`.

## Synopsis

```bash
parse-bank-statements [OPTIONS]
```

## Options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--input-dir` | `-i` | Either `-i` or `-f` | Directory containing PDF statements |
| `--input-file` | `-f` | Either `-i` or `-f` | Single PDF file to parse |
| `--output-dir` | `-o` | No | Output directory for parsed files |
| `--output-file` | | No | Output file for single file parsing |
| `--bank` | `-b` | **Yes** | Bank code: `hdfc`, `icici`, `sbi`, `axis` |
| `--format` | | No | Output format: `csv`, `json`, `dataframe` (default: `csv`) |
| `--reconcile-gstr2a` | | No | Generate GSTR-2A reconciliation output |
| `--gstin` | | With `--reconcile-gstr2a` | GSTIN for GSTR-2A reconciliation |
| `--list-banks` | | No | List supported banks and exit |
| `--help` | | No | Show help message |

## Examples

### Parse directory

```bash
parse-bank-statements \
  --input-dir ./statements \
  --output-dir ./parsed \
  --bank hdfc \
  --format csv
```

### Parse single file

```bash
parse-bank-statements \
  --input-file ./statement.pdf \
  --output-file ./parsed.csv \
  --bank icici
```

### GSTR-2A reconciliation

```bash
parse-bank-statements \
  --input-dir ./statements \
  --output-dir ./gstr2a \
  --bank sbi \
  --reconcile-gstr2a \
  --gstin 29ABCDE1234F1Z5
```

### List banks

```bash
parse-bank-statements --list-banks
```

### Help

```bash
parse-bank-statements --help
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (invalid args, file not found, parse error) |

## Output Formats

| Format | Description |
|--------|-------------|
| `csv` | CSV file (default) |
| `json` | JSON array of transactions |
| `dataframe` | Pandas DataFrame (Python API only) |

## Bank Codes

| Code | Bank |
|------|------|
| `hdfc` | HDFC Bank Savings/Current |
| `hdfc_cc` | HDFC Credit Card |
| `icici` | ICICI Bank Savings/Current |
| `icici_cc` | ICICI Credit Card |
| `sbi` | SBI Savings/Current |
| `sbi_cc` | SBI Credit Card |
| `axis` | Axis Bank Savings/Current |
| `axis_cc` | Axis Credit Card |

## Docker Usage

```bash
docker run --rm \
  -v $(pwd)/statements:/input \
  -v $(pwd)/parsed:/output \
  ghcr.io/raptar231/indian-bank-statement-parser:latest \
  --input-dir /input --output-dir /output --bank hdfc
```

## Environment Variables

No environment variables required. All configuration via CLI flags.

## See Also

- [Python API](../user_guide/python_api.md)
- [GSTR-2A Reconciliation](../user_guide/gstr2a.md)
- [Supported Banks](./banks.md)