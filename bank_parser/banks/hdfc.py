"""
HDFC Bank statement parsers.

Savings account statements ship in several layouts that share the same
block structure:

- Old (pre-2020): ``Date Narration Chq. / Ref No. Value Date Withdrawal
  Amount Deposit Amount Closing Balance*`` with rows that may wrap over
  several lines and a cheque/reference token sitting between the
  narration and the value date.
- New (2024): ``Txn Date Narration Withdrawals Deposits Closing Balance``
  with the narration inline-carrying ``Value Dt dd/mm/yyyy Ref <ref>``
  fragments and the amounts on their own line.
- Current (2026): ``Date Narration Chq./Ref.No. Value Dt Withdrawal Amt.
  Deposit Amt. Closing Balance`` where withdrawals/deposits collapse into
  a single amount column and rows wrap across continuation lines.

Credit card statements use ``DATE & TIME | TRANSACTION DESCRIPTION ...
AMOUNT`` rows with ``+ <n> C <amount>`` tails; debit vs credit is decided
from the narration (refunds, cashback and card payments are credits).
"""

import re
from datetime import date
from decimal import Decimal

from bank_parser.banks.base import BaseBankParser
from bank_parser.models import Statement, Transaction

# A savings transaction row always starts with a date (dd/mm/yy or dd/mm/yyyy);
# the narration may be on the same line or on following lines.
ROW_START_RE = re.compile(r"^(\d{2}/\d{2}/\d{2,4})(?:\s+(.*))?$")

# Two or three trailing amounts (withdrawal deposit closing / amount balance).
AMOUNTS_RE = re.compile(r"([\d,]+\.\d{2})(?:\s+([\d,]+\.\d{2}))(?:\s+([\d,]+\.\d{2}))?\s*$")

SAVINGS_HEADER_RE = re.compile(
    r"\bNarration\b[^\n]*\bWithdraw\w*\b[^\n]*\bDeposit\w*\b[^\n]*\bClosing\b",
    re.IGNORECASE,
)

# Lines that mark the end of the transaction table on a savings page.
SUMMARY_START_RE = re.compile(
    r"^(?:STATEMENT\s+SUMMARY|Cr\s+Count|Credit\s+Count|Debits|Credits"
    r"|Opening\s+Balance|Closing\s+Balance|Page\b|BALANCE\b|Total)",
    re.IGNORECASE,
)

VALUE_DATE_PHRASE_RE = re.compile(r"\bValue\s+Dt\s+\d{1,2}/\d{1,2}/\d{2,4}\b", re.IGNORECASE)
STANDALONE_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")

REF_MARKER_RE = re.compile(r"\bRef\s+([A-Za-z0-9][\w/-]*)")

PERIOD_PATTERNS = [
    r"Statement\s+of\s+account\s*From\s*:\s*(\d{2}/\d{2}/\d{2,4})\s*To\s*:\s*(\d{2}/\d{2}/\d{2,4})",
    r"Statement\s+From\s*:\s*(\d{2}/\d{2}/\d{2,4})\s*TO\s*:\s*(\d{2}/\d{2}/\d{2,4})",
    r"(\d{2}/\d{2}/\d{4})\s+To\s+(\d{2}/\d{2}/\d{4})",
    r"Billing\s+Period\s*[\n:]*\s*(\d{1,2}/\d{1,2}/\d{4})\s+to\s+(\d{1,2}/\d{1,2}/\d{4})",
    r"(\d{1,2}\s+\w{3},\s*\d{4})\s+-\s+(\d{1,2}\s+\w{3},\s*\d{4})",
]

OPENING_PATTERNS = [
    r"Opening\s+Balance[^\n]*\n\s*:?\s*([\d,]+\.\d{2})",
    r"Opening\s+Balance\s*[:\s]*([\d,]+\.\d{2})",
    r":\s*([\d,]+\.\d{2})[ \t]*:[ \t]*[\d,]+\.\d{2}[ \t]*$",
]

# Closing balance patterns capture the remainder of the line that follows the
# label; the balance is the last amount on that line (e.g. the 2026 summary
# line ``400,000.00 11 4 102,650.50 177,550.00 476,899.50`` ends with the
# closing balance). The 2024 combined layout pairs ``: 0.00`` (sweep-in) with
# ``: <closing>`` on the next line.
CLOSING_PATTERNS = [
    r"Closing\s+Balance[^\n]*\n\s*(?!\d{2}/\d{2}/\d{2,4})([^\n]*)",
    r"Closing\s+Bal[^\n]*\n\s*(?!\d{2}/\d{2}/\d{2,4})([^\n]*)",
    r":\s*0\.00\s*\n\s*:\s*([\d,]+\.\d{2})",
]

