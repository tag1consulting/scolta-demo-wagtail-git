"""URL configuration for the GitMastery Wagtail demo.

Non-prefixed routes (asset + index static serving, the Scolta AI endpoints, the
Wagtail/Django admins) come first; the Wagtail page tree is served under
``i18n_patterns`` so each locale gets a URL prefix (``/es/``, ``/fr/`` ...),
mirroring the Drupal demo's language paths.
"""

from pathlib import Path

import scolta
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from docs import views as docs_views
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

_ASSETS = Path(scolta.__file__).resolve().parent / "assets"
_PAGEFIND = Path(settings.SCOLTA["output_dir"]) / "pagefind"

urlpatterns = [
    # Browser-loaded Scolta static bundle + the in-process Pagefind index.
    re_path(r"^pagefind/(?P<path>.*)$", serve, {"document_root": str(_PAGEFIND)}),
    re_path(r"^scolta-assets/(?P<path>.*)$", serve, {"document_root": str(_ASSETS)}),
    # Scolta AI proxy endpoints (expand-query / summarize / followup / health).
    path("", include("scolta_django.urls")),
    # Admins.
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    # Language switcher uses Django's set_language view.
    path("i18n/", include("django.conf.urls.i18n")),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]

# Per-locale prefixed routes. The dedicated search page must come before the
# Wagtail catch-all (which would otherwise try to resolve "search" against the
# page tree and 404). Mirrors the Drupal demo's /search route; EN is unprefixed
# so it resolves at /search, other locales at /es/search, /fr/search, etc.
urlpatterns += i18n_patterns(
    re_path(r"^search/?$", docs_views.search, name="search"),
    path("", include(wagtail_urls)),
    prefix_default_language=False,
)
