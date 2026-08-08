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
