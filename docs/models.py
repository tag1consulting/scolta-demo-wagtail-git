"""GitMastery Wagtail page models.

A faithful port of the Drupal ``git-manual`` content model:

  Drupal content type    -> Wagtail page model
  ---------------------     ----------------------
  documentation_page     -> DocumentationPage
  tutorial               -> Tutorial
  comparison             -> Comparison
  tip                    -> Tip
  page ("About")         -> AboutPage

The Drupal taxonomies (section / difficulty / topic) and scalar fields
(git_version, weight, estimated_time, ...) become page fields. Search filters
and sortables are attached in ``to_searchable_content()`` on each model — the
exact equivalent of the Drupal ``gitmastery_scolta_scolta_content_item_alter``
hook, which pushed ``section``/``difficulty``/``topic``/``git_version`` into
``ContentItem.filters`` and ``weight`` into ``ContentItem.sortable``.

These models are listed in ``settings.SCOLTA['models']`` so the Django content
source indexes them. ``HomePage`` is deliberately NOT listed (it is a listing /
landing page, like the Drupal front view — not indexed), which keeps the index
at 285 EN content pages x 5 languages + 1 About = 1,426, matching the Drupal
demo's Pagefind ``page_count``.
"""

from __future__ import annotations

from django.db import models
from scolta.content import ContentItem
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index

from scolta_django.searchable import SearchableMixin

# Difficulty choices mirror the Drupal 'difficulty' vocabulary.
DIFFICULTY_CHOICES = [
    ("Beginner", "Beginner"),
    ("Intermediate", "Intermediate"),
    ("Advanced", "Advanced"),
    ("Expert", "Expert"),
]


def _scolta_date(page) -> str:
    dt = (
        getattr(page, "last_published_at", None)
        or getattr(page, "latest_revision_created_at", None)
        or getattr(page, "first_published_at", None)
    )
    return dt.strftime("%Y-%m-%d") if dt else ""


def _scolta_url(page) -> str:
    """Relative, locale-prefixed URL for the page (portable across hosts)."""
    return page.url or page.get_url() or page.url_path or f"/{page.slug}/"


class HomePage(Page):
    """Site landing page. Lists sections; not indexed (like the Drupal front view)."""

    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [FieldPanel("intro")]

    # Everything documentation-related lives under the home page.
    subpage_types = [
        "docs.DocumentationPage",
        "docs.Tutorial",
        "docs.Comparison",
        "docs.Tip",
        "docs.AboutPage",
    ]

    class Meta:
        verbose_name = "Home page"


