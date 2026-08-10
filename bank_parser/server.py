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

"""FastAPI web server exposing the parser as a web UI + REST API.

Run with ``parse-bank-statements --serve``. Every core operation is exposed:
list banks, parse an uploaded statement, parse everything in the input
directory, unlock password-protected PDFs and download generated files.
"""

import shutil
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from bank_parser import __version__
from bank_parser.core import (
    list_banks,
    parse_file,
    parse_statements,
    pdf_needs_password,
    unlock_pdf,
)
from bank_parser.logging import get_logger, redact, register_secret, uvicorn_log_config
from bank_parser.models import BalanceValidation, Statement
from bank_parser.paths import data_dirs

logger = get_logger("bank_parser.server")

app = FastAPI(
    title="parse-bank-statements",
    version=__version__,
    description="Parse Indian bank statement PDFs to structured CSV/JSON.",
)

_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


def _validation_dict(validation: BalanceValidation | None) -> dict[str, Any] | None:
    if validation is None:
        return None
    return {
        "ok": validation.ok,
        "status": validation.status,
        "reason": validation.reason,
        "expected_closing": (
            float(validation.expected_closing) if validation.expected_closing is not None else None
        ),
        "calculated_closing": (
            float(validation.calculated_closing)
            if validation.calculated_closing is not None
            else None
        ),
        "difference": (float(validation.difference) if validation.difference is not None else None),
        "total_debits": (
            float(validation.total_debits) if validation.total_debits is not None else None
        ),
        "total_credits": (
            float(validation.total_credits) if validation.total_credits is not None else None
        ),
    }


def _statement_dict(statement: Statement) -> dict[str, Any]:
    return {
        "account_number": statement.account_number,
        "account_type": statement.account_type,
        "statement_period_start": (
            statement.statement_period_start.isoformat()
            if statement.statement_period_start is not None
            else None
        ),
        "statement_period_end": (
            statement.statement_period_end.isoformat()
            if statement.statement_period_end is not None
            else None
        ),
        "opening_balance": (
            float(statement.opening_balance) if statement.opening_balance is not None else None
        ),
        "closing_balance": (
            float(statement.closing_balance) if statement.closing_balance is not None else None
        ),
        "transactions": [t.to_dict() for t in statement.transactions],
        "validation": _validation_dict(statement.validation),
    }


def _save_upload(file: UploadFile) -> Path:
    input_dir = data_dirs()["input"]
    name = Path(file.filename or "statement.pdf").name
    dest = input_dir / name
    dest.write_bytes(file.file.read())
    logger.info("Saved upload to %s", dest)
    return dest


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/api/banks")
def banks() -> dict[str, Any]:
    return {"banks": list_banks()}


@app.get("/api/version")
def version() -> dict[str, str]:
    return {"version": __version__}


@app.get("/api/dirs")
def dirs() -> dict[str, str]:
    return {name: str(path) for name, path in data_dirs().items()}


@app.get("/api/download/{name}")
def download(name: str) -> FileResponse:
    output_dir = data_dirs()["output"]
    path = (output_dir / name).resolve()
    if output_dir.resolve() not in path.parents or not path.is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=path.name)


@app.post("/api/parse")
async def parse_upload(
    file: UploadFile = File(...),
    bank: str = Form(...),
    format: str = Form("json"),
    password: str | None = Form(None),
    gstin: str | None = Form(None),
    reconcile: bool = Form(False),
    output_filename: str | None = Form(None),
) -> dict[str, Any]:
    from bank_parser.models import Statement, Transaction

    register_secret(password)
    path = _save_upload(file)
    try:
        if reconcile:
            if not gstin:
                raise ValueError("GSTIN is required for GSTR-2A reconciliation")
            records = parse_file(
                path,
                bank,
                output_format="json",
                reconcile_gstr2a=True,
                gstin=gstin,
                password=password,
            )
            result = {"filename": path.name, "bank": bank, "gstr2a": records}
        else:
            statement = cast(
                Statement, parse_file(path, bank, output_format="statement", password=password)
            )
            result = {
                "filename": path.name,
                "bank": bank,
                "format": format,
                **_statement_dict(statement),
            }

        # If output_filename provided, save to output directory
        if output_filename and output_filename.strip():
            output_dir = data_dirs()["output"]
            output_dir.mkdir(parents=True, exist_ok=True)
            # Ensure extension matches format
            fname = output_filename.strip()
            if not fname.endswith(f".{format}"):
                fname = f"{fname}.{format}"
            out_path = output_dir / fname

            if format == "json":
                import json

                out_path.write_text(json.dumps(result, default=str, indent=2))
            elif format == "csv":
                import pandas as pd  # type: ignore[import-untyped]

                pd.DataFrame(result.get("transactions", [])).to_csv(out_path, index=False)
            elif format == "xlsx":
                transactions = result.get("transactions", [])
                stmt = Statement(bank=bank, transactions=[Transaction(**t) for t in transactions])  # type: ignore[arg-type]
                stmt.to_excel(str(out_path))
            elif format == "yaml":
                import yaml  # type: ignore[import-untyped]

                out_path.write_text(yaml.dump(result, default_flow_style=False, sort_keys=False))

            result["download_url"] = f"/api/download/{fname}"
            result["saved_as"] = fname

        return result
    except ValueError as e:
        raise HTTPException(400, redact(e)) from None
    except Exception as e:  # noqa: BLE001 - surface parse failures as 500s
        logger.error("Parse failed for %s: %s", path.name, redact(e))
        raise HTTPException(500, "Failed to parse the uploaded statement") from None


