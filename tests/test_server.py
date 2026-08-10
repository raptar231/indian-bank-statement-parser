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

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pymupdf
import pytest
from fastapi.testclient import TestClient

from bank_parser.paths import data_dirs
from bank_parser.server import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def data_root(tmp_path, monkeypatch):
    monkeypatch.setenv("BANK_PARSER_DATA_DIR", str(tmp_path))
    data_dirs()
    return tmp_path


def test_index_serves_ui():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "parse-bank-statements" in resp.text
    assert resp.text.count("{{") == 0
    assert 'id="helpModal"' in resp.text
    assert "What you can do" in resp.text
    assert "toggleHelp" in resp.text


def test_banks_endpoint():
    resp = client.get("/api/banks")
    assert resp.status_code == 200
    assert "hdfc" in resp.json()["banks"]
    assert "icici" in resp.json()["banks"]


def test_dirs_endpoint(data_root):
    resp = client.get("/api/dirs")
    assert resp.status_code == 200
    dirs = resp.json()
    assert dirs["input"] == str(data_root / "input")
    assert dirs["output"] == str(data_root / "output")
    assert dirs["unlocked"] == str(data_root / "unlocked")


def test_download_blocks_traversal():
    resp = client.get("/api/download/..%2Fpyproject.toml")
    assert resp.status_code == 404


def test_parse_rejects_garbage_file(data_root):
    bad = data_root / "input" / "garbage.pdf"
    bad.write_bytes(b"this is not a pdf")
    with open(bad, "rb") as f:
        resp = client.post(
            "/api/parse",
            files={"file": ("garbage.pdf", f, "application/pdf")},
            data={"bank": "hdfc", "format": "json"},
        )
    assert resp.status_code in (400, 500)


def _make_locked_pdf(path: Path, password: str) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Confidential statement")
    doc.save(str(path), encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password)
    doc.close()


def test_unlock_roundtrip(data_root):
    src = data_root / "input" / "locked.pdf"
    _make_locked_pdf(src, "secret123")
    with open(src, "rb") as f:
        resp = client.post(
            "/api/unlock",
            files={"files": ("locked.pdf", f, "application/pdf")},
            data={"password": "secret123"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert [u["name"] for u in data["unlocked"]] == ["locked.pdf"]
    assert data["failed"] == []
    assert data["skipped"] == []

    unlocked = data_root / "unlocked" / "locked.pdf"
    assert unlocked.is_file()

    stored = data_root / "output" / "locked.pdf"
    assert stored.is_file()

    doc = pymupdf.open(str(unlocked))
    try:
        assert not doc.needs_pass
        assert "Confidential" in doc.load_page(0).get_text()
    finally:
        doc.close()


def test_unlock_rejects_wrong_password(data_root):
    src = data_root / "input" / "locked.pdf"
    _make_locked_pdf(src, "secret123")
    with open(src, "rb") as f:
        resp = client.post(
            "/api/unlock",
            files={"files": ("locked.pdf", f, "application/pdf")},
            data={"password": "wrong"},
        )
    assert resp.status_code == 400


def test_parse_requires_bank():
    resp = client.post(
        "/api/parse",
        files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
        data={"format": "json"},
    )
    assert resp.status_code == 422


def test_unlock_without_password_succeeds_on_unlocked_pdf(data_root):
    plain = data_root / "input" / "plain.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Plain statement")
    doc.save(str(plain))
    doc.close()
    with open(plain, "rb") as f:
        resp = client.post(
            "/api/unlock",
            files={"files": ("plain.pdf", f, "application/pdf")},
            data={},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert [u["name"] for u in data["unlocked"]] == ["plain.pdf"]
    assert data["failed"] == []


def test_unlock_protected_requires_password(data_root):
    src = data_root / "input" / "locked.pdf"
    _make_locked_pdf(src, "secret123")
    with open(src, "rb") as f:
        resp = client.post(
            "/api/unlock",
            files={"files": ("locked.pdf", f, "application/pdf")},
            data={},
        )
    assert resp.status_code == 400
    assert "Password required" in resp.json()["detail"]


def test_unlock_multiple_files_share_password(data_root):
    for name in ("a.pdf", "b.pdf"):
        _make_locked_pdf(data_root / "input" / name, "sharedpw")
    with (
        open(data_root / "input" / "a.pdf", "rb") as fa,
        open(data_root / "input" / "b.pdf", "rb") as fb,
    ):
        resp = client.post(
            "/api/unlock",
            files=[
                ("files", ("a.pdf", fa, "application/pdf")),
                ("files", ("b.pdf", fb, "application/pdf")),
            ],
            data={"password": "sharedpw"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert sorted(u["name"] for u in data["unlocked"]) == ["a.pdf", "b.pdf"]
    assert data["failed"] == []
    assert (data_root / "output" / "a.pdf").is_file()
    assert (data_root / "output" / "b.pdf").is_file()
    assert data["zip"] == "/api/unlock.zip?files=a.pdf,b.pdf"


def test_unlock_dir(data_root):
    _make_locked_pdf(data_root / "input" / "x.pdf", "pw123")

    resp = client.post("/api/unlock-dir", data={"password": "pw123"})
    assert resp.status_code == 200
    data = resp.json()
    assert [u["name"] for u in data["unlocked"]] == ["x.pdf"]
    assert data["skipped"] == []
    assert data["failed"] == []
    assert (data_root / "output" / "x.pdf").is_file()

    resp2 = client.post("/api/unlock-dir", data={"password": "pw123"})
    data2 = resp2.json()
    assert data2["unlocked"] == []
    assert data2["skipped"] == [{"name": "x.pdf", "reason": "already unlocked"}]


def test_unlock_dir_no_pdfs(data_root):
    resp = client.post("/api/unlock-dir", data={"password": "pw123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["unlocked"] == []
    assert data["skipped"] == []
    assert data["failed"] == []
    assert data["zip"] is None


def test_unlock_zip(data_root):
    _make_locked_pdf(data_root / "input" / "a.pdf", "pw")
    _make_locked_pdf(data_root / "input" / "b.pdf", "pw")
    with (
        open(data_root / "input" / "a.pdf", "rb") as fa,
        open(data_root / "input" / "b.pdf", "rb") as fb,
    ):
        resp = client.post(
            "/api/unlock",
            files=[
                ("files", ("a.pdf", fa, "application/pdf")),
                ("files", ("b.pdf", fb, "application/pdf")),
            ],
            data={"password": "pw"},
        )
    data = resp.json()
    assert data["zip"]

    zresp = client.get(data["zip"])
    assert zresp.status_code == 200
    assert zresp.headers["content-type"] == "application/zip"
    with ZipFile(BytesIO(zresp.content)) as zf:
        assert sorted(zf.namelist()) == ["a.pdf", "b.pdf"]
        for name in ("a.pdf", "b.pdf"):
            doc = pymupdf.open(stream=BytesIO(zf.read(name)))
            try:
                assert not doc.needs_pass
            finally:
                doc.close()