ACCOUNT_PATTERNS = [
    r"A/c\s*No[.:]\s*(\d{14})",
    r"Account\s+No\s*[.:]\s*(\d{14})",
    r"Account\s+Number[.:]\s*(\d{14})",
    r"(\d{14})",
]


class HDFCParser(BaseBankParser):
    bank_code = "hdfc"
    bank_name = "HDFC Bank"

    def parse(self) -> Statement:
        pages_text = self.extract_text()
        full_text = "\n".join(pages_text)
        if self._looks_like_credit_card(full_text):
            cc_parser = HDFCCreditCardParser(self.pdf_path)
            return cc_parser._parse_statement(pages_text, full_text)
        return self._parse_statement(pages_text, full_text)

    def _parse_statement(self, pages_text: list[str], full_text: str) -> Statement:
        self.statement.account_number = self._extract_account_number(full_text)
        self.statement.account_type = self._extract_account_type(full_text)
        self.statement.statement_period_start, self.statement.statement_period_end = (
            self._extract_period(full_text)
        )
        self.statement.opening_balance = self._extract_opening_balance(full_text)
        self.statement.closing_balance = self._extract_closing_balance(full_text)
        self.statement.transactions = self._parse_transactions(pages_text)
        return self.statement

    def _looks_like_credit_card(self, text: str) -> bool:
        return re.search(r"Credit\s+Card\s+Statement", text, re.IGNORECASE) is not None

    def _extract_account_number(self, text: str) -> str | None:
        for pat in ACCOUNT_PATTERNS:
            match = re.search(pat, text)
            if match:
                return match.group(1)
        return None

    def _extract_account_type(self, text: str) -> str | None:
        if re.search(r"Credit\s+Card\s+Statement|Credit\s+Card\b", text, re.IGNORECASE):
            return "Credit Card"
        match = re.search(r"Account\s+Type\s*:\s*([A-Z][A-Za-z -]*)", text)
        if match:
            return match.group(1).strip()
        if re.search(r"\bSAVINGS\b", text, re.IGNORECASE):
            return "Savings"
        if re.search(r"\bCURRENT\b", text, re.IGNORECASE):
            return "Current"
        return None

    def _extract_period(self, text: str) -> tuple[date | None, date | None]:
        for pat in PERIOD_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                start = self.parse_date(match.group(1))
                end = self.parse_date(match.group(2))
                if start and end:
                    return start.date(), end.date()
        return None, None

    def _extract_opening_balance(self, text: str) -> Decimal | None:
        for pat in OPENING_PATTERNS:
            match = re.search(pat, text, re.MULTILINE)
            if match:
                return self.parse_amount(match.group(1))
        return None

    def _extract_closing_balance(self, text: str) -> Decimal | None:
        for pat in CLOSING_PATTERNS:
            match = re.search(pat, text, re.MULTILINE)
            if match:
                amounts = re.findall(r"[\d,]+\.\d{2}", match.group(1))
                if amounts:
                    return self.parse_amount(amounts[-1])
        return None

    def _parse_transactions(self, pages_text: list[str]) -> list[Transaction]:
        transactions: list[Transaction] = []
        for page_text in pages_text:
            transactions.extend(self._parse_savings_page(page_text))
        return transactions

    def _parse_savings_page(self, page_text: str) -> list[Transaction]:
        transactions: list[Transaction] = []
        header = SAVINGS_HEADER_RE.search(page_text)
        lines = page_text[header.end() :].split("\n") if header else page_text.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            row_start = ROW_START_RE.match(line)
            if not row_start:
                i += 1
                continue

            block = [line]
            has_amounts = AMOUNTS_RE.search(line) is not None
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if not next_line:
                    i += 1
                    continue
                # A date-prefixed line only starts a new row once the current
                # block already has its amounts; value-date continuation lines
                # (e.g. ``01/04/2024 Ref N098765432112345``) come before them.
                if has_amounts and ROW_START_RE.match(next_line):
                    break
                if SUMMARY_START_RE.match(next_line):
                    break
                if AMOUNTS_RE.search(next_line):
                    has_amounts = True
                block.append(next_line)
                i += 1

            txn = self._parse_savings_block(block)
            if txn:
                transactions.append(txn)
        return transactions

    def _parse_savings_block(self, block: list[str]) -> Transaction | None:
        row_start = ROW_START_RE.match(block[0])
        if not row_start:
            return None
        txn_date_dt = self.parse_date(row_start.group(1))
        if txn_date_dt is None:
            return None
        txn_date = txn_date_dt.date()

        amounts_line_idx = None
        amounts_match = None
        for idx in range(len(block) - 1, -1, -1):
            match = AMOUNTS_RE.search(block[idx])
            if match:
                amounts_line_idx = idx
                amounts_match = match
                break
        if amounts_match is None or amounts_line_idx is None:
            return None

        amount1 = self.parse_amount(amounts_match.group(1))
        amount2 = self.parse_amount(amounts_match.group(2))
        amount3 = self.parse_amount(amounts_match.group(3))

        # Chq/ref column: a trailing all-digit token before the value date.
        prefix = self._strip_value_dates(block[amounts_line_idx][: amounts_match.start()].strip())
        ref_no: str | None = None
        narration_lines: list[str] = []
        for idx, line in enumerate(block):
            if idx == amounts_line_idx:
                continue
            if idx == 0:
                line = row_start.group(2) or ""
            line = self._strip_value_dates(line).strip()
            if line:
                narration_lines.append(line)

        if prefix:
            tokens = prefix.split()
            if tokens:
                candidate = tokens[-1]
                if re.fullmatch(r"\d+", candidate):
                    ref_no = self._normalize_ref(candidate)
                    prefix = " ".join(tokens[:-1])
                elif candidate and candidate in " ".join(narration_lines):
                    prefix = " ".join(tokens[:-1])

        # Assemble the narration in page order, slotting the amounts-line tail
        # back into its original position.
        parts: list[str] = []
        for idx, line in enumerate(block):
            if idx == amounts_line_idx:
                if prefix:
                    parts.append(prefix)
                continue
            if idx == 0:
                line = row_start.group(2) or ""
            line = self._strip_value_dates(line).strip()
            if line:
                parts.append(line)
        raw = " ".join(parts).strip()

        explicit_ref, raw = self._extract_explicit_ref(raw)
        if explicit_ref:
            ref_no = explicit_ref
        description = self.clean_description(raw)

        balance: Decimal | None
        if amount3 is not None:
            # Three slots: withdrawal deposit closing.
            debit = amount1
            credit = amount2
            balance = amount3
        else:
            # Two slots: amount closing (one of debit/credit is blank).
            balance = amount2
            if self._is_credit(description):
                credit, debit = amount1, None
            else:
                debit, credit = amount1, None

        if balance is None or (debit is None and credit is None):
            return None

        return Transaction(
            date=txn_date,
            description=description,
            debit=debit,
            credit=credit,
            balance=balance,
            ref_no=ref_no,
            category="credit" if credit else "debit",
        )

    def _strip_value_dates(self, text: str) -> str:
        text = VALUE_DATE_PHRASE_RE.sub(" ", text)
        text = STANDALONE_DATE_RE.sub(" ", text)
        return re.sub(r"\bValue\s+Dt\b", " ", text, flags=re.IGNORECASE)

    def _extract_explicit_ref(self, text: str) -> tuple[str | None, str]:
        matches = list(REF_MARKER_RE.finditer(text))
        if not matches:
            return None, text
        last = matches[-1]
        ref = self._normalize_ref(last.group(1))
        stripped = text[: last.start()] + text[last.end() :]
        return ref, stripped

    def _normalize_ref(self, ref: str) -> str | None:
        if not ref:
            return None
        if re.fullmatch(r"\d+", ref):
            stripped = ref.lstrip("0")
            return stripped or None
        return ref

    def _is_credit(self, narration: str) -> bool:
        upper = narration.upper()
        if re.search(r"\bDR\b|(?<![A-Z])DR[- ]|(?<![A-Z])D[- ]", upper):
            return False
        return bool(
            re.search(
                r"\bCR\b|(?<![A-Z])CR[- ]|(?<![A-Z])C[- ]" r"|REFUND|SALARY|DEPOSIT|INWARD|CREDIT",
                upper,
            )
        )


