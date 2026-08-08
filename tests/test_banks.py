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

raptar231)/raptar231)
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

from pathlib import Path

from bank_parser.banks import BANK_PARSERS, detect_bank

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_bank_parsers_exist():
    expected = [
        "hdfc",
        "hdfc_cc",
        "icici",
        "icici_cc",
        "sbi",
        "sbi_cc",
        "axis",
        "axis_cc",
        "pnb",
        "kotak",
        "dbs",
    ]
    for bank in expected:
        assert bank in BANK_PARSERS


def test_hdfc_parser_instantiation():
    from bank_parser.banks.hdfc import HDFCCreditCardParser, HDFCParser

    parser = HDFCParser("dummy.pdf")
    assert parser.bank_code == "hdfc"
    assert parser.bank_name == "HDFC Bank"

    cc_parser = HDFCCreditCardParser("dummy.pdf")
    assert cc_parser.bank_code == "hdfc_cc"


def test_icici_parser_instantiation():
    from bank_parser.banks.icici import ICICIParser

    parser = ICICIParser("dummy.pdf")
    assert parser.bank_code == "icici"
    assert parser.bank_name == "ICICI Bank"


def test_sbi_parser_instantiation():
    from bank_parser.banks.sbi import SBIParser

    parser = SBIParser("dummy.pdf")
    assert parser.bank_code == "sbi"
    assert parser.bank_name == "State Bank of India"


def test_axis_parser_instantiation():
    from bank_parser.banks.axis import AxisParser

    parser = AxisParser("dummy.pdf")
    assert parser.bank_code == "axis"
    assert parser.bank_name == "Axis Bank"


def test_pnb_parser_instantiation():
    from bank_parser.banks.pnb import PNBParser

    parser = PNBParser("dummy.pdf")
    assert parser.bank_code == "pnb"
    assert parser.bank_name == "Punjab National Bank"


def test_kotak_parser_instantiation():
    from bank_parser.banks.kotak import KotakParser

    parser = KotakParser("dummy.pdf")
    assert parser.bank_code == "kotak"
    assert parser.bank_name == "Kotak Mahindra Bank"


def test_dbs_parser_instantiation():
    from bank_parser.banks.dbs import DBSParser

    parser = DBSParser("dummy.pdf")
    assert parser.bank_code == "dbs"
    assert parser.bank_name == "DBS Bank India"


def test_detect_bank_resolves_all_fixtures():
    for fixture in sorted(FIXTURES_DIR.glob("*/*.txt")):
        text = fixture.read_text(encoding="utf-8")
        assert detect_bank(text) == fixture.parent.name, (
            f"{fixture.name} should be detected as {fixture.parent.name}, "
            f"got {detect_bank(text)!r}"
        )
