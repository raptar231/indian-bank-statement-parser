from bank_parser.banks.sbi_versions.v2016_a import SBIParser2016A
from pathlib import Path
import re

text = Path('tests/fixtures/sbi/dummy.txt').read_text()
pages = text.split('=== PAGE ')
pages = [p for p in pages if p.strip()]

parser = SBIParser2016A('')

# Debug amounts parsing
amounts_re = re.compile(
    r"((?<!\w)-|[\d,]+\.\d{2})\s+" r"((?<!\w)-|[\d,]+\.\d{2})(?:\s+((?<!\w)-|[\d,]+\.\d{2}))?"
)

for page in pages[:2]:
    lines = page.split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        row_match = parser.row_start_re.match(stripped)
        if not row_match:
            continue
        rest = row_match.group(3).strip()
        amount_matches = list(amounts_re.finditer(rest))
        if amount_matches:
            last = amount_matches[-1]
            amounts = last.groups()
            if 'SMS' in rest.upper() or 'CHARGES' in rest.upper():
                print(f"LINE: {rest[:80]}")
                print(f"  AMOUNTS: {amounts}")
                slot0 = amounts[0].strip() if amounts[0] else ""
                slot1 = amounts[1].strip() if amounts[1] else ""
                print(f"  SLOT0: '{slot0}' SLOT1: '{slot1}'")
                print(f"  SLOT0=='-': {slot0 == '-'} SLOT1=='-': {slot1 == '-'}")