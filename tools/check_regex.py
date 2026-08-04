import re
from pathlib import Path

text = Path('tests/fixtures/sbi/dummy.txt').read_text()
pages = text.split('=== PAGE ')
pages = [p for p in pages if p.strip()]

# Check year_line_re
year_line_re = re.compile(r'^(\d{4})\s+(\d{4})\s*(.*)')
glued_year_re = re.compile(r'/\s*(\d{4})\s+(\d{4})\s*')
amounts_re = re.compile(
    r'((?<!\w)-|[\d,]+\.\d{2})\s+' r'((?<!\w)-|[\d,]+\.\d{2})(?:\s+((?<!\w)-|[\d,]+\.\d{2}))?'
)

print("=== YEAR LINE RE MATCHES ===")
for page_idx, page in enumerate(pages[:3]):
    lines = page.split('\n')
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        m = year_line_re.match(stripped)
        if m:
            print(f"  Page {page_idx}: {stripped} -> {m.groups()}")

print("\n=== GLUED YEAR RE MATCHES ===")
for page_idx, page in enumerate(pages[:3]):
    for m in glued_year_re.finditer(page):
        print(f"  Page {page_idx}: {m.groups()}")

print("\n=== AMOUNTS RE MATCHES ===")
for page_idx, page in enumerate(pages[:3]):
    lines = page.split('\n')
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        m = amounts_re.search(stripped)
        if m:
            print(f"  Page {page_idx}: {stripped[:80]} -> {m.groups()}")