"""The Django content source enumerates the GitMastery page models."""

import pytest

from docs.models import DocumentationPage
from scolta_django.content_source import DjangoContentSource, get_content_source
from tests.conftest import make_page


def test_uses_django_content_source():
    # SCOLTA has no 'wagtail' key, so the ORM-model source is used (each model's
    # own to_searchable_content drives filters/sortable — full Drupal parity).
    assert isinstance(get_content_source(), DjangoContentSource)


@pytest.mark.django_db
def test_published_content_includes_pages(home):
    make_page(
        home, DocumentationPage, title="Cloning", slug="cloning",
        body="<p>git clone</p>", section="Getting Started",
        difficulty="Beginner", weight=2,
    )
    source = get_content_source()
    titles = {i.title for i in source.get_published_content()}
    assert "Cloning" in titles
    assert source.get_total_count() >= 1
