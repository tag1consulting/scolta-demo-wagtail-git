"""WSGI config for the GitMastery demo."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gitmastery.settings")

application = get_wsgi_application()

# Optionally wrap with WhiteNoise so the container can serve static assets, the
# Scolta JS/CSS/WASM bundle, and the Pagefind index without a separate web
# server. Enabled when USE_WHITENOISE is set (see Dockerfile).
if os.environ.get("USE_WHITENOISE"):
    from whitenoise import WhiteNoise
    from django.conf import settings

    application = WhiteNoise(application, root=str(settings.STATIC_ROOT))
    # Serve the built Pagefind index at /pagefind/ and the Scolta asset bundle
    # at /scolta-assets/ as immutable static trees.
    import scolta

    application.add_files(str(settings.SCOLTA["output_dir"]) + "/pagefind", prefix="pagefind/")
    application.add_files(
        str((__import__("pathlib").Path(scolta.__file__).resolve().parent / "assets")),
        prefix="scolta-assets/",
    )
