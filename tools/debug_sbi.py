#!/usr/bin/env python3
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
Debug script for SBI parser regex development.
Loads a fixture, runs parser, shows detailed extraction.
Usage: python tools/debug_sbi.py tests/fixtures/sbi/your_fixture.txt
"""
import re
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bank_parser.banks.sbi import SBIParser
from bank_parser.banks.sbi_versions.sbi_standard import SBIStandardParser
from bank_parser.banks.sbi_versions.v2016_a import SBIParser2016A
from bank_parser.banks.sbi_versions.v2017_b import SBIParser2017B
from bank_parser.banks.sbi_versions.v2019_c import SBIParser2019C
from bank_parser.banks.sbi_versions.v2021_d import SBIParser2021D
from bank_parser.banks.sbi_versions.v2023_e import SBIParser2023E
from bank_parser.models import Transaction


def load_fixture(path: Path) -> tuple[str, list[str]]:
    text = path.read_text(encoding="utf-8")
    pages = text.split("=== PAGE ")
    # Normalize: first split may be empty
    pages = [p for p in pages if p.strip()]
    pages = [p.replace("===\n", "").replace("===", "") for p in pages]
    return text, pages


def test_all_parsers(pages: list[str], full_text: str):
    """Try each SBI version parser and show results."""
    parsers = [
        ("standard", SBIStandardParser("")),
        ("2016_a", SBIParser2016A("")),
        ("2017_b", SBIParser2017B("")),
        ("2019_c", SBIParser2019C("")),
        ("2021_d", SBIParser2021D("")),
        ("2023_e", SBIParser2023E("")),
    ]
    
    print("=" * 80)
    print("TESTING ALL SBI VERSION PARSERS")
    print("=" * 80)
    
    for name, parser in parsers:
        print(f"\n--- {name} ---")
        try:
            # Test metadata extraction
            acct = parser._extract_account_number(full_text)
            acct_type = parser._extract_account_type(full_text)
            # Use base class method
            period = parser.detect_statement_period(full_text)
            balances = (parser._extract_opening_balance(full_text), parser._extract_closing_balance(full_text))
            print(f"  Account: {acct}, Type: {acct_type}, Period: {period}, Balances: {balances}")
            
            # Test transactions
            txns = parser._parse_transactions(pages)
            print(f"  Transactions: {len(txns)}")
            for i, t in enumerate(txns[:5]):  # First 5
                print(f"    {i}: {t.date} | {t.category} | D:{t.debit} C:{t.credit} | Bal:{t.balance} | {t.description[:60]}")
            if len(txns) > 5:
                print(f"    ... and {len(txns) - 5} more")
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()


def debug_regex_matches(pages: list[str]):
    """Show what each regex matches on each page."""
    from bank_parser.banks.sbi_versions.sbi_standard import (
        row_start_re, year_line_re, glued_year_re, amounts_re, ref_re, utr_re, inline_ref_re
    )
    
    print("\n" + "=" * 80)
    print("REGEX MATCH DEBUG (SBI Standard)")
    print("=" * 80)
    
    for page_idx, page in enumerate(pages):
        print(f"\n--- PAGE {page_idx + 1} ---")
        lines = page.split("\n")
        for line_idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            
            matches = []
            for name, pattern in [
                ("row_start", row_start_re),
                ("year_line", year_line_re),
                ("glued_year", glued_year_re),
                ("amounts", amounts_re),
                ("ref", ref_re),
                ("utr", utr_re),
                ("inline_ref", inline_ref_re),
            ]:
                m = pattern.search(stripped)
                if m:
                    matches.append(f"{name}: {m.groups()}")
            
            if matches:
                print(f"  L{line_idx}: {stripped[:100]}")
                for m in matches:
                    print(f"    -> {m}")


def interactive_regex_test(pages: list[str]):
    """Interactive regex testing loop."""
    print("\n" + "=" * 80)
    print("INTERACTIVE REGEX TESTER (type 'quit' to exit)")
    print("=" * 80)
    
    # Combine all text for searching
    full_text = "\n".join(pages)
    
    while True:
        try:
            pattern_str = input("\nEnter regex pattern (or 'quit'): ").strip()
            if pattern_str.lower() in ('quit', 'exit', 'q'):
                break
            
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
            except re.error as e:
                print(f"Invalid regex: {e}")
                continue
            
            matches = list(pattern.finditer(full_text))
            print(f"Found {len(matches)} matches:")
            for i, m in enumerate(matches[:20]):
                print(f"  {i}: {m.groups() if m.groups() else m.group()}")
                # Show context
                start = max(0, m.start() - 50)
                end = min(len(full_text), m.end() + 50)
                context = full_text[start:end].replace('\n', '\\n')
                print(f"     ...{context}...")
            if len(matches) > 20:
                print(f"  ... and {len(matches) - 20} more")
                
        except KeyboardInterrupt:
            break
        except EOFError:
            break


def show_parser_internals(pages: list[str], full_text: str):
    """Show internal parser state for SBI standard."""
    parser = SBIStandardParser("")
    
    print("\n" + "=" * 80)
    print("PARSER INTERNAL STATE (SBI Standard)")
    print("=" * 80)
    
    # Show what _strip_value_dates does
    print("\n--- Value Date Stripping ---")
    for page in pages[:2]:
        for line in page.split("\n")[:10]:
            if "VALUE DATE" in line.upper():
                stripped = parser._strip_value_dates(line)
                if stripped != line:
                    print(f"  BEFORE: {line[:100]}")
                    print(f"  AFTER:  {stripped[:100]}")
    
    # Show transaction block parsing
    print("\n--- Block Parsing ---")
    from bank_parser.banks.sbi_versions.sbi_standard import row_start_re
    blocks = []
    current = []
    for page in pages:
        for line in page.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if row_start_re.match(stripped):
                if current:
                    blocks.append(current)
                current = [stripped]
            elif current:
                current.append(stripped)
        if current:
            blocks.append(current)
            current = []
    
    print(f"Found {len(blocks)} transaction blocks")
    for i, block in enumerate(blocks[:5]):
        print(f"\n  Block {i}:")
        for line in block:
            print(f"    {line}")
        # Try parsing
        try:
            txn = parser._parse_transaction_block(block)
            if txn:
                print(f"    -> PARSED: {txn.date} | {txn.category} | D:{txn.debit} C:{txn.credit} | {txn.description[:50]}")
            else:
                print(f"    -> FAILED TO PARSE")
        except Exception as e:
            print(f"    -> ERROR: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/debug_sbi.py <fixture.txt>")
        print("       python tools/debug_sbi.py <fixture.txt> --interactive")
        sys.exit(1)
    
    fixture_path = Path(sys.argv[1])
    if not fixture_path.exists():
        print(f"Not found: {fixture_path}")
        sys.exit(1)
    
    full_text, pages = load_fixture(fixture_path)
    print(f"Loaded: {fixture_path.name} ({len(pages)} pages, {len(full_text)} chars)")
    
    # Run all tests
    test_all_parsers(pages, full_text)
    debug_regex_matches(pages)
    show_parser_internals(pages, full_text)
    
    if "--interactive" in sys.argv:
        interactive_regex_test(pages)


if __name__ == "__main__":
    main()