"""
SBI Parser Version 2019C (2019-2021 format)

Netbanking statement with the same stable table layout. Era markers
for this period are inbound/outbound IMPS, NEFT and salary credits.
"""

from bank_parser.banks.sbi_versions.sbi_standard import SBIStandardParser


class SBIParser2019C(SBIStandardParser):
    """SBI Parser for 2019-2021 netbanking format (Version 2019C)"""

    version = "2019C"
    year_range = (2019, 2021)
    require_header = False

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
        "BY TRANSFER-INB",
        "SALARY CREDIT",
        "IMPS/P2A",
        "CREDIT INTEREST",
    ]

    has_value_date_column = True
    has_cheque_no_column = True
