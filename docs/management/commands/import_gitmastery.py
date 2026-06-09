"""Import the GitMastery corpus (YAML) into Wagtail across five locales.

Port of the Drupal demo's ``import/import-content.php`` +
``import/import-translations.php`` + ``import/setup-about-page.php``.

Pipeline
--------
1. Ensure the five locales exist (en default + es/fr/it/de).
2. Ensure an English ``HomePage`` exists and the default Site points at it.
3. Import the 285 English pages from ``content/en/content-en-batch*.yaml``
   into the four content page models, under the English home page.
4. Create the English About page.
5. For each of es/fr/it/de, ensure a translated home page, then import the
   per-language translations from ``content/translations/content-<lang>-batch*.yaml``,
   linking each translated page to its English source via ``translation_key``
   (matched on ``source_title``).

Result: 285 EN content pages x 5 languages (1,425) + 1 About page = 1,426
indexable pages, matching the Drupal demo.

Idempotent: re-running skips pages that already exist (matched by locale + slug).
Use ``--reset`` to delete all GitMastery pages first.
"""

from __future__ import annotations

import glob
from pathlib import Path

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from wagtail.models import Locale, Page, Site

from docs.models import (
    AboutPage,
    Comparison,
    DocumentationPage,
    HomePage,
    Tip,
    Tutorial,
)

CONTENT_DIR = Path(settings.BASE_DIR) / "content"
LANGS = ["es", "fr", "it", "de"]

TYPE_MAP = {
    "documentation_page": DocumentationPage,
    "tutorial": Tutorial,
    "comparison": Comparison,
    "tip": Tip,
}

ABOUT_BODY = (
    "<h2>About This Site</h2>"
    "<p><strong>GitMastery is a fictional website.</strong> It was created by Tag1 "
    "Consulting to demonstrate the capabilities of Scolta, an open-source AI-powered "
    "search platform, on a content-rich technical reference site built with Wagtail.</p>"
    "<h2>What You Are Looking At</h2>"
    "<p>This site contains 285 pages of English Git reference content across categories "
    "including getting started, core concepts, advanced workflows, comparisons, and tips. "
    "All content is available in five languages: English, German, Spanish, French, and "
    "Italian, demonstrating Scolta's multilingual search capabilities.</p>"
    "<h2>What Scolta Does Here</h2>"
    "<p>The search bar uses Scolta to let you explore the Git documentation by asking "
    "natural-language questions. Scolta uses Pagefind for full-text indexing, Claude via "
    "the Anthropic API for query expansion and AI overviews, and a custom scoring layer. "
    "The result is a search experience that understands what you are asking, not just "
    "which keywords you used.</p>"
    "<h2>About Tag1 Consulting</h2>"
    "<p>Tag1 Consulting built and open-sources Scolta. For more information, visit "
    '<a href="https://tag1.com">tag1.com</a>.</p>'
)


