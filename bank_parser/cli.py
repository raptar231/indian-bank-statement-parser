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

from pathlib import Path
from typing import Any, cast

import pandas as pd  # type: ignore[import-untyped]
import typer
from rich.console import Console
from rich.table import Table

from bank_parser import __version__
from bank_parser.core import (
    list_banks,
    parse_csv_or_xlsx,
    parse_file,
    parse_statements,
    unlock_pdfs,
)
from bank_parser.logging import (
    get_logger,
    print_banner,
    redact,
    register_secret,
    ts_print,
)
from bank_parser.models import BalanceValidation, Statement
from bank_parser.paths import data_dirs

app = typer.Typer(
    name="parse-bank-statements",
    help="Parse Indian bank statement PDFs to structured CSV/JSON",
    add_completion=False,
)
console = Console()
logger = get_logger("bank_parser.cli")


def _print_validation(validation: BalanceValidation | None) -> None:
    if validation is None:
        return
    if validation.status == "ok":
        ts_print("[bright_green]Balance validation: OK[/bright_green]")
    elif validation.status == "skipped":
        ts_print(f"[yellow]Balance validation: skipped ({validation.reason})[/yellow]")
    else:
        ts_print("[red]Balance validation FAILED - statement may not be parsed correctly[/red]")
        ts_print(f"[red]  expected closing : {validation.expected_closing}[/red]")
        ts_print(f"[red]  calculated closing: {validation.calculated_closing}[/red]")
        ts_print(f"[red]  difference       : {validation.difference}[/red]")
        ts_print(f"[red]  total debits     : {validation.total_debits}[/red]")
        ts_print(f"[red]  total credits    : {validation.total_credits}[/red]")


def _format_statement(statement: Statement, fmt: str) -> Any:
    if fmt == "statement":
        return statement
    df = statement.to_dataframe()
    if fmt == "dataframe":
        return df
    if fmt == "xlsx":
        return statement.to_excel()
    if fmt == "yaml":
        return statement.to_yaml()
    return df.to_dict("records")


