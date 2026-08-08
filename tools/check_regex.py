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