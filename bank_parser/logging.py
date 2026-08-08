"""Logging setup for bank_parser with automatic password/secret redaction.

Secrets registered via :func:`register_secret` are replaced with ``***`` in
every log message and in any output produced through :func:`log_banner`, so a
password can never leak through logging or the startup banner.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich import print as rprint
from rich.box import MINIMAL_HEAVY_HEAD
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

REDACTION_MASK = "***"

LOG_FILE = Path("logs.txt")

_secrets: set[str] = set()

_logger_configured = False

_LEVEL_COLORS = {
    logging.DEBUG: "\x1b[36m",
    logging.INFO: "\x1b[37m",
    logging.WARNING: "\x1b[33m",
    logging.ERROR: "\x1b[31m",
    logging.CRITICAL: "\x1b[1;31m",
}
_RESET = "\x1b[0m"

ICON = r""" ╭───────────────────────────╮
 │  ┌─────────────────────┐  │
 │  │         ₹           │  │
 │  │  DATE     AMOUNT    │  │
 │  │  ──────   ──────    │  │
 │  │  01-JUL   500.00    │  │
 │  │  02-JUL   250.00    │  │
 │  │  03-JUL    20.75    │  │
 │  └─────────────────────┘  │
 ╰───────────────────────────╯
"""

WORDMARK = r"""                    _               _
 _ __  __ _ _ _ ___ ___  | |__  __ _ _ _ | |__
| '_ \/ _` | '_(_-</ -_) | '_ \/ _` | ' \| / /
| .__/\__,_|_| /__/\___| |_.__/\__,_|_||_|_\_\
|_|
    _        _                     _
 __| |_ __ _| |_ ___ _ __  ___ _ _| |_ ___
(_-<  _/ _` |  _/ -_) '  \/ -_) ' \  _(_-<
/__/\__\__,_|\__\___|_|_|_\___|_||_\__/__/
"""

ICON_STYLE = "bright_green"
WORDMARK_STYLE = "magenta"


def register_secret(secret: str | None) -> None:
    """Register a value (e.g. a password) to be redacted from all log output."""
    if secret:
        _secrets.add(str(secret))


def redact(text: Any) -> str:
    """Replace every registered secret found in ``text`` with ``***``."""
    value = str(text)
    for secret in _secrets:
        if secret and secret in value:
            value = value.replace(secret, REDACTION_MASK)
    return value


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        return redact(message)


class ColorLevelFormatter(RedactingFormatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        return f"{_LEVEL_COLORS.get(record.levelno, '')}{message}{_RESET}"


def _configure() -> None:
    global _logger_configured
    if _logger_configured:
        return
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(
        ColorLevelFormatter(
            "%(asctime)s %(name)s: %(message)s",
            datefmt="%d-%m-%y %H:%M:%S",
        )
    )
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(
        RedactingFormatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%d-%m-%y %H:%M:%S",
        )
    )
    root = logging.getLogger("bank_parser")
    root.addHandler(console_handler)
    root.addHandler(file_handler)
    root.setLevel(logging.INFO)
    root.propagate = False
    _logger_configured = True


def get_logger(name: str = "bank_parser") -> logging.Logger:
    _configure()
    return logging.getLogger(name)


def uvicorn_log_config() -> dict[str, Any]:
    """Return a ``logging`` dictConfig that routes uvicorn through our handlers.

    Web server access/error logs then follow the same conventions as the rest
    of the tool: coloured timestamps on the console and redacted lines in
    ``logs.txt``.
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {
                "()": "bank_parser.logging.ColorLevelFormatter",
                "format": "%(asctime)s %(name)s: %(message)s",
                "datefmt": "%d-%m-%y %H:%M:%S",
            },
            "file": {
                "()": "bank_parser.logging.RedactingFormatter",
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%d-%m-%y %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "stream": "ext://sys.stderr",
            },
            "file": {
                "class": "logging.FileHandler",
                "formatter": "file",
                "filename": str(LOG_FILE),
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
            "uvicorn.access": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }


def _banner_table(arguments: dict[str, Any]) -> Table:
    table = Table(
        box=MINIMAL_HEAVY_HEAD,
        show_header=False,
        show_edge=False,
        pad_edge=False,
        padding=(0, 2),
    )
    table.add_column("Section", style="bold magenta", justify="right")
    table.add_column("Argument", style="bold magenta")
    table.add_column("Value", style="bright_green")

    sections: list[tuple[str, list[str]]] = [
        ("Input", ["input-dir", "input-file"]),
        ("Output", ["output-dir", "output-file"]),
        ("Processing", ["bank", "format", "strict"]),
        ("Options", ["pretty", "reconcile-gstr2a", "gstin", "list-banks", "unlock"]),
        ("Server", ["serve", "host", "port"]),
        ("Security", ["password"]),
    ]
    for section, keys in sections:
        for i, key in enumerate(keys):
            value = redact(arguments.get(key))
            table.add_row(section if i == 0 else "", f"{key} ", str(value))
        if section != sections[-1][0]:
            table.add_section()
    return table


def log_banner(arguments: dict[str, Any], version: str | None = None) -> None:
    """Log a startup banner listing every CLI argument, passwords masked.

    Args:
        arguments: Mapping of argument names to their parsed values.
        version: Optional tool version shown in the banner header.
    """
    logger = get_logger("bank_parser.cli")
    logger.info("=" * 60)
    suffix = f" v{version}" if version else ""
    logger.info("parse-bank-statements%s invocation", suffix)
    logger.info("=" * 60)
    for key, value in arguments.items():
        logger.info("  %s = %s", key, redact(value))
    logger.info("-" * 60)


def _print_logo() -> None:
    icon_lines = ICON.rstrip("\n").split("\n")
    mark_lines = WORDMARK.rstrip("\n").split("\n")
    icon_w = max(len(line) for line in icon_lines)
    max_lines = max(len(icon_lines), len(mark_lines))

    icon_top = (max_lines - len(icon_lines)) // 2
    mark_top = (max_lines - len(mark_lines)) // 2

    console = Console()
    for i in range(max_lines):
        if icon_top <= i < icon_top + len(icon_lines):
            icon_line = icon_lines[i - icon_top].ljust(icon_w)
        else:
            icon_line = " " * icon_w
        if mark_top <= i < mark_top + len(mark_lines):
            mark_line = mark_lines[i - mark_top].rstrip()
        else:
            mark_line = ""
        console.print(
            Text(icon_line, style=ICON_STYLE)
            + Text("  ", style="dim")
            + Text(mark_line, style=WORDMARK_STYLE)
        )


def print_banner(arguments: dict[str, Any], version: str | None = None) -> None:
    """Print a startup banner to the console, passwords masked.

    Args:
        arguments: Mapping of argument names to their parsed values.
        version: Optional tool version shown in the banner header.
    """
    _print_logo()

    suffix = f" v{version}" if version else ""
    panel = Panel(
        _banner_table(arguments),
        title=f"[bold magenta]parse-bank-statements[/bold magenta] {suffix}",
        title_align="left",
        border_style="magenta",
        padding=(1, 2),
    )
    rprint(panel)


def safe_exit(message: str, code: int = 1) -> None:
    ts_print(f"[red]{redact(message)}[/red]")
    raise typer.Exit(code)


def timestamp() -> str:
    """Return the current time formatted as ``DD-MM-YY HH:MM:SS``."""
    return datetime.now().strftime("%d-%m-%y %H:%M:%S")


def ts_print(message: Any = "") -> None:
    """Print a message to stdout with a dim timestamp prefix."""
    rprint(f"[dim]{timestamp()}[/dim] {message}")
