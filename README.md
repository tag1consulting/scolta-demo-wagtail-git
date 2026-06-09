# GitMastery (Wagtail) — Multilingual Git Documentation Site

A comprehensive Git documentation site built on **Wagtail**, showcasing
[Scolta](https://tag1consulting.com/scolta) AI-powered search across **1,426
pages in 5 languages** (EN/ES/FR/IT/DE).

This is the Django/Wagtail port of the Drupal `git-manual` demo, built on
[`scolta-python`](../../packages/scolta-python) (the Python binding + in-process
Pagefind indexer) and [`scolta-django`](../../packages/scolta-django) (the
Django/Wagtail adapter). It has feature parity with the Drupal demo: the same
content, the same five languages, the same Scolta configuration, and the same
search behavior.

---

## Prerequisites

- Python 3.10+ and [`uv`](https://docs.astral.sh/uv/) (for local development), **or** Docker (for the container build / smoke test)
- An **Anthropic API key** — needed for query expansion and the AI overview (search still works without it; the AI tier degrades gracefully)

---

## Quick Start (local, uv)

```bash
cd demos/git-manual-django
uv venv --python 3.12
uv pip install -e ".[dev]"          # resolves scolta + scolta-django from ../../packages

uv run python manage.py migrate
uv run python manage.py import_gitmastery   # imports all 1,426 pages (a few minutes)
uv run python manage.py scolta_build        # builds the Pagefind index (pure-Python indexer)
uv run python manage.py runserver
```

Open **http://127.0.0.1:8000/**. For live AI summaries:

```bash
SCOLTA_API_KEY=sk-ant-... uv run python manage.py runserver
```

Create a Wagtail admin user with `uv run python manage.py createsuperuser`; the
admin is at `/admin/` and includes a **Scolta Search** panel (rebuild + index
status).

## Quick Start (Docker / smoke test)

```bash
docker build -t gitmastery-django .
docker run --rm -p 8080:8080 -e SCOLTA_API_KEY=sk-ant-... gitmastery-django
# open http://localhost:8080/
```

The image migrates, imports the full corpus, and builds the index at build time,
so the container is ready immediately. The smoke test wraps this:

```bash
bash tests/smoke-test.sh
```

---

## What's Inside

### Content

| Section | EN pages | Total (×5 languages) |
|---|---|---|
| Getting Started, Core Concepts, Commands Reference, Advanced, Performance, Tips, Comparisons, Tutorials | 285 | 1,425 |
| About This Demo (EN) | 1 | 1 |
| **Total indexed** | | **1,426** |

285 English pages across four content types — **200** documentation pages,
**50** tips, **20** tutorials, **15** comparisons — plus full translations into
Spanish, French, Italian, and German. The corpus lives in `content/` (committed)
and is identical to the Drupal demo's `import/` YAML.

**Content model (Drupal → Wagtail):**

| Drupal content type | Wagtail page model | Extra fields |
|---|---|---|
| `documentation_page` | `DocumentationPage` | section, difficulty, git_version, weight |
| `tutorial` | `Tutorial` | + estimated_time |
| `comparison` | `Comparison` | + compared_systems, verdict |
| `tip` | `Tip` | + topic |
| `page` (About) | `AboutPage` | body only |

The Drupal taxonomies/fields (`section`, `difficulty`, `topic`, `git_version`,
`weight`) become search **filters** and **sortables** in each model's
`to_searchable_content()` — the exact equivalent of the Drupal
`gitmastery_scolta_scolta_content_item_alter()` hook.

### Search

Scolta provides AI-enhanced search powered by [Pagefind](https://pagefind.app/)
(client-side WASM) plus the Anthropic Claude API for **query expansion**, an **AI
overview**, and **follow-up questions**. Configuration lives entirely in the
`SCOLTA` dict in `gitmastery/settings.py` — a flat mirror of the Drupal demo's
`config/sync/scolta.settings.yml` (`preset: reference`, the same scoring
overrides, the same `section`/`difficulty`/`topic`/`git_version` filter fields,
and `language: en` so every page lands in one Pagefind bucket — which is how the
index reports ~1,426 pages and the smoke test's ≥1,400 bar holds).

### Showcase Queries

| Query | Language | What Scolta does |
|---|---|---|
| "undo my last commit" | EN | Expands to reset/revert/amend; AI overview of options |
| "how to delete a branch" | EN | Surfaces `git branch -d`, `push --delete` |
| "slow git" | EN | Finds performance section: partial clone, sparse checkout, LFS |
| "comment annuler un commit" | FR | French expansion + French AI overview |
| "sistema di controllo versione distribuito" | IT | Italian expansion → Italian pages |
| "Änderungen rückgängig machen" | DE | German expansion + German results |
| "cómo ver el historial" | ES | Spanish expansion → log/shortlog/reflog pages |

To test a non-English query, switch language first (e.g. `/it/`) then search.

---

## Architecture Notes

- **Indexer:** the pure-Python in-process Pagefind indexer (`indexer: auto`) — no
  Pagefind binary required (the Drupal demo used `indexer: php`).
- **Content source:** the four content models + `AboutPage` are listed in
  `SCOLTA["models"]`, so the `DjangoContentSource` indexes them and each model's
  `to_searchable_content()` controls its filters/sortables. `HomePage` is *not*
  listed (it's a landing page, like the Drupal front view — not indexed), which
  keeps the index at exactly 1,426.
- **i18n:** Wagtail's built-in internationalization. Translations are real page
  instances linked by `translation_key`; the locale URL prefix (`/es/`, `/fr/`,
  …) is served via `i18n_patterns`. The header language switcher resolves the
  current page's translation per locale.
- **Asset + index serving:** `scolta.js`/CSS/WASM are served from the installed
  `scolta` package at `/scolta-assets/`; the built Pagefind index is served at
  `/pagefind/`. In Docker, WhiteNoise serves both.

### Migrations

The `docs` app migration is committed (`docs/migrations/0001_initial.py`), so
setup is just `migrate` — no `makemigrations` step is needed locally or in the
Docker build.

---

## Tests

```bash
# Unit tests (models, content source, import pipeline)
uv run pytest

# Docker smoke test — builds the image and asserts the index reports ≥1,400 pages
bash tests/smoke-test.sh
```

The smoke test is the direct port of the Drupal demo's `tests/smoke-test.sh`
(same ≥1,400-page assertion). The pytest suite adds coverage for the
filter/sortable mapping, the live-only searchable queryset, the content source,
and the translation-linking import pipeline.

---

See `SOURCES.md` for content provenance and licensing.
