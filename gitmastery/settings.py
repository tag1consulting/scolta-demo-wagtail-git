"""
Django/Wagtail settings for the GitMastery demo — a port of the Drupal 11
``git-manual`` demo to Wagtail, using ``scolta-python`` + ``scolta-django``.

The whole search configuration lives in the ``SCOLTA`` dict below. It is a flat
mirror of the Drupal demo's ``config/sync/scolta.settings.yml`` (the nested
``scoring:`` / ``display:`` / ``pagefind:`` groups are flattened into the
top-level snake_case keys that ``scolta.config.ScoltaConfig`` accepts).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "gitmastery-demo-insecure-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    # GitMastery
    "docs",
    "theme",
    # Scolta
    "scolta_django",
    # Wagtail
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail.locales",
    "wagtail",
    "modelcluster",
    "taggit",
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "gitmastery.urls"
WSGI_APPLICATION = "gitmastery.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "theme" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_DB_PATH", str(BASE_DIR / "db.sqlite3")),
    }
}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# ---------------------------------------------------------------------------
# Internationalization — five languages, mirroring the Drupal demo
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("es", "Español"),
    ("fr", "Français"),
    ("it", "Italiano"),
    ("de", "Deutsch"),
]

# Wagtail multilingual: enable i18n and declare the five content languages so
# pages can be translated and a localized URL prefix (/es/, /fr/, ...) is served.
WAGTAIL_I18N_ENABLED = True
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "theme" / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if os.environ.get("USE_WHITENOISE")
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Wagtail
# ---------------------------------------------------------------------------
WAGTAIL_SITE_NAME = "GitMastery"
WAGTAILADMIN_BASE_URL = os.environ.get("WAGTAILADMIN_BASE_URL", "http://localhost:8000")
WAGTAILSEARCH_BACKENDS = {
    "default": {"BACKEND": "wagtail.search.backends.database"}
}
WAGTAILDOCS_EXTENSIONS = ["csv", "docx", "key", "odt", "pdf", "pptx", "rtf", "txt", "xlsx", "zip"]

# ---------------------------------------------------------------------------
# Scolta — flat mirror of git-manual/config/sync/scolta.settings.yml
# ---------------------------------------------------------------------------
SCOLTA = {
    # --- AI provider ---
    "ai_api_key": os.environ.get("SCOLTA_API_KEY", ""),
    "ai_provider": os.environ.get("SCOLTA_AI_PROVIDER", "anthropic"),
    "ai_model": os.environ.get("SCOLTA_AI_MODEL", "claude-sonnet-4-5-20250929"),
    "ai_expansion_model": "",
    "ai_base_url": "",
    "ai_expand_query": True,
    "ai_summarize": True,
    "ai_languages": ["en", "es", "fr", "de", "it"],
    "max_follow_ups": 3,

    # --- Site identity ---
    "site_name": "GitMastery",
    "site_description": (
        "GitMastery, 1,425 pages of Git documentation including man pages for all "
        "git commands (git-log, git-blame, git-grep, git-rebase, git-stash, etc.) in "
        "English, Spanish, French, German, and Italian; search in your native "
        "language and get results and AI summaries back in that language."
    ),

    # --- Indexer: pure-Python in-process indexer (Drupal used 'php') ---
    "indexer": "auto",

    # --- Searchable models (DjangoContentSource path; each model's
    #     to_searchable_content() controls filters + sortable, exactly like the
    #     Drupal gitmastery_scolta hook). HomePage / SectionIndexPage are NOT
    #     listed, so only real content + the About page are indexed. ---
    "models": [
        "docs.DocumentationPage",
        "docs.Tutorial",
        "docs.Comparison",
        "docs.Tip",
        "docs.AboutPage",
    ],

    # --- Build/output locations ---
    "output_dir": str(BASE_DIR / "pagefind_index"),
    "state_dir": str(BASE_DIR / ".scolta-state"),
    "pagefind_index_path": "/pagefind",   # browser loads /pagefind/pagefind.js
    "asset_url": "/scolta-assets",        # browser loads /scolta-assets/js/scolta.js

    # --- Rebuild on edit: OFF for the demo. The corpus is built once via
    #     `manage.py scolta_build`; a debounced rebuild on every page save would
    #     thrash during the 1,425-page import. ---
    "auto_rebuild": False,
    "auto_rebuild_delay": 300,
    "route_prefix": "api/scolta/v1",

    # --- Single-language Pagefind bucket. The Drupal demo forces every page
    #     (all five languages) into one 'en' index bucket — that is why its
    #     pagefind-entry.json reports a single language with ~1,426 pages and the
    #     smoke test's >=1,400 bar holds. Match that exactly. ---
    "language": "en",
    "auto_language_filter": True,

    # --- Scoring preset + explicit overrides (preset applied first, these win) ---
    "preset": "reference",
    "title_match_boost": 3.0,
    "title_all_terms_multiplier": 1.5,
    "content_match_boost": 0.5,
    "recency_boost_max": 0.1,
    "recency_half_life_days": 3650,
    "recency_penalty_after_days": 36500,
    "recency_max_penalty": 0.05,
    "expand_primary_weight": 0.8,
    "recency_strategy": "exponential",
    "custom_stop_words": [],

    # --- Display ---
    "excerpt_length": 350,
    "results_per_page": 12,
    "max_pagefind_results": 60,
    "ai_summary_top_n": 10,
    "ai_summary_max_chars": 4000,
    "cache_ttl": 2592000,

    # --- Sortable + filter facets (drive AI sort/filter intent) ---
    "sortable_fields": ["weight", "date"],
    "sortable_field_descriptions": {
        "weight": "Importance weight of the documentation page (higher = more fundamental)",
        "date": "Publication or last-updated date of the document",
    },
    "filter_fields": ["section", "difficulty", "topic", "git_version"],
    "filter_field_descriptions": {
        "section": (
            "Documentation section. Map the user's query to one of these values: "
            "Getting Started (installation, first repo, basic workflow), Core Concepts "
            "(branching model, DAG, objects, refs, index, working tree, HEAD), Commands "
            "Reference (git-add, git-commit, git-push, git-pull, git-merge, git-rebase, "
            "git-log, git-diff, git-stash, git-checkout, git-branch, git-remote, "
            "git-fetch, git-reset, git-revert, git-tag, git-cherry-pick, git-bisect, "
            "git-blame, git-grep), Advanced (internals, plumbing, custom scripts, "
            "recovery, subtree), Performance (large repos, shallow clone, sparse "
            "checkout, partial clone), Tips (quick tips, shortcuts, aliases), "
            "Comparisons (tool comparisons, workflow comparisons), Tutorials "
            "(step-by-step walkthroughs, how-to guides)"
        ),
        "difficulty": (
            "Difficulty level. Values: Beginner (basic operations, first steps), "
            "Intermediate (branching, merging, rebasing, workflows), Advanced "
            "(internals, plumbing, custom scripts, recovery), Expert (contributing to "
            "git, low-level implementation)"
        ),
        "topic": (
            "Subject topic area. Values: Branching (branch management, strategies), "
            "Merging (merge conflicts, strategies), Remotes (push, pull, fetch, "
            "upstream), History (log, blame, bisect, reflog), Undoing (reset, revert, "
            "checkout, restore), Configuration (gitconfig, aliases, hooks setup), "
            "Performance (large repos, optimization), Hooks (pre-commit, post-commit, "
            "server hooks), Large Repos (monorepos, LFS, sparse checkout), Migration "
            "(from SVN, Mercurial, other VCS)"
        ),
        "git_version": (
            "Git version where this feature was introduced (e.g. 2.30+, 2.37+). Use "
            "when the user asks about a specific version."
        ),
    },

    # --- Memory budget for the indexer ---
    "memory_budget": {"profile": "conservative", "custom_bytes": None, "chunk_size": None},
}

# --- Reverse-proxy support (e.g. DDEV's TLS-terminating router) -------------
# Trust X-Forwarded-Proto so Django knows the original request was HTTPS, and
# accept the proxy origin for CSRF checks. Both are env-gated no-ops outside
# a proxy setup, so runserver/Docker behavior is unchanged.
if os.environ.get("DJANGO_BEHIND_PROXY", "") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o
]
