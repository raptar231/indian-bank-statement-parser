# GitHub Pages Deployment

The docs are served at [raptar231.github.io/indian-bank-statement-parser](https://raptar231.github.io/indian-bank-statement-parser/) using **versioned docs** via [mike](https://github.com/jimporter/mike).

## How it works

`.github/workflows/docs.yml` deploys on:

- **Tag push (`v*`)** — deploys `$VERSION` from the tag, aliased as `latest` (e.g. `0.2.0 [latest]`)
- **Push to `master`** — updates the `latest` alias with the current docs
- **Manual** — via the Actions tab

`mike` commits the built site to the `gh-pages` branch, so every version stays available
(e.g. `.../0.1.0/`, `.../latest/`).

## Prerequisites (one-time)

1. **GitHub repo → Settings → Pages**
   - Source: **Deploy from a branch**
   - Branch: `gh-pages` / `/(root)`
2. Nothing else — the workflow has `contents: write` permission and commits directly to `gh-pages`.

## Local preview

```bash
pip install -e ".[docs]"
mkdocs serve          # http://127.0.0.1:8000
```

## Building docs locally

```bash
mkdocs build
```

Output goes to `site/` (gitignored).

## Version selector

The dropdown is enabled by `extra.version.provider: mike` in `mkdocs.yml`.
`latest` always points at the newest released tag via `mike set-default --push latest`.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Page 404 at project root | Run the workflow once (tag or manual), then `mike set-default --push latest` |
| `Deploy docs` failed | Check `gh-pages` branch exists after first deploy; Pages source must be `gh-pages` |
| Docs not updating on tag | Ensure tag matches `pyproject.toml` version (`release-on-tag.yml` enforces this) |

## See Also

- [Docker Deployment](../deployment/docker.md)
- [PyPI Release](../deployment/pypi_release.md)
