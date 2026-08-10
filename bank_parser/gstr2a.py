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

import re
from decimal import Decimal

import pandas as pd  # type: ignore[import-untyped]

from bank_parser.models import GSTR2AEntry, Statement, Transaction

# GST rate detection from narration/description
# Common patterns in Indian bank statements:
# - "GST @18%", "GST@18%", "GST 18%"
# - "*18%", "*5%", "*12%", "*28%"
# - "GST: 18", "GST:5"
# - Invoice suffixes like "/18", "/5", "/12", "/28"
# - UPI narration often has "GST" keyword with rate

GST_RATE_PATTERNS = [
    # GST @X% or GST@X% or GST X%
    (r"GST\s*[@:]?\s*(\d{1,2})\s*%", re.IGNORECASE),
    # *X%  (common in UPI/merchant descriptions)
    (r"\*(\d{1,2})\s*%", re.IGNORECASE),
    # GST: X  (without %)
    (r"GST\s*:\s*(\d{1,2})\b", re.IGNORECASE),
    # /X at end of invoice/ref (e.g. INV123/18)
    (r"/(\d{1,2})(?:\s|$)", re.IGNORECASE),
    # CGST/SGST/IGST X%
    (r"(?:C|S|I)?GST\s*(\d{1,2})\s*%", re.IGNORECASE),
]

VALID_GST_RATES = {5, 12, 18, 28, 0}  # 0 for exempt/nil

DEFAULT_GST_RATE = 18


def detect_gst_rate(narration: str) -> int:
    """Detect GST rate from transaction narration/description.

    Returns the detected rate (5, 12, 18, 28) or DEFAULT_GST_RATE (18) if not found.
    """
    if not narration:
        return DEFAULT_GST_RATE

    text = narration.upper()

    for pattern, flags in GST_RATE_PATTERNS:
        matches = re.findall(pattern, text, flags)
        for match in matches:
            try:
                rate = int(match)
                if rate in VALID_GST_RATES:
                    return rate
            except ValueError:
                continue

    return DEFAULT_GST_RATE


def calculate_taxable_and_igst(invoice_value: Decimal, rate: int) -> tuple[Decimal, Decimal]:
    """Calculate taxable value and IGST from invoice value and GST rate."""
    if rate == 0:
        return invoice_value, Decimal("0")
    multiplier = Decimal("1") + Decimal(str(rate)) / Decimal("100")
    taxable_value = invoice_value / multiplier
    igst = invoice_value - taxable_value
    return taxable_value, igst


def generate_gstr2a(statement: Statement, gstin: str) -> "pd.DataFrame":
    entries = []

    for txn in statement.transactions:
        if txn.category == "credit" and txn.credit:
            rate = detect_gst_rate(txn.description)
            taxable_value, igst = calculate_taxable_and_igst(txn.credit, rate)

            entry = GSTR2AEntry(
                gstin=gstin,
                invoice_date=txn.date,
                invoice_number=txn.ref_no or f"TXN{txn.date.strftime('%Y%m%d')}",
                invoice_value=txn.credit,
                place_of_supply="29",
                rate=Decimal(str(rate)),
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
            rate = detect_gst_rate(txn.description)
            taxable_value, igst = calculate_taxable_and_igst(txn.credit, rate)

            entry = GSTR2AEntry(
                gstin=gstin,
                invoice_date=txn.date,
                invoice_number=txn.ref_no or f"TXN{txn.date.strftime('%Y%m%d')}",
                invoice_value=txn.credit,
                place_of_supply="29",
                rate=Decimal(str(rate)),
                taxable_value=taxable_value,
                igst=igst,
            )
            entries.append(entry.to_dict())

    return pd.DataFrame(entries)


def save_gstr2a_csv(df: "pd.DataFrame", output_path: str) -> None:
    df.to_csv(output_path, index=False)