class Command(BaseCommand):
    help = "Import the GitMastery content corpus into Wagtail (all five locales)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true", help="Delete existing GitMastery pages first."
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        self._ensure_locales()
        en_home = self._ensure_home()

        created = self._import_english(en_home)
        self.stdout.write(self.style.SUCCESS(f"English: {created} pages created."))

        self._ensure_about(en_home)

        for lang in LANGS:
            n = self._import_translations(lang)
            self.stdout.write(self.style.SUCCESS(f"  {lang}: {n} translated pages created."))

        total = Page.objects.type(DocumentationPage, Tutorial, Comparison, Tip, AboutPage).count()
        self.stdout.write(self.style.SUCCESS(f"Done. Indexable content pages: {total} (target 1426)."))

    # -- setup ---------------------------------------------------------------
    def _reset(self):
        for model in (DocumentationPage, Tutorial, Comparison, Tip, AboutPage, HomePage):
            qs = model.objects.all()
            self.stdout.write(f"Deleting {qs.count()} {model.__name__} pages...")
            for page in list(qs):
                page.delete()

    def _ensure_locales(self):
        for code in ["en", *LANGS]:
            Locale.objects.get_or_create(language_code=code)

    def _ensure_home(self) -> HomePage:
        en = Locale.objects.get(language_code="en")
        home = HomePage.objects.filter(locale=en).first()
        if home:
            return home

        root = Page.get_first_root_node()

        # Wagtail's initial migration creates a default welcome page with slug
        # 'home'. Free that slug before creating our own HomePage; the page is
        # removed at the end (after the Site is repointed, so the CASCADE on
        # Site.root_page does not delete the Site).
        welcome = root.get_children().first()
        if welcome and not isinstance(welcome.specific, HomePage):
            welcome.slug = f"__welcome_{welcome.pk}"
            welcome.save()

        home = HomePage(
            title="GitMastery",
            slug="home",
            locale=en,
            intro="<p>Master Git with 285 pages of reference docs in five languages.</p>",
        )
        root.add_child(instance=home)
        home.save_revision().publish()

        site = Site.objects.filter(is_default_site=True).first()
        if site:
            site.root_page = home
            site.save()
        else:
            Site.objects.create(
                hostname="localhost", port=80, root_page=home, is_default_site=True,
                site_name="GitMastery",
            )

        if welcome and not isinstance(welcome.specific, HomePage):
            try:
                welcome.delete()
            except Exception:  # noqa: BLE001
                pass
        return home

    def _home_for(self, locale) -> HomePage:
        home = HomePage.objects.filter(locale=locale).first()
        if home:
            return home
        en_home = HomePage.objects.get(locale=Locale.objects.get(language_code="en"))
        # Translated home: same translation_key as the English home (so Wagtail's
        # locale-aware site-root routing serves its subtree under the /<lang>/
        # prefix), but a distinct slug to avoid a sibling-slug clash under root.
        root = Page.get_first_root_node()
        home = HomePage(
            title=en_home.title,
            slug=f"home-{locale.language_code}",
            locale=locale,
            translation_key=en_home.translation_key,
            intro=en_home.intro,
        )
        root.add_child(instance=home)
        home.save_revision().publish()
        return home

    # -- english -------------------------------------------------------------
    def _english_docs(self):
        for path in sorted(glob.glob(str(CONTENT_DIR / "en" / "content-en-batch*.yaml"))):
            for entry in yaml.safe_load(Path(path).read_text()) or []:
                yield entry

    @transaction.atomic
    def _import_english(self, home: HomePage) -> int:
        en = Locale.objects.get(language_code="en")
        used_slugs: set[str] = set(
            home.get_children().values_list("slug", flat=True)
        )
        created = 0
        for data in self._english_docs():
            model = TYPE_MAP.get(data.get("type", "documentation_page"), DocumentationPage)
            # Idempotency keyed on the (unique) title, not the slug — re-running
            # must not create duplicates with suffixed slugs.
            if home.get_children().filter(title=data["title"]).exists():
                continue
            slug = _unique_slug(data["title"], used_slugs)
            page = model(title=data["title"], slug=slug, locale=en)
            _apply_fields(page, data)
            home.add_child(instance=page)
            page.save_revision().publish()
            used_slugs.add(slug)
            created += 1
        return created

    def _ensure_about(self, home: HomePage):
        en = Locale.objects.get(language_code="en")
        if AboutPage.objects.filter(locale=en).exists():
            return
        page = AboutPage(title="About This Demo", slug="about", locale=en, body=ABOUT_BODY)
        home.add_child(instance=page)
        page.save_revision().publish()

    # -- translations --------------------------------------------------------
    def _translation_entries(self, lang):
        pattern = str(CONTENT_DIR / "translations" / f"content-{lang}-batch*.yaml")
        for path in sorted(glob.glob(pattern)):
            for entry in yaml.safe_load(Path(path).read_text()) or []:
                yield entry

    @transaction.atomic
    def _import_translations(self, lang) -> int:
        locale = Locale.objects.get(language_code=lang)
        home = self._home_for(locale)

        # Map English source title -> source page (any of the four content types).
        en = Locale.objects.get(language_code="en")
        source_by_title = {}
        for model in (DocumentationPage, Tutorial, Comparison, Tip):
            for page in model.objects.filter(locale=en):
                source_by_title[page.title] = page

        used_slugs: set[str] = set(home.get_children().values_list("slug", flat=True))
        created = 0
        for entry in self._translation_entries(lang):
            source_title = entry.get("source_title")
            title = entry.get("title")
            if not source_title or not title:
                continue
            source = source_by_title.get(source_title)
            if source is None:
                self.stderr.write(f"  [{lang}] no source for: {source_title!r}")
                continue
            model = type(source)
            # Reuse the source slug so translations share a stable path; ensure
            # uniqueness under this locale's home just in case.
            slug = source.slug if source.slug not in used_slugs else _unique_slug(title, used_slugs)
            if home.get_children().filter(translation_key=source.translation_key).exists():
                continue
            page = model(
                title=title,
                slug=slug,
                locale=locale,
                translation_key=source.translation_key,  # links the translation
                body=entry.get("body", ""),
                section=source.section,
                difficulty=source.difficulty,
                git_version=source.git_version,
                weight=source.weight,
            )
            # Carry type-specific structural fields from the source.
            if isinstance(source, Tutorial):
                page.estimated_time = source.estimated_time
            elif isinstance(source, Comparison):
                page.compared_systems = source.compared_systems
                page.applies_to = source.applies_to
                page.verdict = source.verdict
                page.feature_table = source.feature_table
            elif isinstance(source, Tip):
                page.topic = source.topic
            home.add_child(instance=page)
            page.save_revision().publish()
            used_slugs.add(slug)
            created += 1
        return created


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _unique_slug(title: str, used: set[str]) -> str:
    base = slugify(title) or "page"
    base = base[:230]
    slug = base
    i = 2
    while slug in used:
        slug = f"{base}-{i}"
        i += 1
    return slug


def _apply_fields(page, data: dict) -> None:
    page.body = data.get("body", "") or ""
    page.section = data.get("section", "") or ""
    page.difficulty = data.get("difficulty", "") or ""
    page.git_version = data.get("git_version", "") or ""
    page.weight = int(data.get("weight") or 0)
    if isinstance(page, Tutorial):
        page.estimated_time = data.get("estimated_time", "") or ""
    elif isinstance(page, Comparison):
        cs = data.get("compared_systems") or []
        page.compared_systems = ", ".join(cs) if isinstance(cs, list) else str(cs)
        page.applies_to = data.get("applies_to", "") or ""
        page.verdict = data.get("verdict", "") or ""
        page.feature_table = data.get("feature_table", "") or ""
    elif isinstance(page, Tip):
        page.topic = data.get("category", "") or ""
