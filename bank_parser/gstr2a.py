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

from decimal import Decimal

import pandas as pd  # type: ignore[import-untyped]

from bank_parser.models import GSTR2AEntry, Statement, Transaction


def generate_gstr2a(statement: Statement, gstin: str) -> "pd.DataFrame":
    entries = []

    for txn in statement.transactions:
        if txn.category == "credit" and txn.credit:
            taxable_value = txn.credit / Decimal("1.18")
            igst = txn.credit - taxable_value

            entry = GSTR2AEntry(
                gstin=gstin,
                invoice_date=txn.date,
                invoice_number=txn.ref_no or f"TXN{txn.date.strftime('%Y%m%d')}",
                invoice_value=txn.credit,
                place_of_supply="29",
                rate=Decimal("18"),
                taxable_value=taxable_value,
                igst=igst,
            )
            entries.append(entry.to_dict())

    return pd.DataFrame(entries)


def generate_gstr2a_from_transactions(
    transactions: list[Transaction], gstin: str
) -> "pd.DataFrame":
    entries = []

    for txn in transactions:
        if txn.category == "credit" and txn.credit:
            taxable_value = txn.credit / Decimal("1.18")
            igst = txn.credit - taxable_value

            entry = GSTR2AEntry(
                gstin=gstin,
                invoice_date=txn.date,
                invoice_number=txn.ref_no or f"TXN{txn.date.strftime('%Y%m%d')}",
                invoice_value=txn.credit,
                place_of_supply="29",
                rate=Decimal("18"),
                taxable_value=taxable_value,
                igst=igst,
            )
            entries.append(entry.to_dict())

    return pd.DataFrame(entries)


def save_gstr2a_csv(df: "pd.DataFrame", output_path: str) -> None:
    df.to_csv(output_path, index=False)
