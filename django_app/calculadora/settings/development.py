from .base import *  # noqa: F401, F403

DEBUG = True
SECRET_KEY = "dev-secret-key-do-not-use-in-production-abc123"

ALLOWED_HOSTS = ["*"]

# SQLite for local development
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

# Disable static file compression in dev
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Show emails in console during development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Django Debug Toolbar (optional, uncomment if installed)
# INSTALLED_APPS += ["debug_toolbar"]
# MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
# INTERNAL_IPS = ["127.0.0.1"]
