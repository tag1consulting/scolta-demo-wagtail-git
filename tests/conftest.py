"""Shared pytest fixtures for the GitMastery demo tests."""

import pytest


@pytest.fixture
def home(db):
    """An English HomePage attached under the Wagtail root, plus the default Site."""
    from wagtail.models import Locale, Page, Site

    from docs.models import HomePage

    Locale.objects.get_or_create(language_code="en")
    root = Page.get_first_root_node()

    # Free the 'home' slug used by Wagtail's default welcome page.
    welcome = root.get_children().first()
    if welcome and not isinstance(welcome.specific, HomePage):
        welcome.slug = f"__welcome_{welcome.pk}"
        welcome.save()

    home = HomePage(title="GitMastery", slug="home", locale=Locale.get_default())
    root.add_child(instance=home)
    home.save_revision().publish()
    home.refresh_from_db()

    site = Site.objects.filter(is_default_site=True).first()
    if site:
        site.root_page = home
        site.save()
    if welcome and not isinstance(welcome.specific, HomePage):
        try:
            welcome.delete()
        except Exception:
            pass
    return home


def make_page(parent, model, **fields):
    """Create + publish a content page under ``parent``."""
    page = model(**fields)
    parent.add_child(instance=page)
    page.save_revision().publish()
    page.refresh_from_db()
    return page
