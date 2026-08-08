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