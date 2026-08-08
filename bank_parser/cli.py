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

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from bank_parser.core import list_banks, parse_file, parse_statements
from bank_parser.models import BalanceValidation, Statement

app = typer.Typer(
    name="parse-bank-statements",
    help="Parse Indian bank statement PDFs to structured CSV/JSON",
    add_completion=False,
)
console = Console()


def _print_validation(validation: BalanceValidation | None) -> None:
    if validation is None:
        return
    if validation.status == "ok":
        rprint("[green]Balance validation: OK[/green]")
    elif validation.status == "skipped":
        rprint(f"[yellow]Balance validation: skipped ({validation.reason})[/yellow]")
    else:
        rprint("[red]Balance validation FAILED - statement may not be parsed correctly[/red]")
        rprint(f"[red]  expected closing : {validation.expected_closing}[/red]")
        rprint(f"[red]  calculated closing: {validation.calculated_closing}[/red]")
        rprint(f"[red]  difference       : {validation.difference}[/red]")
        rprint(f"[red]  total debits     : {validation.total_debits}[/red]")
        rprint(f"[red]  total credits    : {validation.total_credits}[/red]")


def _format_statement(statement: Statement, fmt: str) -> Any:
    if fmt == "statement":
        return statement
    df = statement.to_dataframe()
    if fmt == "dataframe":
        return df
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
    format: str = typer.Option("csv", "--format", help="Output format: csv, json, dataframe"),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output"),
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
) -> None:
    if list_banks_flag:
        banks = list_banks()
        table = Table(title="Supported Banks")
        table.add_column("Code", style="cyan")
        table.add_column("Name", style="green")
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
        console.print(table)
        return

    if not bank:
        rprint("[red]Error: --bank is required[/red]")
        raise typer.Exit(1)

    if not input_dir and not input_file:
        rprint("[red]Error: Either --input-dir or --input-file is required[/red]")
        raise typer.Exit(1)

    if input_dir and input_file:
        rprint("[red]Error: Cannot specify both --input-dir and --input-file[/red]")
        raise typer.Exit(1)

    if reconcile_gstr2a and not gstin:
        rprint("[red]Error: --gstin is required when using --reconcile-gstr2a[/red]")
        raise typer.Exit(1)

    try:
        if input_file:
            if not input_file.exists():
                rprint(f"[red]Error: File not found: {input_file}[/red]")
                raise typer.Exit(1)

            rprint(f"[green]Parsing {input_file} with {bank} parser...[/green]")
            statement = cast(
                Statement,
                parse_file(
                    input_file,
                    bank=bank,
                    output_format="statement",
                    reconcile_gstr2a=False,
                ),
            )
            _print_validation(statement.validation)
            if strict and statement.validation and statement.validation.status == "failed":
                rprint("[red]Error: balance validation failed (--strict)[/red]")
                raise typer.Exit(1)

            if reconcile_gstr2a:
                result = parse_file(
                    input_file,
                    bank=bank,
                    output_format=format,
                    reconcile_gstr2a=reconcile_gstr2a,
                    gstin=gstin,
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
                        import pandas as pd  # type: ignore[import-untyped]

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
                rprint(f"[green]Output saved to {output_file}[/green]")
            else:
                indent = 2 if pretty else None
                if format == "dataframe":
                    if hasattr(result, "head"):
                        console.print(result.head(20))
                    else:
                        console.print(result)
                elif format == "csv":
                    if hasattr(result, "to_csv"):
                        console.print(result.to_csv(index=False))
                    else:
                        console.print(result)
                elif format == "json":
                    indent = 2 if pretty else None
                    if hasattr(result, "to_json"):
                        console.print(
                            result.to_json(orient="records", date_format="iso", indent=indent)
                        )
                    else:
                        import json

                        console.print(json.dumps(result, default=str, indent=indent))

        else:
            if not input_dir or not input_dir.exists():
                rprint(f"[red]Error: Directory not found: {input_dir}[/red]")
                raise typer.Exit(1)

            rprint(f"[green]Parsing all PDFs in {input_dir} with {bank} parser...[/green]")
            failures: list[Statement] = []

            def _report(stmt: Statement) -> None:
                _print_validation(stmt.validation)
                if strict and stmt.validation and stmt.validation.status == "failed":
                    failures.append(stmt)

            result = parse_statements(
                input_dir,
                bank=bank,
                output_format=format,
                output_dir=output_dir,
                reconcile_gstr2a=reconcile_gstr2a,
                gstin=gstin,
                on_file=_report,
            )
            if strict and failures:
                rprint(
                    "[red]Error: balance validation failed for one or more files (--strict)[/red]"
                )
                raise typer.Exit(1)

            if output_dir:
                rprint(f"[green]Output saved to {output_dir}[/green]")
            else:
                indent = 2 if pretty else None
                if format == "dataframe":
                    if hasattr(result, "head"):
                        console.print(result.head(20))
                    else:
                        console.print(result)
                elif format == "csv":
                    if hasattr(result, "to_csv"):
                        console.print(result.to_csv(index=False))
                    else:
                        console.print(result)
                elif format == "json":
                    indent = 2 if pretty else None
                    if hasattr(result, "to_json"):
                        console.print(
                            result.to_json(orient="records", date_format="iso", indent=indent)
                        )
                    else:
                        import json

                        console.print(json.dumps(result, default=str, indent=indent))

        rprint("[green]Done![/green]")

    except ValueError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1) from None


if __name__ == "__main__":
    app()