@app.get("/api/parse-dir")
def parse_directory(
    bank: str,
    format: str = "json",
    password: str | None = None,
    gstin: str | None = None,
    reconcile: bool = False,
) -> dict[str, Any]:
    register_secret(password)
    input_dir = data_dirs()["input"]
    output_dir = data_dirs()["output"]
    try:
        if reconcile:
            if not gstin:
                raise ValueError("GSTIN is required for GSTR-2A reconciliation")
            parse_statements(
                input_dir,
                bank,
                output_format="csv",
                output_dir=output_dir,
                reconcile_gstr2a=True,
                gstin=gstin,
                password=password,
            )
            records: list[dict] = []
            files = ["gstr2a_reconciliation.csv"]
        else:
            records = cast(
                list,
                parse_statements(
                    input_dir,
                    bank,
                    output_format="csv",
                    output_dir=output_dir,
                    password=password,
                ),
            )
            files = [f"parsed_{bank}.csv"]
        return {"bank": bank, "format": format, "records": records, "files": files}
    except ValueError as e:
        raise HTTPException(400, redact(e)) from None


@app.post("/api/unlock")
async def unlock_uploads(
    files: list[UploadFile] = File(...),
    password: str | None = Form(None),
) -> dict[str, Any]:
    """Unlock one or more uploaded PDFs that share the same password."""
    register_secret(password)
    unlocked: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    for file in files:
        path = _save_upload(file)
        try:
            unlocked.append(_unlock_result(path, password))
        except ValueError as e:
            failed.append({"name": path.name, "reason": redact(e)})
        except Exception as e:  # noqa: BLE001 - corrupt file etc.
            logger.error("Unlock failed for %s: %s", path.name, redact(e))
            failed.append({"name": path.name, "reason": "Failed to unlock"})
    return _unlock_response(unlocked, [], failed)


@app.post("/api/unlock-dir")
def unlock_directory(password: str | None = Form(None)) -> dict[str, Any]:
    """Unlock every PDF in the input directory with the same password."""
    register_secret(password)
    input_dir = data_dirs()["input"]
    unlocked: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    for path in sorted(input_dir.glob("*.pdf")):
        stored = data_dirs()["output"] / path.name
        try:
            already = stored.is_file() and not pdf_needs_password(stored)
        except Exception:  # noqa: BLE001 - corrupt stored copy
            already = False
        if already:
            skipped.append({"name": path.name, "reason": "already unlocked"})
            continue
        try:
            unlocked.append(_unlock_result(path, password))
        except ValueError as e:
            failed.append({"name": path.name, "reason": redact(e)})
        except Exception as e:  # noqa: BLE001 - corrupt input etc.
            logger.error("Unlock failed for %s: %s", path.name, redact(e))
            failed.append({"name": path.name, "reason": "Failed to unlock"})
    return _unlock_response(unlocked, skipped, failed)


@app.get("/api/unlock.zip")
def unlock_zip(files: str) -> StreamingResponse:
    """Download previously unlocked PDFs as a ZIP."""
    output_dir = data_dirs()["output"].resolve()
    with BytesIO() as buffer:
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in files.split(","):
                name = Path(name).name
                if not name:
                    continue
                path = (output_dir / name).resolve()
                if output_dir not in path.parents or not path.is_file():
                    continue
                archive.write(path, name)
        data = buffer.getvalue()
    if not data:
        raise HTTPException(404, "No files to download")
    return StreamingResponse(
        iter([data]),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="unlocked.zip"'},
    )


def _unlock_result(path: Path, password: str | None) -> dict[str, str]:
    """Unlock one PDF: save to unlocked/ and copy to output/."""
    out = data_dirs()["unlocked"] / path.name
    unlock_pdf(path, out, password)
    stored = data_dirs()["output"] / path.name
    shutil.copyfile(out, stored)
    logger.info("Unlocked %s -> %s (also stored in %s)", path.name, out, stored)
    return {"name": path.name, "stored": str(stored)}


def _unlock_response(
    unlocked: list[dict[str, str]],
    skipped: list[dict[str, str]],
    failed: list[dict[str, str]],
) -> dict[str, Any]:
    if not unlocked and not skipped and failed:
        raise HTTPException(400, failed[0]["reason"])
    names = ",".join(entry["name"] for entry in unlocked)
    return {
        "unlocked": unlocked,
        "skipped": skipped,
        "failed": failed,
        "zip": f"/api/unlock.zip?files={quote(names, safe=',')}" if names else None,
    }


