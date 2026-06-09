"""Template helpers for the GitMastery theme: section nav + language switcher."""

from __future__ import annotations

from django import template
from django.utils.translation import get_language
from wagtail.models import Locale, Page

register = template.Library()

# Canonical section order (mirrors the Drupal "Documentation sections" menu).
SECTION_ORDER = [
    "Getting Started",
    "Core Concepts",
    "Commands Reference",
    "Advanced",
    "Performance",
    "Tips",
    "Comparisons",
    "Tutorials",
]


@register.simple_tag(takes_context=True)
def section_nav(context):
    """Return [(section, [pages...]), ...] for the current locale, ordered.

    Pages are the live content pages under the locale's home page, grouped by
    their ``section`` field and ordered by ``weight`` then title.
    """
    from docs.models import _GitContentPage  # noqa: WPS433 - avoid app-loading cycle

    lang = get_language() or "en"
    try:
        locale = Locale.objects.get(language_code=lang.split("-")[0])
    except Locale.DoesNotExist:
        locale = Locale.get_default()

    # Concrete content pages in this locale.
    grouped: dict[str, list] = {s: [] for s in SECTION_ORDER}
    for model in _GitContentPage.__subclasses__():
        for page in model.objects.live().public().filter(locale=locale):
            grouped.setdefault(page.section or "Other", []).append(page)

    nav = []
    for section in SECTION_ORDER:
        pages = sorted(grouped.get(section, []), key=lambda p: (p.weight, p.title.lower()))
        if pages:
            nav.append((section, pages))
    # Any non-canonical sections last.
    for section, pages in grouped.items():
        if section not in SECTION_ORDER and pages:
            nav.append((section, sorted(pages, key=lambda p: (p.weight, p.title.lower()))))
    return nav


@register.simple_tag
def home_url():
    """URL of the current active locale's home page (for the site brand link)."""
    lang = get_language() or "en"
    try:
        locale = Locale.objects.get(language_code=lang.split("-")[0])
    except Locale.DoesNotExist:
        locale = Locale.get_default()
    home = _home_for_locale(locale)
    return home.url if home else "/"


@register.simple_tag(takes_context=True)
def language_links(context):
    """Return [{code, label, url, active}] translations of the current page.

    Falls back to the per-locale home page when a given page has no translation
    in that language.
    """
    request = context.get("request")
    page = context.get("page") or context.get("self")
    current = get_language() or "en"

    links = []
    locales = {loc.language_code: loc for loc in Locale.objects.all()}
    for code, label in context.get("LANGUAGES", []) or _settings_languages():
        loc = locales.get(code)
        if loc is None:
            continue
        url = None
        if page is not None and isinstance(page, Page):
            translation = page.get_translations(inclusive=True).filter(locale=loc).live().first()
            if translation:
                url = translation.url
        if url is None:
            home = _home_for_locale(loc)
            url = home.url if home else f"/{code}/"
        links.append({"code": code, "label": label, "url": url, "active": code == current})
    return links


def _settings_languages():
    from django.conf import settings

    return settings.LANGUAGES


def _home_for_locale(locale):
    from docs.models import HomePage

    return HomePage.objects.filter(locale=locale).live().first()
