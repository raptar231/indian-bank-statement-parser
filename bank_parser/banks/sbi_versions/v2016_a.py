# Copyright 2024 Koushik Mondal (github.com/komo0225)
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

"""
SBI Parser Version 2016A (2016-2017 format)

Netbanking statement with the year printed on a separate line:

    Txn Date  Value  Description  Ref No./Cheque  Debit  Credit  Balance
    29 Nov    29 Nov CASH DEPOSIT-CASH                         1,000.00 1,000.00
    2016      2016   DEPOSIT SELF-

Transactions carry IMPS/P2A references on the year/continuation lines.
"""

from bank_parser.banks.sbi_versions.sbi_standard import SBIStandardParser


class SBIParser2016A(SBIStandardParser):
    """SBI Parser for 2016-2017 netbanking format (Version 2016A)"""

    version = "2016A"
    year_range = (2016, 2017)
    require_header = False

    header_patterns = [
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
        "DEPOSIT SELF",
        "CREDIT INTEREST--",
        "BY TRANSFER-INB",
    ]

    has_value_date_column = True
    has_cheque_no_column = True
