# Copyright 2024-2026 Koushik Mondal (github.com/raptar231)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Union, cast

import pandas as pd  # type: ignore[import-untyped]

from bank_parser.banks import BANK_PARSERS
from bank_parser.gstr2a import generate_gstr2a
from bank_parser.logging import get_logger
from bank_parser.models import Statement, Transaction

logger = get_logger("bank_parser.core")


def parse_csv_or_xlsx(
    file_path: str | Path,
    bank: str,
) -> Statement:
    """Parse a CSV or Excel file exported from netbanking."""
    file_path = Path(file_path)
    df = pd.read_excel(file_path) if file_path.suffix.lower() == ".xlsx" else pd.read_csv(file_path)

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Try to map common column variations
    col_map = {
        "date": ["date", "txn_date", "transaction_date", "value_date"],
        "description": [
            "description",
            "narration",
            "particulars",
            "details",
            "transaction_details",
        ],
        "debit": ["debit", "withdrawal", "dr", "debit_amount"],
        "credit": ["credit", "deposit", "cr", "credit_amount"],
        "balance": ["balance", "running_balance", "closing_balance"],
        "ref_no": ["ref_no", "reference", "ref_number", "utr", "transaction_id"],
    }

    mapped_cols = {}
    for std_col, variations in col_map.items():
        for var in variations:
            if var in df.columns:
                mapped_cols[std_col] = var
                break

    if "date" not in mapped_cols:
        raise ValueError("Could not find date column in file")

    transactions = []
    for _, row in df.iterrows():
        date_val = row[mapped_cols["date"]]
        if pd.isna(date_val):
            continue

        # Parse date
        from datetime import datetime

        date_formats = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d.%m.%Y",
            "%d/%m/%y",
            "%d-%m-%y",
            "%d.%m.%y",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d %b %Y",
            "%d %b, %Y",
            "%d-%b-%Y",
            "%d-%B-%Y",
            "%d %B %Y",
            "%b %d, %Y",
            "%B %d, %Y",
        ]
        txn_date = None
        for fmt in date_formats:
            try:
                txn_date = datetime.strptime(str(date_val).strip(), fmt)
                break
            except ValueError:
                continue

        if txn_date is None:
            continue

        description = str(row.get(mapped_cols.get("description", ""), "")).strip()
        if not description:
            continue

        from contextlib import suppress

        debit = None
        credit = None
        if "debit" in mapped_cols and not pd.isna(row[mapped_cols["debit"]]):
            val = str(row[mapped_cols["debit"]]).replace(",", "").strip()
            if val and val not in ("", "-", "0.00", "0"):
                with suppress(Exception):
                    debit = Decimal(val)

        if "credit" in mapped_cols and not pd.isna(row[mapped_cols["credit"]]):
            val = str(row[mapped_cols["credit"]]).replace(",", "").strip()
            if val and val not in ("", "-", "0.00", "0"):
                with suppress(Exception):
                    credit = Decimal(val)

        balance = Decimal("0")
        if "balance" in mapped_cols and not pd.isna(row[mapped_cols["balance"]]):
            val = str(row[mapped_cols["balance"]]).replace(",", "").strip()
            if val and val not in ("", "-", "0.00", "0"):
                with suppress(Exception):
                    balance = Decimal(val)

        ref_no = str(row.get(mapped_cols.get("ref_no", ""), "")).strip() or None

        # Determine category
        if credit is not None:
            category = "credit"
        elif debit is not None:
            category = "debit"
        else:
            category = "debit"

        transactions.append(
            Transaction(
                date=txn_date.date(),
                description=description,
                debit=debit,
                credit=credit,
                balance=balance,
                ref_no=ref_no,
                category=category,
            )
        )

    statement = Statement(bank=bank, transactions=transactions)
    return statement


def list_banks() -> list[str]:
    return list(BANK_PARSERS.keys())


def get_parser(bank: str) -> type:
    bank = bank.lower()
    if bank not in BANK_PARSERS:
        raise ValueError(f"Unsupported bank: {bank}. Supported banks: {list_banks()}")
    return BANK_PARSERS[bank]


def parse_file(
    pdf_path: str | Path,
    bank: str,
    output_format: str = "dataframe",
    reconcile_gstr2a: bool = False,
    gstin: str | None = None,
    password: str | None = None,
) -> Union["pd.DataFrame", Statement, list[dict], str, bytes]:
    parser_class = get_parser(bank)
    parser = parser_class(str(pdf_path), password=password)
    logger.info("Parsing %s with %s parser", pdf_path, bank)
    statement = parser.parse()
    statement.validate_balances()

    if reconcile_gstr2a:
        if not gstin:
            raise ValueError("GSTIN is required for GSTR-2A reconciliation")
        gstr2a_df = generate_gstr2a(statement, gstin)
        if output_format == "dataframe":
            return gstr2a_df
        elif output_format in ("csv", "json", "xlsx", "yaml"):
            return gstr2a_df.to_dict("records")
        return gstr2a_df

    if output_format == "dataframe":
        return statement.to_dataframe()
    elif output_format == "statement":
        return statement
    if output_format == "csv" or output_format == "json":
        return statement.to_dataframe().to_dict("records")
    elif output_format == "xlsx":
        return statement.to_excel()
    elif output_format == "yaml":
        return statement.to_yaml()
    else:
        raise ValueError(f"Unknown output format: {output_format}")


