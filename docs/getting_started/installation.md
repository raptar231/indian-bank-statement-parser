# Installation

Multiple installation methods for different workflows.

## pip (Standard)

```bash
# Basic install
pip install indian-bank-statement-parser

# With development dependencies
pip install -e ".[dev]"
```

## Poetry

```bash
# Add to project
poetry add indian-bank-statement-parser

# With dev dependencies
poetry add --group dev indian-bank-statement-parser

# Install from source (development)
git clone https://github.com/raptar231/indian-bank-statement-parser
cd indian-bank-statement-parser
poetry install --with dev,test,lint,docs
```

## UV (Fastest)

```bash
# Add to project
uv add indian-bank-statement-parser

# With all extras
uv sync --all-extras

# Specific extras
uv sync --extra dev --extra test --extra lint --extra docs

# Use UV script aliases
uv run parse-bank-statements --help
```

## Docker

```bash
# Pull image
docker pull ghcr.io/raptar231/indian-bank-statement-parser:latest

# Run CLI
docker run --rm \
  -v $(pwd)/statements:/input \
  -v $(pwd)/parsed:/output \
  ghcr.io/raptar231/indian-bank-statement-parser:latest \
  --input-dir /input --output-dir /output --bank hdfc
```

## Development Setup

```bash
git clone https://github.com/raptar231/indian-bank-statement-parser
cd indian-bank-statement-parser

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/ -v

# Run linting
ruff check bank_parser/ tests/
mypy bank_parser/
black --check bank_parser/ tests/
```

## Requirements

- Python 3.10+
- System dependencies: `poppler-utils` (for PDF text extraction)

### Ubuntu/Debian
```bash
sudo apt-get install poppler-utils
```

### macOS
```bash
brew install poppler
```

### Windows
```bash
# Use Docker or WSL2
```

## Verify Installation

```bash
# Check CLI
parse-bank-statements --list-banks

# Check Python API
python -c "from bank_parser import list_banks; print(list_banks())"
```

## Next Steps

- [Quickstart](quickstart.md) — Parse your first statement
- [CLI Reference](../user_guide/cli.md) — All commands
- [Python API](../user_guide/python_api.md) — Programmatic usage