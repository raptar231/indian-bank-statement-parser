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

from bank_parser.banks.sbi_versions.v2016_a import SBIParser2016A
from pathlib import Path

text = Path('tests/fixtures/sbi/dummy.txt').read_text()
pages = text.split('=== PAGE ')
pages = [p for p in pages if p.strip()]

parser = SBIParser2016A('')

# Monkey patch to debug
original_is_credit = parser._is_credit
def debug_is_credit(desc):
    result = original_is_credit(desc)
    if 'SMS' in desc.upper() or 'CHARGES' in desc.upper():
        print(f'_is_credit("{desc}") -> {result}')
    return result
parser._is_credit = debug_is_credit

txns = parser._parse_transactions(pages)

for t in txns:
    if 'SMS' in t.description or 'CHARGES' in t.description:
        print(f'{t.date} | {t.category} | D:{t.debit} C:{t.credit} | Bal:{t.balance} | {t.description}')