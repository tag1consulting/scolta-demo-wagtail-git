"""End-to-end test of the import command on a tiny corpus.

Verifies the pipeline that, at full scale, produces 285 EN pages x 5 languages +
1 About = 1,426 pages: locale setup, English import, About page, and
translation linkage via ``translation_key`` (matched on ``source_title``).
"""

from pathlib import Path

import pytest
import yaml
from django.core.management import call_command


def _write(dirpath: Path, name: str, data) -> None:
    dirpath.mkdir(parents=True, exist_ok=True)
    (dirpath / name).write_text(yaml.safe_dump(data, allow_unicode=True))


@pytest.fixture
def tiny_corpus(tmp_path, monkeypatch):
    en = [
        {"title": "What is Git?", "type": "documentation_page", "section": "Getting Started",
         "difficulty": "Beginner", "git_version": "2.30+", "weight": 10,
         "body": "<p>Git is a distributed VCS.</p>"},
        {"title": "Alias tip", "type": "tip", "section": "Tips", "difficulty": "Beginner",
         "weight": 5, "body": "<p>Use aliases.</p>"},
    ]
    es = [
        {"source_title": "What is Git?", "title": "¿Qué es Git?", "langcode": "es",
         "body": "<p>Git es un VCS distribuido.</p>"},
        {"source_title": "Alias tip", "title": "Consejo de alias", "langcode": "es",
         "body": "<p>Usa alias.</p>"},
    ]
    _write(tmp_path / "en", "content-en-batch1.yaml", en)
    _write(tmp_path / "translations", "content-es-batch1.yaml", es)

    import docs.management.commands.import_gitmastery as cmd
    monkeypatch.setattr(cmd, "CONTENT_DIR", tmp_path)
    monkeypatch.setattr(cmd, "LANGS", ["es"])
    return tmp_path


@pytest.mark.django_db
def test_import_creates_pages_and_links_translations(tiny_corpus):
    from wagtail.models import Locale

    from docs.models import AboutPage, DocumentationPage, Tip

    call_command("import_gitmastery")

    en = Locale.objects.get(language_code="en")
    es = Locale.objects.get(language_code="es")

    assert DocumentationPage.objects.filter(locale=en).count() == 1
    assert Tip.objects.filter(locale=en).count() == 1
    assert AboutPage.objects.filter(locale=en).count() == 1

    # Spanish translations exist and are linked to their English sources.
    es_doc = DocumentationPage.objects.get(locale=es)
    assert es_doc.title == "¿Qué es Git?"
    en_doc = DocumentationPage.objects.get(locale=en)
    assert es_doc.translation_key == en_doc.translation_key
    # Structural fields are carried from the source.
    assert es_doc.section == "Getting Started"
    assert es_doc.weight == 10

    # Total indexable content pages: 2 EN + 2 ES + 1 About = 5.
    total = sum(
        m.objects.count() for m in (DocumentationPage, Tip, AboutPage)
    )
    assert total == 5


@pytest.mark.django_db
def test_import_is_idempotent(tiny_corpus):
    from docs.models import DocumentationPage, Tip

    call_command("import_gitmastery")
    first = DocumentationPage.objects.count() + Tip.objects.count()
    call_command("import_gitmastery")
    second = DocumentationPage.objects.count() + Tip.objects.count()
    assert first == second
