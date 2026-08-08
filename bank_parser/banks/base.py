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
from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal

import pdfplumber  # type: ignore[import-untyped]
import pymupdf  # type: ignore[import-untyped]

from bank_parser.models import Statement


class BaseBankParser(ABC):
    bank_code: str = ""
    bank_name: str = ""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.statement = Statement(bank=self.bank_code)

    @abstractmethod
    def parse(self) -> Statement:
        pass

    def extract_text_pdfplumber(self) -> list[str]:
        pages_text = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
        return pages_text

    def extract_text_pymupdf(self) -> list[str]:
        pages_text = []
        doc = pymupdf.open(self.pdf_path)
        for i in range(doc.page_count):
            text = doc.load_page(i).get_text()
            if text:
                pages_text.append(text)
        doc.close()
        return pages_text

    def extract_text(self) -> list[str]:
        try:
            return self.extract_text_pdfplumber()
        except Exception:
            return self.extract_text_pymupdf()

    def parse_date(self, date_str: str) -> datetime | None:
        formats = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d.%m.%Y",
            "%d/%m/%y",
            "%d-%m-%y",
            "%d.%m.%y",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d %b %Y",
            "%d %b, %Y",
            "%d-%b-%Y",
            "%d-%B-%Y",
            "%d %B %Y",
            "%b %d, %Y",
            "%B %d, %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None

    def parse_amount(self, amount_str: str) -> Decimal | None:
        if not amount_str:
            return None
        cleaned = amount_str.replace(",", "").replace(" ", "").strip()
        if cleaned in ("", "-", "0.00", "0"):
            return None
        try:
            return Decimal(cleaned)
        except Exception:
            return None

    def clean_description(self, desc: str) -> str:
        desc = re.sub(r"\s+", " ", desc).strip()
        desc = re.sub(r"^[-\s:;]+|[-\s:;]+$", "", desc)
        return desc

    def detect_account_info(self, text: str) -> dict:
        info = {}
        patterns = {
            "account_number": [
                r"(?:A/C|Account|Acct)\s*(?:No|Number|#)?[.:]?\s*([\d\*X]+)",
                r"Account\s+Number[:\s]+([\d\*X]+)",
            ],
            "account_type": [
                r"(?:Account|A/C)\s*Type[:\s]+(\w+)",
                r"(Savings|Current|Salary|Credit\s*Card)",
            ],
        }
        for key, pat_list in patterns.items():
            for pat in pat_list:
                match = re.search(pat, text, re.IGNORECASE)
                if match:
                    info[key] = match.group(1).strip()
                    break
        return info

    def detect_statement_period(self, text: str) -> tuple[date | None, date | None]:
        patterns = [
            r"Account\s+Statement\s+from\s+(\d{1,2}\s+\w{3}\s+\d{4})\s+to\s+(\d{1,2}\s+\w{3}\s+\d{4})",
            r"(?:Statement|Period)\s*(?:from|:)\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*(?:to|-)\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*-\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                start = self.parse_date(match.group(1))
                end = self.parse_date(match.group(2))
                if start and end:
                    return start.date(), end.date()
        return None, None
