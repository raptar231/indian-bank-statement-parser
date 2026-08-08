# Copyright 2024-{{year}} Koushik Mondal (github.com/raptar231)
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

# Copyright 2024 Koushik Mondal (github.com/raptar231)
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
from pathlib import Path
from typing import Union, cast

import pandas as pd  # type: ignore[import-untyped]

from bank_parser.banks import BANK_PARSERS
from bank_parser.gstr2a import generate_gstr2a
from bank_parser.models import Statement, Transaction


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
) -> Union["pd.DataFrame", Statement, list[dict]]:
    parser_class = get_parser(bank)
    parser = parser_class(str(pdf_path))
    statement = parser.parse()
    statement.validate_balances()

    if reconcile_gstr2a:
        if not gstin:
            raise ValueError("GSTIN is required for GSTR-2A reconciliation")
        gstr2a_df = generate_gstr2a(statement, gstin)
        if output_format == "dataframe":
            return gstr2a_df
        elif output_format == "csv" or output_format == "json":
            return gstr2a_df.to_dict("records")
        return gstr2a_df

    if output_format == "dataframe":
        return statement.to_dataframe()
    elif output_format == "statement":
        return statement
    if output_format == "csv" or output_format == "json":
        return statement.to_dataframe().to_dict("records")
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
            output_file = output_path / f"parsed_{bank}.csv"

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