class _GitContentPage(SearchableMixin, Page):
    """Shared base for the four indexed Git content types.

    Provides the common Drupal fields and a single ``to_searchable_content()``
    that builds the ContentItem with filters + sortable. Subclasses add their
    own fields and extend ``extra_filters`` / ``body_extra``.
    """

    body = RichTextField(blank=True, help_text="Main HTML body")
    section = models.CharField(max_length=64, blank=True, db_index=True)
    difficulty = models.CharField(max_length=32, blank=True, choices=DIFFICULTY_CHOICES)
    git_version = models.CharField("Git version", max_length=32, blank=True)
    weight = models.IntegerField(default=0)

    is_creatable = False  # abstract-ish base; only concrete subclasses are creatable

    search_fields = Page.search_fields + [
        index.SearchField("body"),
        index.FilterField("section"),
        index.FilterField("difficulty"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("body"),
        FieldPanel("section"),
        FieldPanel("difficulty"),
        FieldPanel("git_version"),
        FieldPanel("weight"),
    ]

    subpage_types = []  # leaf pages

    class Meta:
        abstract = True

    # --- Scolta integration -------------------------------------------------
    @classmethod
    def searchable_queryset(cls):
        """Only live, public pages are indexed (all locales)."""
        return cls.objects.live().public()

    def should_be_searchable(self) -> bool:
        return self.live

    def extra_filters(self) -> dict:
        """Subclass hook: additional ContentItem.filters (e.g. 'topic')."""
        return {}

    def body_extra(self) -> str:
        """Subclass hook: extra HTML appended to the indexed body."""
        return ""

    def to_searchable_content(self) -> ContentItem:
        from django.conf import settings

        filters: dict = {}
        if self.section:
            filters["section"] = self.section
        if self.difficulty:
            filters["difficulty"] = self.difficulty
        if self.git_version:
            filters["git_version"] = self.git_version
        filters.update(self.extra_filters())

        sortable: dict = {"weight": int(self.weight or 0)}
        date = _scolta_date(self)
        if date:
            sortable["date"] = date

        body_html = str(self.body or "")
        extra = self.body_extra()
        if extra:
            body_html = f"{body_html}\n{extra}"

        return ContentItem(
            id=f"gitmastery-{self.pk}",
            title=str(self.title or ""),
            body_html=body_html,
            url=_scolta_url(self),
            date=date,
            site_name=settings.SCOLTA.get("site_name", "GitMastery"),
            # Per-page filter language (Wagtail locale), so the language facet
            # is populated per page instead of collapsing to the index bucket.
            language=self.locale.language_code,
            filters=filters,
            sortable=sortable,
        )


class DocumentationPage(_GitContentPage):
    is_creatable = True

    class Meta:
        verbose_name = "Documentation page"


class Tutorial(_GitContentPage):
    estimated_time = models.CharField(max_length=64, blank=True)

    is_creatable = True

    content_panels = _GitContentPage.content_panels + [FieldPanel("estimated_time")]

    class Meta:
        verbose_name = "Tutorial"


class Comparison(_GitContentPage):
    compared_systems = models.CharField(
        max_length=255, blank=True, help_text="Comma-separated list of compared systems"
    )
    applies_to = models.CharField(max_length=128, blank=True)
    verdict = RichTextField(blank=True)
    feature_table = RichTextField(blank=True)

    is_creatable = True

    content_panels = _GitContentPage.content_panels + [
        FieldPanel("compared_systems"),
        FieldPanel("applies_to"),
        FieldPanel("verdict"),
        FieldPanel("feature_table"),
    ]

    def body_extra(self) -> str:
        # Index the verdict + feature table too, so a comparison's full content
        # is findable (the Drupal node rendered these fields in the view mode).
        parts = [str(self.verdict or ""), str(self.feature_table or "")]
        return "\n".join(p for p in parts if p)

    class Meta:
        verbose_name = "Comparison"


class Tip(_GitContentPage):
    # The Drupal 'tip' type used field_category referencing the 'topic'
    # vocabulary; here it is a 'topic' field exposed as the 'topic' filter.
    topic = models.CharField(max_length=64, blank=True, db_index=True)

    is_creatable = True

    content_panels = _GitContentPage.content_panels + [FieldPanel("topic")]

    def extra_filters(self) -> dict:
        return {"topic": self.topic} if self.topic else {}

    class Meta:
        verbose_name = "Tip"


class AboutPage(SearchableMixin, Page):
    """The 'About This Demo' page (Drupal 'page' bundle). Indexed, body only."""

    body = RichTextField(blank=True)

    search_fields = Page.search_fields + [index.SearchField("body")]
    content_panels = Page.content_panels + [FieldPanel("body")]
    subpage_types = []

    @classmethod
    def searchable_queryset(cls):
        return cls.objects.live().public()

    def should_be_searchable(self) -> bool:
        return self.live

    def to_searchable_content(self) -> ContentItem:
        from django.conf import settings

        return ContentItem(
            id=f"gitmastery-{self.pk}",
            title=str(self.title or ""),
            body_html=str(self.body or ""),
            url=_scolta_url(self),
            date=_scolta_date(self),
            site_name=settings.SCOLTA.get("site_name", "GitMastery"),
            # Per-page filter language (Wagtail locale); see _GitContentPage.
            language=self.locale.language_code,
        )

    class Meta:
        verbose_name = "About page"
