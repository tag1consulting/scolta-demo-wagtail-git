"""Test settings — the project settings with an in-memory DB.

All apps (including ``docs``, whose Wagtail Page subclasses require real
migrations) run their migrations against an in-memory SQLite database. Wagtail's
migrations create the root page and the default Site.
"""

import tempfile
from pathlib import Path

from gitmastery.settings import *  # noqa: F401,F403

_TMP = Path(tempfile.mkdtemp(prefix="gitmastery-test-"))

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

# Keep Scolta build artifacts out of the project tree during tests.
SCOLTA = {**SCOLTA, "output_dir": str(_TMP / "out"), "state_dir": str(_TMP / "state"), "ai_api_key": ""}  # noqa: F405
