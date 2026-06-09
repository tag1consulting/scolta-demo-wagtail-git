"""Browser-layer regression tests for the GitMastery search UI.

These drive a real headless browser against the running demo (default the DDEV
site; override with ``DEMO_BASE_URL``). They cover two bugs that no server-side
string check can see, because ``scolta.js`` renders the entire UI client-side:

* layout — the search UI must live in the page's main content, NOT inside the
  ``<header>`` (the old ``{% scolta_search %}`` in the header spilled a 2,000px
  results column over the homepage);
* i18n — loading ``/it/?q=…`` must auto-apply the Italian language filter so
  every result URL is under ``/it/``.

Requires Playwright + a chromium build (``pip install playwright`` then
``playwright install chromium``). Skips cleanly when either — or the running
demo — is unavailable, so ``ddev exec pytest`` (no browser in the container)
stays green.
"""

import os

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import sync_playwright  # noqa: E402

BASE_URL = os.environ.get("DEMO_BASE_URL", "https://gitmastery-django.ddev.site").rstrip("/")


def _browser(pw):
    try:
        return pw.chromium.launch()
    except Exception as exc:  # browser binary not installed
        pytest.skip(f"chromium unavailable (run: playwright install chromium): {exc}")


def _goto(page, url):
    try:
        page.goto(url, wait_until="networkidle", timeout=15000)
    except Exception as exc:  # demo not running / unreachable
        pytest.skip(f"demo unreachable at {url}: {exc}")


def test_search_ui_in_main_content_not_header():
    """`#scolta-search` must mount in <main>, not <header>; after a search the
    results column must not overlap the header band."""
    with sync_playwright() as pw:
        browser = _browser(pw)
        try:
            page = browser.new_page()
            _goto(page, BASE_URL + "/")
            page.wait_for_selector("#scolta-search #scolta-query", timeout=10000)

            placement = page.eval_on_selector(
                "#scolta-search",
                "el => ({inHeader: el.closest('header') !== null, "
                "inMain: el.closest('main') !== null})",
            )
            assert placement["inHeader"] is False, "search UI must not be inside <header>"
            assert placement["inMain"] is True, "search UI must be inside <main>"

            # Run a search and wait for result cards to render.
            page.fill("#scolta-query", "undo my last commit")
            page.press("#scolta-query", "Enter")
            page.wait_for_selector(".scolta-result-card", timeout=15000)

            boxes = page.evaluate(
                """() => {
                    const h = document.querySelector('header').getBoundingClientRect();
                    const r = document.querySelector('#scolta-results').getBoundingClientRect();
                    return {h: {top: h.top, bottom: h.bottom},
                            r: {top: r.top, bottom: r.bottom}};
                }"""
            )
            # Results must sit entirely below the header band (no vertical overlap).
            assert boxes["r"]["top"] >= boxes["h"]["bottom"] - 1, (
                f"results overlap the header: {boxes}"
            )
        finally:
            browser.close()


def test_locale_root_auto_filters_language():
    """`/it/?q=…` auto-applies the Italian language filter (auto_language_filter
    derives f_language from the locale root): every result URL is under /it/."""
    with sync_playwright() as pw:
        browser = _browser(pw)
        try:
            page = browser.new_page()
            _goto(page, BASE_URL + "/it/?q=annullare+commit")
            page.wait_for_selector(".scolta-result-card .scolta-result-title", timeout=15000)

            paths = page.eval_on_selector_all(
                ".scolta-result-card .scolta-result-title",
                "els => els.map(a => new URL(a.href).pathname)",
            )
            assert paths, "no results rendered for the Italian query"
            offenders = [p for p in paths if not p.startswith("/it/")]
            assert not offenders, f"non-/it/ results leaked into an Italian search: {offenders}"
        finally:
            browser.close()
