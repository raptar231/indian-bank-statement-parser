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

from bank_parser.banks.axis import AxisCreditCardParser, AxisParser
from bank_parser.banks.base import BaseBankParser
from bank_parser.banks.dbs import DBSParser
from bank_parser.banks.hdfc import HDFCCreditCardParser, HDFCParser
from bank_parser.banks.icici import ICICICreditCardParser, ICICIParser
from bank_parser.banks.kotak import KotakParser
from bank_parser.banks.pnb import PNBParser
from bank_parser.banks.sbi import SBICreditCardParser, SBIParser
from bank_parser.models import Statement

BankParserType = (
    type[HDFCParser]
    | type[HDFCCreditCardParser]
    | type[ICICIParser]
    | type[ICICICreditCardParser]
    | type[SBIParser]
    | type[SBICreditCardParser]
    | type[AxisParser]
    | type[AxisCreditCardParser]
    | type[PNBParser]
    | type[KotakParser]
    | type[DBSParser]
)

BANK_PARSERS: dict[str, BankParserType] = {
    "hdfc": HDFCParser,
    "hdfc_cc": HDFCCreditCardParser,
    "icici": ICICIParser,
    "icici_cc": ICICICreditCardParser,
    "sbi": SBIParser,
    "sbi_cc": SBICreditCardParser,
    "axis": AxisParser,
    "axis_cc": AxisCreditCardParser,
    "pnb": PNBParser,
    "kotak": KotakParser,
    "dbs": DBSParser,
}

# Bank detection patterns - ordered by specificity (most specific first)
BANK_DETECTORS = {
    "icici": [
        r"ICICI\s+DIRECT",
        r"ICICI\s+Bank",
        r"ICICIBANK",
        r"icicibank\.com",
    ],
    "axis": [
        r"AXIS\s+BANK",
        r"\bAXISBANK\b(?!-)",  # exclude UPI refs like "AXISBANK-UTIB..."
        r"axisbank\.com",
    ],
    "sbi": [
        r"STATE\s+BANK\s+OF\s+INDIA",
        r"SBI\s+NETBANKING",
        r"YONO\s+SBI",
        r"ONLINES\.SBI",
        r"sbi\.co\.in",  # YONO e-statement footer
        r"ACCOUNT\s+STATEMENT\s+FROM",  # netbanking export header
        r"JSBI\d+",  # SBI transaction reference pattern
        r"ACH\s*Cr",  # ACH Credit - SBI specific
        r"BULK\s+POSTING",  # SBI bulk posting
    ],
    "hdfc": [
        r"HDFC\s+Bank",
        r"HDFCBANK",
        r"hdfcbank\.net",
    ],
    "pnb": [
        r"PUNJAB\s+NATIONAL\s+BANK",
        r"PUNB\d+",  # PNB IFSC code
        r"PNB\s+ONE",
        r"pnbindia",
    ],
    "kotak": [
        r"KOTAK\s+MAHINDRA\s+BANK",
        r"KOTAK\s+BANK",
        r"kotakbank\.com",
    ],
    "dbs": [
        r"DBS\s+BANK\s+INDIA",
        r"DIGIBANK\s+BY\s+DBS",
        r"dbs\.bank\.in",
    ],
}


def detect_bank(text: str) -> str | None:
    """Auto-detect which bank the statement belongs to.
    Returns bank code: 'hdfc', 'icici', 'sbi', 'axis', 'pnb', 'kotak', 'dbs',
    or None if undetected.
    """
    for bank_code, patterns in BANK_DETECTORS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return bank_code
    return None


def get_parser_class(bank_code: str, is_credit_card: bool = False) -> type[BaseBankParser] | None:
    """Get the parser class for a bank code.

    Args:
        bank_code: 'hdfc', 'icici', 'sbi', 'axis', 'pnb', 'kotak', 'dbs'
        is_credit_card: True for credit card statements

    Returns:
        Parser class, or None if not found
    """
    key = f"{bank_code}_cc" if is_credit_card else bank_code
    parser_class = BANK_PARSERS.get(key)
    if parser_class is not None:
        return parser_class  # type: ignore[return-value]
    return None


def auto_parse(pdf_path: str) -> Statement:
    """Convenience function: auto-detect bank and parse.

    Usage:
        from bank_parser.banks import auto_parse
        statement = auto_parse("statement.pdf")

    Auto-detects bank, then savings vs credit card, then format version.
    """
    # Use HDFC parser as base for text extraction (any parser works for extraction)
    temp_parser = HDFCParser(pdf_path)
    pages_text = temp_parser.extract_text()
    full_text = "\n".join(pages_text)

    # Detect bank
    bank_code = detect_bank(full_text)
    if not bank_code:
        raise ValueError("Could not detect bank from statement text")

    # Check if credit card (for banks that support it)
    if bank_code in ("hdfc", "icici", "sbi", "axis"):
        parser_class = BANK_PARSERS.get(bank_code)
        if parser_class and hasattr(parser_class, "_looks_like_credit_card"):
            # Create instance for credit card detection
            parser_instance = parser_class(pdf_path)
            if parser_instance._looks_like_credit_card(full_text):  # type: ignore[union-attr]
                return parser_instance.parse()

    # Regular savings/current account
    parser_class = BANK_PARSERS.get(bank_code)
    if not parser_class:
        raise ValueError(f"No parser for bank: {bank_code}")

    parser = parser_class(pdf_path)
    return parser.parse()


__all__ = [
    "BANK_PARSERS",
    "BANK_DETECTORS",
    "detect_bank",
    "get_parser_class",
    "auto_parse",
    "HDFCParser",
    "HDFCCreditCardParser",
    "ICICIParser",
    "ICICICreditCardParser",
    "SBIParser",
    "SBICreditCardParser",
    "AxisParser",
    "AxisCreditCardParser",
    "PNBParser",
    "KotakParser",
    "DBSParser",
]
