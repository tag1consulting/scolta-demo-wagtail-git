"""Unit tests for the GitMastery page models' Scolta integration.

These assert the equivalent of the Drupal ``gitmastery_scolta`` content-item
alter hook: section/difficulty/topic/git_version land in ContentItem.filters and
weight lands in ContentItem.sortable.
"""

import pytest
from scolta.content import ContentItem

from docs.models import Comparison, DocumentationPage, Tip, Tutorial
from tests.conftest import make_page


@pytest.mark.django_db
def test_documentation_page_filters_and_sortable(home):
    page = make_page(
        home, DocumentationPage,
        title="What is Git?", slug="what-is-git",
        body="<p>Git is a <strong>distributed</strong> VCS.</p>",
        section="Getting Started", difficulty="Beginner",
        git_version="2.30+", weight=10,
    )
    item = page.to_searchable_content()
    assert isinstance(item, ContentItem)
    assert item.id == f"gitmastery-{page.pk}"
    assert item.title == "What is Git?"
    assert "distributed" in item.body_html
    assert item.filters == {
        "section": "Getting Started",
        "difficulty": "Beginner",
        "git_version": "2.30+",
    }
    assert item.sortable["weight"] == 10
    assert item.url.endswith("/what-is-git/")


@pytest.mark.django_db
def test_tip_adds_topic_filter(home):
    page = make_page(
        home, Tip, title="Alias your common commands", slug="alias-tip",
        body="<p>Use git config alias.</p>", section="Tips",
        difficulty="Beginner", topic="Configuration", weight=5,
    )
    item = page.to_searchable_content()
    assert item.filters["topic"] == "Configuration"
    assert item.filters["section"] == "Tips"


@pytest.mark.django_db
def test_comparison_indexes_verdict(home):
    page = make_page(
        home, Comparison, title="Git vs SVN", slug="git-vs-svn",
        body="<p>Body.</p>", section="Comparisons", difficulty="Intermediate",
        compared_systems="Git, SVN", verdict="<p>Use Git for distributed work.</p>",
        weight=3,
    )
    item = page.to_searchable_content()
    # The verdict text is folded into the indexed body so it is searchable.
    assert "distributed work" in item.body_html


@pytest.mark.django_db
def test_searchable_queryset_excludes_unpublished(home):
    live = make_page(
        home, Tutorial, title="Rebasing Tutorial", slug="rebasing",
        body="<p>...</p>", section="Tutorials", difficulty="Advanced", weight=1,
    )
    draft = Tutorial(title="Draft", slug="draft-tut", body="<p>x</p>",
                     section="Tutorials", difficulty="Advanced", weight=1)
    home.add_child(instance=draft)
    draft.live = False
    draft.save()

    pks = set(Tutorial.searchable_queryset().values_list("pk", flat=True))
    assert live.pk in pks
    assert draft.pk not in pks
