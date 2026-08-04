# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- Core parser for HDFC, ICICI, SBI, Axis banks
- GSTR-2A reconciliation
- CLI and Python API
- Docker support
- GitHub Actions CI/CD

## [0.1.0] - 2024-08-05

### Added
- **Core Parsers**: HDFC, ICICI, SBI, Axis (Savings, Current, Credit Card)
- **Standardized Output**: Unified schema (`date`, `description`, `debit`, `credit`, `balance`, `ref_no`, `category`)
- **CLI**: `parse-bank-statements` with Typer
- **Python API**: `parse_file()`, `parse_statements()`, `list_banks()`
- **Models**: Pydantic v2 models (Transaction, Statement, GSTR2AEntry)
- **GSTR-2A Reconciliation**: Generate GST-compatible CSV
- **Plugin Architecture**: Add custom banks in ~50 lines
- **Docker**: Multi-platform images on GHCR
- **CI/CD**: GitHub Actions (lint, test, Docker, release)
- **Documentation**: MkDocs with Material theme

### Features
- Multi-bank support: HDFC, ICICI, SBI, Axis (Savings/Current/Credit Card)
- SBI regional variants support (20+ formats)
- GSTR-2A reconciliation output (18% GST, configurable)
- Offline-first: 100% local, no network calls
- Dual PDF engine: pdfplumber + pymupdf fallback
- Type-safe: Full mypy strict mode, Pydantic v2 validation

### Developer Experience
- Multiple install methods: pip, Poetry, UV
- Comprehensive docs: MkDocs with Material theme
- Code quality: ruff, black, mypy, pytest
- Pre-commit hooks
- Dependabot for dependency updates

### CI/CD
- Automated testing on Python 3.10, 3.11, 3.12, 3.13, 3.14
- Docker multi-platform builds (amd64, arm64)
- Automatic release on tag push
- PyPI Trusted Publishing (no tokens)
- GHCR Docker images
- Release Drafter for changelogs
- License header automation (apache/skywalking-eyes)
- Annual copyright year update

### Documentation
- MkDocs with Material theme
- Getting Started, User Guide, Developer Guide, Deployment
- CLI Reference, Python API, Supported Banks
- GSTR-2A Reconciliation guide
- Adding Bank Parser guide
- Architecture & Testing docs
- Docker, GitHub Actions, PyPI Release guides

---

## Release Process

See [PyPI Release](deployment/pypi_release.md) for details.

### Versioning
- Semantic Versioning (MAJOR.MINOR.PATCH)
- Tags: `v0.1.0`, `v1.0.0`, etc.
- Auto-changelog via Release Drafter

### Release Types
- **Automatic**: Bump `pyproject.toml` version, push tag `vX.Y.Z` → Full release (tests, PyPI, Docker, GitHub Release via `release-on-tag.yml`)

---

## Migration Guide

### From Pre-Release

This is the first release. No migration needed.

---

## Support

- [Issues](https://github.com/raptar231/indian-bank-statement-parser/issues)
- [Discussions](https://github.com/raptar231/indian-bank-statement-parser/discussions)
- [Security](https://github.com/raptar231/indian-bank-statement-parser/security/advisories)