class HDFCCreditCardParser(HDFCParser):
    bank_code = "hdfc_cc"
    bank_name = "HDFC Bank Credit Card"

    CC_HEADER_RE = re.compile(
        r"\bDATE\s*&\s*TIME\b[^\n]*\bTRANSACTION\s+DESCRIPTION\b[^\n]*\bAMOUNT\b",
        re.IGNORECASE,
    )
    CC_ROW_RE = re.compile(r"^(\d{2}/\d{2}/\d{4})\|\s*(?:\d{2}:\d{2}\s*)?(.*)$")
    CC_AMOUNT_TAIL = [
        re.compile(r"\s*\+\s*[\d,]*\s*C\s+([\d,]+\.\d{2})\s*l?\s*$"),
        re.compile(r"\s*C\s+([\d,]+\.\d{2})\s*l?\s*$"),
        re.compile(r"\s+([\d,]+\.\d{2})\s*l?\s*$"),
    ]
    CC_BLOCK_END_RE = re.compile(
        r"^(?:TOTAL\s+AMOUNT|Eligible\s+for\s+EMI|Rewards\s+Program|Offers\s+on"
        r"|Page\s+\d+\s+of|Past\s+Dues|Convert\s+to\s+EMI|IMPORTANT\s+INFORMATION"
        r"|Important\s+Information)",
        re.IGNORECASE,
    )
    CC_CREDIT_RE = re.compile(
        r"REFUND|CASHBACK|\bCC\s+PAYMENT\b|\bBILL\s+PAYMENT\b|\bPAYMENT\s+RECEIVED\b|REWARD",
        re.IGNORECASE,
    )

    def parse(self) -> Statement:
        pages_text = self.extract_text()
        return self._parse_statement(pages_text, "\n".join(pages_text))

    def _parse_statement(self, pages_text: list[str], full_text: str) -> Statement:
        self.statement.account_number = self._extract_cc_account_number(full_text)
        self.statement.account_type = "Credit Card"
        self.statement.statement_period_start, self.statement.statement_period_end = (
            self._extract_period(full_text)
        )
        self.statement.transactions = self._parse_cc_transactions(pages_text)
        return self.statement

    def _extract_cc_account_number(self, text: str) -> str | None:
        labeled = re.search(r"Credit\s+Card\s+No\.?\s*\n?\s*([\dX]{16})", text)
        if labeled and "X" in labeled.group(1):
            return labeled.group(1)
        for match in re.finditer(r"([\dX]{16})", text):
            if "X" in match.group(1):
                return match.group(1)
        return None

    def _parse_cc_transactions(self, pages_text: list[str]) -> list[Transaction]:
        transactions: list[Transaction] = []
        for page_text in pages_text:
            transactions.extend(self._parse_cc_page(page_text))
        return transactions

    def _parse_cc_page(self, page_text: str) -> list[Transaction]:
        transactions: list[Transaction] = []
        header = self.CC_HEADER_RE.search(page_text)
        if not header:
            return transactions
        lines = page_text[header.end() :].split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            row_start = self.CC_ROW_RE.match(line)
            if not row_start:
                i += 1
                continue

            block = [line]
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if not next_line:
                    i += 1
                    continue
                if self.CC_ROW_RE.match(next_line):
                    break
                if self.CC_BLOCK_END_RE.match(next_line):
                    break
                block.append(next_line)
                i += 1

            txn = self._parse_cc_block(block)
            if txn:
                transactions.append(txn)
        return transactions

    def _parse_cc_block(self, block: list[str]) -> Transaction | None:
        row_start = self.CC_ROW_RE.match(block[0])
        if not row_start:
            return None
        txn_date_dt = self.parse_date(row_start.group(1))
        if txn_date_dt is None:
            return None
        txn_date = txn_date_dt.date()

        last = block[-1].strip()
        search_target = row_start.group(2) if len(block) == 1 else last
        amounts_match = None
        for pat in self.CC_AMOUNT_TAIL:
            amounts_match = pat.search(search_target)
            if amounts_match:
                break
        if amounts_match is None:
            return None
        amount = self.parse_amount(amounts_match.group(1))
        if amount is None:
            return None

        desc_last = search_target[: amounts_match.start()].strip()
        parts: list[str] = []
        for idx, line in enumerate(block):
            if idx == len(block) - 1:
                continue
            if idx == 0:
                line = row_start.group(2)
            line = line.strip()
            if line:
                parts.append(line)
        if desc_last:
            parts.append(desc_last)
        description = self.clean_description(" ".join(parts))

        ref_match = re.search(r"Ref\s*#\s*([A-Za-z0-9]+)", description)
        ref_no = ref_match.group(1) if ref_match else None

        if self.CC_CREDIT_RE.search(description):
            credit, debit = amount, None
        else:
            debit, credit = amount, None

        return Transaction(
            date=txn_date,
            description=description,
            debit=debit,
            credit=credit,
            balance=Decimal("0"),
            ref_no=ref_no,
            category="credit" if credit else "debit",
        )