def parse_statements(
    input_dir: str | Path,
    bank: str,
    output_format: str = "dataframe",
    output_dir: str | Path | None = None,
    reconcile_gstr2a: bool = False,
    gstin: str | None = None,
    file_pattern: str = "*.pdf",
    on_file: Callable[[Statement], None] | None = None,
    password: str | None = None,
) -> Union["pd.DataFrame", list[Statement]]:
    input_path = Path(input_dir)
    pdf_files = list(input_path.glob(file_pattern))

    if not pdf_files:
        raise ValueError(f"No PDF files found in {input_dir} matching pattern {file_pattern}")

    all_transactions: list[Transaction] = []
    all_statements: list[Statement] = []

    for pdf_file in sorted(pdf_files):
        try:
            statement = cast(
                Statement,
                parse_file(
                    pdf_file,
                    bank=bank,
                    output_format="statement",
                    reconcile_gstr2a=False,
                    password=password,
                ),
            )
            if on_file is not None:
                on_file(statement)
            all_statements.append(statement)
            all_transactions.extend(statement.transactions)
        except Exception:
            continue

    if not all_transactions:
        raise ValueError("No transactions parsed from any file")

    combined_df = pd.DataFrame([t.to_dict() for t in all_transactions])
    combined_df = combined_df.sort_values("date").reset_index(drop=True)

    if reconcile_gstr2a:
        if not gstin:
            raise ValueError("GSTIN is required for GSTR-2A reconciliation")
        combined_df = generate_gstr2a_from_transactions(all_transactions, gstin)

    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if reconcile_gstr2a:
            output_file = output_path / "gstr2a_reconciliation.csv"
        else:
            if output_format == "xlsx":
                output_file = output_path / f"parsed_{bank}.xlsx"
            else:
                output_file = output_path / f"parsed_{bank}.csv"

        if output_format == "xlsx":
            statement = cast(
                Statement,
                parse_file(
                    pdf_files[0],
                    bank=bank,
                    output_format="statement",
                    reconcile_gstr2a=False,
                    password=password,
                ),
            )
            statement.to_excel(str(output_file))
        else:
            combined_df.to_csv(output_file, index=False)

    if output_format == "dataframe":
        return combined_df
    elif output_format == "statement":
        combined_statement = Statement(bank=bank, transactions=all_transactions)
        return combined_statement
    elif output_format == "csv":
        return combined_df.to_dict("records")
    elif output_format == "json":
        return combined_df.to_json(orient="records", date_format="iso")
    elif output_format == "xlsx":
        combined_statement = Statement(bank=bank, transactions=all_transactions)
        return combined_statement.to_excel()
    elif output_format == "yaml":
        combined_statement = Statement(bank=bank, transactions=all_transactions)
        return combined_statement.to_yaml()
    else:
        raise ValueError(f"Unknown output format: {output_format}")


def generate_gstr2a_from_transactions(
    transactions: list[Transaction], gstin: str
) -> "pd.DataFrame":
    from decimal import Decimal

    from bank_parser.models import GSTR2AEntry

    entries = []
    for txn in transactions:
        if txn.category == "credit" and txn.credit:
            entry = GSTR2AEntry(
                gstin=gstin,
                invoice_date=txn.date,
                invoice_number=txn.ref_no or f"TXN{txn.date.strftime('%Y%m%d')}",
                invoice_value=txn.credit,
                place_of_supply="29",
                rate=Decimal("18"),
                taxable_value=txn.credit / Decimal("1.18"),
                igst=txn.credit * Decimal("0.18") / Decimal("1.18"),
            )
            entries.append(entry.to_dict())

    return pd.DataFrame(entries)


def pdf_needs_password(path: str | Path) -> bool:
    """Return True if the PDF is password-protected."""
    import pymupdf  # type: ignore[import-untyped]

    doc = pymupdf.open(str(path))
    try:
        return bool(doc.needs_pass)
    finally:
        doc.close()


def unlock_pdf(
    input_path: str | Path,
    output_path: str | Path,
    password: str | None = None,
) -> Path:
    """Decrypt a password-protected PDF and save it without a password.

    Args:
        input_path: Path to the password-protected PDF.
        output_path: Where to save the unlocked PDF.
        password: Password for the PDF.

    Returns:
        The output path.
    """
    import pymupdf  # type: ignore[import-untyped]

    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(str(input_path))
    try:
        if doc.needs_pass and not password:
            raise ValueError(f"Password required to unlock {input_path}")
        if doc.needs_pass and not doc.authenticate(password):
            raise ValueError(f"Invalid password for {input_path}")
        doc.save(str(output_path), encryption=pymupdf.PDF_ENCRYPT_NONE)  # type: ignore[attr-defined]
    finally:
        doc.close()
    return output_path


def unlock_pdfs(
    input_dir: str | Path,
    output_dir: str | Path,
    password: str,
    file_pattern: str = "*.pdf",
) -> list[Path]:
    """Remove the password from all PDFs in a directory (same password).

    Args:
        input_dir: Directory containing password-protected PDFs.
        output_dir: Directory where unlocked PDFs are saved (created if missing).
        password: Password shared by all PDFs.
        file_pattern: Glob pattern for PDF files.

    Returns:
        List of paths to the unlocked PDFs.
    """
    input_path = Path(input_dir)
    pdf_files = sorted(input_path.glob(file_pattern))

    if not pdf_files:
        raise ValueError(f"No PDF files found in {input_dir} matching pattern {file_pattern}")

    unlocked: list[Path] = []
    for pdf_file in pdf_files:
        out_file = Path(output_dir) / pdf_file.name
        unlock_pdf(pdf_file, out_file, password)
        unlocked.append(out_file)
    return unlocked
