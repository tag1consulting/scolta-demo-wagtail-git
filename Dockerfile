# GitMastery (Wagtail) demo image.
#
# Mirrors the Drupal git-manual Dockerfile's shape: install dependencies, load
# all content, build the search index at image-build time, then serve. The
# build step imports the full 1,426-page corpus and builds the Pagefind index so
# the running container is ready immediately.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=gitmastery.settings \
    DJANGO_DEBUG=0 \
    USE_WHITENOISE=1 \
    DJANGO_ALLOWED_HOSTS=*

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Optional override, e.g. --build-arg SCOLTA_PIP_SPEC="scolta==1.0.4 scolta-django==1.0.4"
# or a local wheel spec, when PyPI is not the desired source.
ARG SCOLTA_PIP_SPEC=""

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && if [ -n "$SCOLTA_PIP_SPEC" ]; then pip install --no-cache-dir $SCOLTA_PIP_SPEC; fi

COPY . .

# Migrate, import all content, build the index, collect static assets.
RUN python manage.py migrate --no-input \
 && python manage.py import_gitmastery \
 && python manage.py scolta_build \
 && python manage.py collectstatic --no-input

EXPOSE 8080

# A no-API-key container still serves search (Pagefind ranks locally); the AI
# tier degrades gracefully. Pass SCOLTA_API_KEY at runtime for live summaries.
CMD ["gunicorn", "gitmastery.wsgi:application", "--bind", "0.0.0.0:8080", "--workers", "3", "--timeout", "180"]