@app.command()
def parse(
    input_dir: Path | None = typer.Option(
        None, "--input-dir", "-i", help="Directory containing PDF statements"
    ),
    input_file: Path | None = typer.Option(
        None, "--input-file", "-f", help="Single PDF file to parse"
    ),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Output directory for parsed files"
    ),
    output_file: Path | None = typer.Option(
        None, "--output-file", help="Output file for single file parsing"
    ),
    bank: str | None = typer.Option(
        None, "--bank", "-b", help="Bank code (hdfc, icici, sbi, axis, pnb, kotak, dbs)"
    ),
    format: str = typer.Option(
        "csv", "--format", help="Output format: csv, json, xlsx, yaml, dataframe"
    ),
    input_format: str = typer.Option("pdf", "--input-format", help="Input format: pdf, csv, xlsx"),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON/YAML output"),
    reconcile_gstr2a: bool = typer.Option(
        False, "--reconcile-gstr2a", help="Generate GSTR-2A reconciliation output"
    ),
    gstin: str | None = typer.Option(None, "--gstin", help="GSTIN for GSTR-2A reconciliation"),
    strict: bool = typer.Option(
        False, "--strict", help="Exit with error when balance validation fails"
    ),
    list_banks_flag: bool = typer.Option(
        False, "--list-banks", help="List supported banks and exit"
    ),
    password: str | None = typer.Option(
        None, "--password", "-p", help="Password for password-protected PDF"
    ),
    unlock: bool = typer.Option(
        False, "--unlock", help="Remove the password from all PDFs in --input-dir using --password"
    ),
    serve: bool = typer.Option(
        False, "--serve", help="Start the web UI / API server instead of parsing"
    ),
    host: str = typer.Option(
        "0.0.0.0", "--host", help="Host to bind the web server to (with --serve)"
    ),
    port: int = typer.Option(8000, "--port", help="Port for the web server (with --serve)"),
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit"),
) -> None:
    if version:
        ts_print(f"parse-bank-statements {__version__}")
        raise typer.Exit()

    register_secret(password)
    data_dirs()
    print_banner(
        {
            "input-dir": input_dir,
            "input-file": input_file,
            "input-format": input_format,
            "output-dir": output_dir,
            "output-file": output_file,
            "bank": bank,
            "format": format,
            "pretty": pretty,
            "reconcile-gstr2a": reconcile_gstr2a,
            "gstin": gstin,
            "strict": strict,
            "list-banks": list_banks_flag,
            "password": password,
            "unlock": unlock,
            "serve": serve,
            "host": host,
            "port": port,
        },
        version=__version__,
    )

    if serve:
        from bank_parser.server import run_server

        run_server(host, port)
        return

    if unlock:
        if not password:
            ts_print("[red]Error: --password is required with --unlock[/red]")
            raise typer.Exit(1)
        if not input_dir:
            ts_print("[red]Error: --input-dir is required with --unlock[/red]")
            raise typer.Exit(1)
        if not input_dir.exists():
            ts_print(f"[red]Error: Directory not found: {input_dir}[/red]")
            raise typer.Exit(1)
        output_path = output_dir if output_dir else data_dirs()["unlocked"]
        try:
            logger.info("Unlocking PDFs in %s -> %s", input_dir, output_path)
            unlocked = unlock_pdfs(input_dir, output_path, password)
        except ValueError as e:
            ts_print(f"[red]Error: {redact(e)}[/red]")
            raise typer.Exit(1) from None
        for path in unlocked:
            logger.info("Unlocked %s", path.name)
            ts_print(f"[bright_green]Unlocked {path.name}[/bright_green]")
        logger.info("Unlocked %d PDF(s) to %s", len(unlocked), output_path)
        ts_print(f"[bright_green]Unlocked {len(unlocked)} PDF(s) to {output_path}[/bright_green]")
        return

    if list_banks_flag:
        banks = list_banks()
        table = Table(title="Supported Banks")
        table.add_column("Code", style="magenta")
        table.add_column("Name", style="bright_green")
        bank_names = {
            "hdfc": "HDFC Bank",
            "hdfc_cc": "HDFC Bank Credit Card",
            "icici": "ICICI Bank",
            "icici_cc": "ICICI Bank Credit Card",
            "sbi": "State Bank of India",
            "sbi_cc": "SBI Credit Card",
            "axis": "Axis Bank",
            "axis_cc": "Axis Bank Credit Card",
            "pnb": "Punjab National Bank",
            "kotak": "Kotak Mahindra Bank",
            "dbs": "DBS Bank India",
        }
        for code in banks:
            table.add_row(code, bank_names.get(code, code))
        ts_print()
        console.print(table)
        return

    if not bank:
        ts_print("[red]Error: --bank is required[/red]")
        raise typer.Exit(1)

    if not input_dir and not input_file:
        input_dir = data_dirs()["input"]
        ts_print(f"[dim]No input specified, using default directory {input_dir}[/dim]")

    if input_dir and input_file:
        ts_print("[red]Error: Cannot specify both --input-dir and --input-file[/red]")
        raise typer.Exit(1)

    if reconcile_gstr2a and not gstin:
        ts_print("[red]Error: --gstin is required when using --reconcile-gstr2a[/red]")
        raise typer.Exit(1)

    try:
        if input_file:
            if not input_file.exists():
                ts_print(f"[red]Error: File not found: {input_file}[/red]")
                raise typer.Exit(1)

            ts_print(f"[bright_green]Parsing {input_file} with {bank} parser...[/bright_green]")
            logger.info("Parsing %s with %s parser", input_file, bank)

            if input_format in ("csv", "xlsx"):
                statement = parse_csv_or_xlsx(input_file, bank)
            else:
                statement = cast(
                    Statement,
                    parse_file(
                        input_file,
                        bank=bank,
                        output_format="statement",
                        reconcile_gstr2a=False,
                        password=password,
                    ),
                )
            _print_validation(statement.validation)
            if strict and statement.validation and statement.validation.status == "failed":
                ts_print("[red]Error: balance validation failed (--strict)[/red]")
                raise typer.Exit(1)

            if reconcile_gstr2a:
                result = parse_file(
                    input_file,
                    bank=bank,
                    output_format=format,
                    reconcile_gstr2a=reconcile_gstr2a,
                    gstin=gstin,
                    password=password,
                )
            else:
                result = _format_statement(statement, format)

            if output_file:
                indent = 2 if pretty else None
                if format in ("dataframe", "csv"):
                    if hasattr(result, "to_csv"):
                        result.to_csv(str(output_file), index=False)
                    else:
                        # list[dict] case - convert to DataFrame first
                        pd.DataFrame(result).to_csv(str(output_file), index=False)
                elif format == "json":
                    indent = 2 if pretty else None
                    if hasattr(result, "to_json"):
                        result.to_json(
                            str(output_file), orient="records", date_format="iso", indent=indent
                        )
                    else:
                        import json

                        with open(str(output_file), "w") as f:
                            json.dump(result, f, default=str, indent=indent)
                elif format == "xlsx":
                    if isinstance(result, bytes):
                        output_file.write_bytes(result)
                    elif hasattr(result, "to_excel"):
                        # result is a Statement
                        result.to_excel(str(output_file))
                elif format == "yaml":
                    if isinstance(result, str):
                        output_file.write_text(result)
                    elif hasattr(result, "to_yaml"):
                        result.to_yaml(str(output_file))
                ts_print(f"[bright_green]Output saved to {output_file}[/bright_green]")
            else:
                indent = 2 if pretty else None
                if format == "dataframe":
                    if hasattr(result, "head"):
                        ts_print()
                        console.print(result.head(20))
                    else:
                        ts_print()
                        console.print(result)
                elif format == "csv":
                    if hasattr(result, "to_csv"):
                        ts_print()
                        console.print(result.to_csv(index=False))
                    else:
                        ts_print()
                        console.print(result)
                elif format == "json":
                    indent = 2 if pretty else None
                    if hasattr(result, "to_json"):
                        ts_print()
                        console.print(
                            result.to_json(orient="records", date_format="iso", indent=indent)
                        )
                    else:
                        import json

                        ts_print()
                        console.print(json.dumps(result, default=str, indent=indent))
                elif format == "xlsx":
                    ts_print("[dim]XLSX output requires --output-file[/dim]")
                elif format == "yaml":
                    if isinstance(result, str):
                        ts_print()
                        console.print(result)
                    elif result is not None and hasattr(result, "to_yaml"):
                        ts_print()
                        console.print(result.to_yaml())

        else:
            if not input_dir or not input_dir.exists():
                ts_print(f"[red]Error: Directory not found: {input_dir}[/red]")
                raise typer.Exit(1)

            ts_print(
                f"[bright_green]Parsing all files in {input_dir} with {bank} parser...[/bright_green]"
            )
            logger.info("Parsing all files in %s with %s parser", input_dir, bank)
            failures: list[Statement] = []

            def _report(stmt: Statement) -> None:
                _print_validation(stmt.validation)
                if strict and stmt.validation and stmt.validation.status == "failed":
                    failures.append(stmt)

            if input_format in ("csv", "xlsx"):
                # Parse CSV/XLSX files in directory
                input_path = Path(input_dir)
                pattern = "*.csv" if input_format == "csv" else "*.xlsx"
                files = list(input_path.glob(pattern))

                if not files:
                    raise ValueError(f"No {pattern} files found in {input_dir}")

                all_transactions = []
                all_statements = []
                for file in sorted(files):
                    try:
                        statement = parse_csv_or_xlsx(file, bank)
                        _report(statement)
                        all_statements.append(statement)
                        all_transactions.extend(statement.transactions)
                    except Exception as e:
                        logger.error("Failed to parse %s: %s", file, e)
                        if strict:
                            raise

                if not all_transactions:
                    raise ValueError("No transactions parsed from any file")

                combined_df = pd.DataFrame([t.to_dict() for t in all_transactions])
                combined_df = combined_df.sort_values("date").reset_index(drop=True)

                if output_dir:
                    output_path = Path(output_dir)
                    output_path.mkdir(parents=True, exist_ok=True)
                    if format == "xlsx":
                        output_file = output_path / f"parsed_{bank}.xlsx"
                        combined_statement = Statement(bank=bank, transactions=all_transactions)
                        combined_statement.to_excel(str(output_file))
                    else:
                        output_file = output_path / f"parsed_{bank}.csv"
                        combined_df.to_csv(output_file, index=False)

                if format == "dataframe":
                    result = combined_df
                elif format == "statement":
                    result = Statement(bank=bank, transactions=all_transactions)
                elif format == "csv":
                    result = combined_df.to_dict("records")
                elif format == "json":
                    result = combined_df.to_json(orient="records", date_format="iso")
                elif format == "xlsx":
                    result = Statement(bank=bank, transactions=all_transactions).to_excel()
                elif format == "yaml":
                    result = Statement(bank=bank, transactions=all_transactions).to_yaml()
                else:
                    raise ValueError(f"Unknown output format: {format}")
            else:
                result = parse_statements(
                    input_dir,
                    bank=bank,
                    output_format=format,
                    output_dir=output_dir,
                    reconcile_gstr2a=reconcile_gstr2a,
                    gstin=gstin,
                    on_file=_report,
                    password=password,
                )
            if strict and failures:
                ts_print(
                    "[red]Error: balance validation failed for one or more files (--strict)[/red]"
                )
                raise typer.Exit(1)

            if output_dir:
                ts_print(f"[bright_green]Output saved to {output_dir}[/bright_green]")
            else:
                indent = 2 if pretty else None
                if format == "dataframe":
                    if result is not None and hasattr(result, "head"):
                        ts_print()
                        console.print(result.head(20))
                    else:
                        ts_print()
                        console.print(result)
                elif format == "csv":
                    if result is not None and hasattr(result, "to_csv"):
                        ts_print()
                        console.print(result.to_csv(index=False))
                    else:
                        ts_print()
                        console.print(result)
                elif format == "json":
                    indent = 2 if pretty else None
                    if result is not None and hasattr(result, "to_json"):
                        ts_print()
                        console.print(
                            result.to_json(orient="records", date_format="iso", indent=indent)
                        )
                    else:
                        import json

                        ts_print()
                        console.print(json.dumps(result, default=str, indent=indent))

        ts_print("[bright_green]Done![/bright_green]")

    except ValueError as e:
        ts_print(f"[red]Error: {redact(e)}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        ts_print(f"[red]Unexpected error: {redact(e)}[/red]")
        raise typer.Exit(1) from None


if __name__ == "__main__":
    app()
