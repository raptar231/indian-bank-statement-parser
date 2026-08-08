# GitHub Actions CI/CD

## Workflows Overview

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push, PR | Lint, type-check, test |
| `docker.yml` | Push, tags | Build & push Docker image |
| `release-on-tag.yml` | Tag `v*` | Full release: test → PyPI → Docker → GitHub Release (version read from `pyproject.toml`) |
| `license-header.yml` | Push, manual | Auto-add Apache headers |
| `update-copyright-year.yml` | Annual (Jan 1) | Update copyright year |

## CI Workflow (`ci.yml`)

```yaml
# Runs on every push/PR
jobs:
  lint:
    - ruff check
    - black --check
    - mypy
  tests:
    - pytest on Python 3.10, 3.11, 3.12, 3.13, 3.14
    - Coverage upload to Codecov
```

### Run Locally

```bash
# Lint
ruff check bank_parser/ tests/
black --check bank_parser/ tests/
mypy bank_parser/

# Test
pytest tests/ -v --cov=bank_parser
```

## Docker Workflow (`docker.yml`)

```yaml
# Push to main: build & test only
# Push tag v*: build & push to GHCR
```

### GHCR Image

```bash
docker pull ghcr.io/raptar231/indian-bank-statement-parser:latest
docker pull ghcr.io/raptar231/indian-bank-statement-parser:v0.1.0
```

## Release on Tag (`release-on-tag.yml`)

**Trigger:** Push tag matching `v*`

```bash
# 1. Update version in pyproject.toml
# version = "0.1.0"

# 2. Create and push tag
git tag v0.1.0
git push origin v0.1.0
```

**Pipeline:**
1. ✅ Validate tag format & matches `pyproject.toml`
2. ✅ Run full test suite
3. ✅ Build Python package
4. ✅ Publish to PyPI (Trusted Publishing)
5. ✅ Build & push Docker image to GHCR
6. ✅ Create GitHub Release with changelog

### PyPI Trusted Publishing Setup

1. Go to [PyPI Publishing Settings](https://pypi.org/manage/account/publishing/)
2. Add trusted publisher:
   - Owner: `raptar231`
   - Repository: `indian-bank-statement-parser`
   - Workflow: `release-on-tag.yml`
   - Environment: `pypi`
3. Create GitHub Environment `pypi` (Settings → Environments → New)

## Version Bump

Bump `pyproject.toml` version, commit, and push a matching `vX.Y.Z` tag:

```bash
git add pyproject.toml
git commit -m "chore: bump version to 0.2.0"
git tag v0.2.0
git push origin v0.2.0
```

The tag push triggers `release-on-tag.yml`, which reads the version from `pyproject.toml`.

## License Header Workflow (`license-header.yml`)

Auto-adds Apache 2.0 headers using `apache/skywalking-eyes`.

**Trigger:** Push to main, or manual

```yaml
# Creates PR with header fixes
```

Config: `.licenserc.yaml`

## Copyright Year Workflow (`update-copyright-year.yml`)

**Trigger:** Annual (Jan 1), or manual

```yaml
# Updates copyright-year in .licenserc.yaml
# Updates headers in source files
# Creates PR
```

## Required Secrets

| Secret | Purpose | Workflow |
|--------|---------|----------|
| `GITHUB_TOKEN` | Auto-provided | All |

## Environments

| Environment | Protection | Workflow |
|-------------|------------|----------|
| `pypi` | Required for PyPI publish | release-on-tag.yml |

## Status Badges

```markdown
[![CI](https://github.com/raptar231/indian-bank-statement-parser/actions/workflows/ci.yml/badge.svg)](https://github.com/raptar231/indian-bank-statement-parser/actions/workflows/ci.yml)
[![Docker](https://github.com/raptar231/indian-bank-statement-parser/actions/workflows/docker.yml/badge.svg)](https://github.com/raptar231/indian-bank-statement-parser/actions/workflows/docker.yml)
```

## See Also

- [Docker Deployment](../deployment/docker.md)
- [PyPI Release](../deployment/pypi_release.md)