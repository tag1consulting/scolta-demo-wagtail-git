"""Plain Django views for the GitMastery demo.

The documentation itself is served by the Wagtail page tree; this module holds
the non-page routes (currently just the dedicated search page) that mirror the
Drupal demo's URL surface.
"""

from __future__ import annotations

from django.shortcuts import render


def search(request):
    """Dedicated search page, mirroring the Drupal demo's ``/search`` route.

    Renders the full Scolta search UI (``{% scolta_search %}``) in the main
    content area. scolta.js reads the ``?q=`` and ``f_*`` query params on load
    and auto-runs the search, so deep links like ``/search?q=interactive+rebase``
    (and the per-locale ``/es/search?q=...``) work without any server-side query
    handling. The route lives inside ``i18n_patterns`` so every language prefix
    resolves it.
    """
    return render(request, "docs/search_page.html")
