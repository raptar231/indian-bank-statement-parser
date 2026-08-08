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

"""
SBI Parser Version 2017B (2017-2019 format)

Netbanking statement; the same layout as 2016A with the year on a
separate line, but rows may also be extracted with the year inline
(``1 Nov 2017 1 Nov 2017 ...``) or glued at the end of the row
(``... 1,454.52 / 2017 2017 szyrfG8E9BEfdEy v9wIGACNQPJJ9``).

References include ``NEFT*HDFC0000240*N286170`` and split UTRs such as
``JSBI5800496343I GACIPGSU8``.
"""

from bank_parser.banks.sbi_versions.sbi_standard import SBIStandardParser


class SBIParser2017B(SBIStandardParser):
    """SBI Parser for 2017-2019 netbanking format (Version 2017B)"""

    version = "2017B"
    year_range = (2017, 2019)
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
        "IMPS/P2A",
        "NEFT*HDFC",
        "ATM WDL",
        "TO TRANSFER-INB",
        "JSBI",
    ]

    has_value_date_column = True
    has_cheque_no_column = True