def run_server(host: str, port: int) -> None:
    import socket

    import uvicorn  # lazy: web support is optional

    # Determine display URLs
    urls = []
    if host in ("0.0.0.0", "::"):
        urls.append(f"http://127.0.0.1:{port}")
        try:
            lan_ip = socket.gethostbyname(socket.gethostname())
            if lan_ip != "127.0.0.1":
                urls.append(f"http://{lan_ip}:{port}")
        except Exception:
            pass
    else:
        urls.append(f"http://{host}:{port}")

    logger.info("Starting web server on %s", " | ".join(urls))
    for name, path in data_dirs().items():
        logger.info("%s directory: %s", name, path)
    uvicorn.run(app, host=host, port=port, log_config=uvicorn_log_config(), log_level="info")


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>parse-bank-statements</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<header>
  <h1>&#8379; parse-bank-statements <span id="version"></span></h1>
  <span style="margin-left:auto">
    <button class="ghost" id="themeToggle" onclick="toggleTheme()">Light</button>
    <button class="ghost" onclick="toggleHelp()">Help</button>
  </span>
</header>
<main>
  <div class="card" id="dirsCard"><h2>Data directories</h2><ul id="dirs"></ul></div>

  <div class="grid">
    <div class="card">
      <h2>Parse statement</h2>
      <label>PDF file</label><input type="file" id="pf">
      <div class="row">
        <div><label>Bank</label><select id="pb"></select></div>
        <div><label>Format</label>
          <select id="pfmt"><option>json</option><option>csv</option><option>xlsx</option><option>yaml</option><option>dataframe</option></select>
        </div>
      </div>
      <label>Password (if protected)</label><input type="password" id="ppw" placeholder="optional">
      <label>GSTIN (GSTR-2A reconciliation)</label><input id="pgstin" placeholder="optional">
      <label><input type="checkbox" id="prec" style="width:auto"> Reconcile GSTR-2A</label>
      <label>Output filename (optional)</label><input id="pout" placeholder="e.g. parsed_hdfc  — saved to output/ & downloadable">
      <button onclick="parseFile()">Parse</button>
      <div id="presult"></div>
    </div>

    <div class="card">
      <h2>Parse input directory</h2>
      <p class="muted">Parses every PDF in the input directory and writes
      <code>parsed_&lt;bank&gt;.csv</code> to the output directory.</p>
      <label>Bank</label><select id="db"></select>
      <button onclick="parseDir()">Parse directory</button>
      <div id="dresult"></div>
    </div>
  </div>

  <div class="card">
    <h2>Unlock password-protected PDFs</h2>
    <p class="muted">Select one or more PDFs sharing the same password (leave
    the password empty if already unlocked). Unlocked files are stored in the
    output and unlocked directories.</p>
    <label>PDF files (multiple allowed)</label><input type="file" id="uf" multiple>
    <label>Password (shared)</label><input type="password" id="upw" placeholder="optional">
    <div class="row">
      <div><button onclick="unlock()">Unlock selected &amp; download ZIP</button></div>
      <div><button onclick="unlockDir()">Unlock all in input directory</button></div>
    </div>
    <div id="uresult"></div>
  </div>
</main>
<div class="modal" id="helpModal" role="dialog" aria-label="Help">
  <div class="modal-card">
    <h2>What you can do</h2>

    <h3>Parse statement</h3>
    <ul>
      <li>Pick a <b>bank</b> and a <b>format</b> (JSON, CSV or dataframe).</li>
      <li>Add the PDF <b>password</b> if the statement is protected.</li>
      <li>Optionally enter your <b>GSTIN</b> and tick <b>Reconcile GSTR-2A</b> to cross-check purchases.</li>
      <li>The parsed transactions appear below; the result can be downloaded from <code>output/</code>.</li>
    </ul>

    <h3>Parse input directory</h3>
    <ul>
      <li>Parses every PDF in the input directory with the chosen bank.</li>
      <li>Writes <code>parsed_&lt;bank&gt;.csv</code> to the output directory and links it for download.</li>
    </ul>

    <h3>Unlock PDFs</h3>
    <ul>
      <li>Select <b>one or more</b> PDFs sharing the same password and click
        <b>Unlock selected &amp; download ZIP</b>.</li>
      <li>Leave the password empty if the PDF has no password.</li>
      <li>Unlocked copies are stored in both <code>output/</code> and <code>unlocked/</code>.</li>
      <li><b>Unlock all in input directory</b> applies the same password to every
        PDF already present; already-unlocked files are skipped.</li>
    </ul>

    <h3>Downloads</h3>
    <ul>
      <li>Unlocked PDFs can be downloaded individually or as a ZIP.</li>
      <li>Every generated file in the output directory is downloadable.</li>
    </ul>

    <h3>Notes</h3>
    <ul>
      <li>The data directories at the top show where files live on disk.</li>
      <li>Password fields are never logged.</li>
      <li>Full REST API reference is available at <code>/docs</code>.</li>
    </ul>

    <div style="text-align:right"><button class="ghost" onclick="toggleHelp()">Close</button></div>
  </div>
</div>
<script src="/static/app.js"></script>
</body>
</html>
"""

INDEX_HTML = INDEX_HTML.replace("{{VERSION}}", __version__)
