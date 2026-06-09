"""Language-filter regression tests (the "every page indexed as `en`" bug).

Two layers:

* unit — each page's ``to_searchable_content().language`` reflects its Wagtail
  locale (the per-page filter language, distinct from the single-bucket index
  ``language`` setting);
* index — after a build, the on-disk Pagefind ``language`` filter has one value
  per locale with the expected page counts. This catches the all-`en` class of
  bug regardless of where the language gets dropped (model, mixin, or builder).
"""

import glob
import gzip
import os

import pytest
from django.conf import settings

from docs.models import AboutPage, DocumentationPage
from tests.conftest import make_page

LOCALES = ["es", "fr", "it", "de"]


# -- unit: per-page language --------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("code", LOCALES)
def test_content_page_language_matches_locale(home, code):
    """A content page in a non-default locale indexes with that locale's code."""
    from wagtail.models import Locale

    loc, _ = Locale.objects.get_or_create(language_code=code)
    page = DocumentationPage(
        title=f"Doc {code}", slug=f"doc-{code}",
        body="<p>body</p>", section="Getting Started",
        difficulty="Beginner", weight=1, locale=loc,
    )
    home.add_child(instance=page)
    page.save_revision().publish()
    page.refresh_from_db()
    assert page.locale.language_code == code
    assert page.to_searchable_content().language == code


@pytest.mark.django_db
def test_default_locale_page_is_en(home):
    """The default-locale (English) content page indexes as `en`."""
    page = make_page(
        home, DocumentationPage, title="Cloning", slug="cloning",
        body="<p>git clone</p>", section="Getting Started",
        difficulty="Beginner", weight=1,
    )
    assert page.to_searchable_content().language == "en"


@pytest.mark.django_db
@pytest.mark.parametrize("code", LOCALES)
def test_about_page_language_matches_locale(home, code):
    """AboutPage (its own to_searchable_content override) also sets language."""
    from wagtail.models import Locale

    loc, _ = Locale.objects.get_or_create(language_code=code)
    page = AboutPage(title=f"About {code}", slug=f"about-{code}",
                     body="<p>about</p>", locale=loc)
    home.add_child(instance=page)
    page.save_revision().publish()
    page.refresh_from_db()
    assert page.to_searchable_content().language == code


# -- index: built filter map --------------------------------------------------

_DELIMITER = b"pagefind_dcd"


class _Cbor:
    """Minimal CBOR reader — just enough to walk a .pf_filter payload
    (``[name, [[value, [pageNums]], ...]]``) with no third-party dependency."""

    def __init__(self, data: bytes):
        self.d = data
        self.i = 0

    def _head(self):
        b = self.d[self.i]
        self.i += 1
        major, info = b >> 5, b & 0x1F
        if info < 24:
            return major, info
        if info == 24:
            val = self.d[self.i]; self.i += 1
        elif info == 25:
            val = int.from_bytes(self.d[self.i:self.i + 2], "big"); self.i += 2
        elif info == 26:
            val = int.from_bytes(self.d[self.i:self.i + 4], "big"); self.i += 4
        elif info == 27:
            val = int.from_bytes(self.d[self.i:self.i + 8], "big"); self.i += 8
        else:
            raise ValueError(f"unsupported additional info {info}")
        return major, val

    def read(self):
        major, val = self._head()
        if major == 0:  # uint
            return val
        if major == 1:  # negative int
            return -1 - val
        if major == 2:  # byte string
            s = self.d[self.i:self.i + val]; self.i += val; return s
        if major == 3:  # text string
            s = self.d[self.i:self.i + val]; self.i += val; return s.decode("utf-8")
        if major == 4:  # array
            return [self.read() for _ in range(val)]
        if major == 5:  # map
            return {self.read(): self.read() for _ in range(val)}
        raise ValueError(f"unsupported major type {major}")


def _decode_filter_file(path: str):
    payload = gzip.decompress(open(path, "rb").read())
    assert payload.startswith(_DELIMITER), f"missing pagefind delimiter in {path}"
    return _Cbor(payload[len(_DELIMITER):]).read()


def _language_counts(index_root: str) -> dict:
    """Return {language_value: page_count} from the built `language` filter."""
    for path in sorted(glob.glob(os.path.join(index_root, "pagefind", "filter", "*.pf_filter"))):
        name, values = _decode_filter_file(path)
        if name == "language":
            return {value: len(page_nums) for value, page_nums in values}
    raise AssertionError("no `language` filter found in the built index")


def test_built_index_language_filter_has_five_locales():
    """The built `language` filter must split per locale: en=286, others=285
    (parity with the Drupal demo's {en:286, de/es/fr/it:285}). Regression for
    the single-bucket `language: {en: 1426}` map."""
    # The test settings point output_dir at a throwaway temp dir; assert against
    # the *production* built index under BASE_DIR (what `scolta_build` writes and
    # what the running site serves).
    index_root = os.path.join(str(settings.BASE_DIR), "pagefind_index")
    if not os.path.isdir(os.path.join(index_root, "pagefind", "filter")):
        pytest.skip(
            "no built index at %s — run `python manage.py scolta_build --force`" % index_root
        )
    counts = _language_counts(index_root)
    assert set(counts) == {"en", "es", "fr", "it", "de"}, (
        f"expected 5 language values, got {counts}"
    )
    assert counts["en"] == 286, counts
    for code in LOCALES:
        assert counts[code] == 285, counts
