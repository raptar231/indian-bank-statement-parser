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
Anonymize a bank statement PDF for use as test fixture.
Replaces PII with realistic masked values.
"""
import re
import sys
from pathlib import Path
import pdfplumber


# Patterns to anonymize
PATTERNS = [
    # Account numbers (9-18 digits)
    (re.compile(r'\b\d{9,18}\b'), lambda m: 'X' * len(m.group())),
    # IFSC codes (4 letters + 7 alphanum)
    (re.compile(r'\b[A-Z]{4}[A-Z0-9]{7}\b'), lambda m: 'XXXX0000000'),
    # PAN (5 letters, 4 digits, 1 letter)
    (re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b'), lambda m: 'AAAAA0000A'),
    # Aadhaar (12 digits, possibly spaced)
    (re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b'), lambda m: 'XXXX XXXX XXXX'),
    # Phone numbers (10 digits, possibly with +91)
    (re.compile(r'(?:\+91[\s-]?)?\b[6-9]\d{9}\b'), lambda m: '+91 XXXXXXXXXX'),
    # Email addresses
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), lambda m: 'user@example.com'),
    # Names (capitalized words, 2-4 words) - be careful not to over-match
    (re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b'), lambda m: 'Account Holder'),
    # Addresses (lines with numbers, commas, typical address words)
    (re.compile(r'\b\d+[\s,].*(?:Road|Street|Lane|Nagar|Colony|Sector|Block|Floor|Apt|Flat|Building|House|No|Plot|Phase).*', re.IGNORECASE), lambda m: '123 Main Street, City, State - 123456'),
    # Dates - keep format but randomize slightly (optional)
    # (re.compile(r'\b\d{2}[-/]\d{2}[-/]\d{4}\b'), lambda m: '01-01-2024'),
    # Amounts - keep as-is (they're test data)
    # Card numbers (16 digits, possibly grouped)
    (re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), lambda m: 'XXXX XXXX XXXX XXXX'),
    # UPI IDs
    (re.compile(r'\b[\w.-]+@[\w.-]+\b'), lambda m: 'user@upi'),
    # MICR codes (9 digits)
    (re.compile(r'\b\d{9}\b'), lambda m: '000000000'),
]

# Specific SBI patterns
SBI_PATTERNS = [
    # SBI account number format
    (re.compile(r'Account Number\s*:?\s*\d+', re.IGNORECASE), 'Account Number: XXXXXXXXXXXX'),
    (re.compile(r'CIF\s*:?\s*\d+', re.IGNORECASE), 'CIF: XXXXXXXXXX'),
    (re.compile(r'Customer Name\s*:?\s*[A-Z\s]+', re.IGNORECASE), 'Customer Name: ACCOUNT HOLDER'),
    (re.compile(r'Address\s*:?\s*.*', re.IGNORECASE), 'Address: 123 Main Street, City, State - 123456'),
    (re.compile(r'Branch\s*:?\s*.*', re.IGNORECASE), 'Branch: MAIN BRANCH (00000)'),
    (re.compile(r'IFSC\s*:?\s*[A-Z0-9]+', re.IGNORECASE), 'IFSC: XXXX0000000'),
    (re.compile(r'MICR\s*:?\s*\d+', re.IGNORECASE), 'MICR: 000000000'),
]


def anonymize_text(text: str) -> str:
    """Apply all anonymization patterns to text."""
    # SBI-specific first
    for pattern, replacement in SBI_PATTERNS:
        text = pattern.sub(replacement, text)
    # Generic patterns
    for pattern, repl_fn in PATTERNS:
        text = pattern.sub(repl_fn, text)
    return text


def extract_and_anonymize(pdf_path: Path, output_path: Path = None) -> str:
    """Extract text from PDF, anonymize, and optionally save."""
    all_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                all_text.append(f"=== PAGE {i+1} ===\n{text}")
    full_text = "\n\n".join(all_text)
    anonymized = anonymize_text(full_text)
    
    if output_path:
        output_path.write_text(anonymized, encoding='utf-8')
        print(f"Saved anonymized fixture to: {output_path}")
    
    return anonymized


def main():
    if len(sys.argv) < 2:
        print("Usage: python anonymize_pdf.py <input.pdf> [output.txt]")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)
    
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = Path("tests/fixtures/sbi") / f"{input_path.stem}_anon.txt"
    
    extract_and_anonymize(input_path, output_path)


if __name__ == "__main__":
    main()