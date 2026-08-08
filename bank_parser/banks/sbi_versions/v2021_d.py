"""
SBI Parser Version 2021D (2021-2023 format)

Netbanking statement with the same stable table layout. UPI is the
dominant payment rail in this period (``BY UPI``, ``TO UPI``,
``UPI/210000000000/...`` references) alongside IMPS and NEFT.
"""

from bank_parser.banks.sbi_versions.sbi_standard import SBIStandardParser


class SBIParser2021D(SBIStandardParser):
    """SBI Parser for 2021-2023 netbanking format (Version 2021D)"""

    version = "2021D"
    year_range = (2021, 2023)

    header_patterns = [
        r"Txn\s+Date\s+Value\s+Date\s+Description\s+Ref\s+No\./Cheque\s+No\.\s+Debit\s+Credit\s+Balance",
        r"Txn\s+Date\s+Value\s+Description\s+Ref\s+No\./Cheque\s+No\.\s+Debit\s+Credit\s+Balance",
        r"Txn\s+Date\s+Value\s+Description\s+Ref\s+No\./Cheque\s+Debit\s+Credit\s+Balance",
    ]

    identifier_keywords = [
        "Txn Date",
        "Value Date",
        "Ref No./Cheque No.",
        "Debit Credit Balance",
        "REGULAR SB CHQ",
        "STATE BANK OF INDIA",
        "BY UPI",
        "TO UPI",
        "UPI/",
        "IMPS/P2A",
        "NEFT",
    ]

    has_value_date_column = True
    has_cheque_no_column = True
