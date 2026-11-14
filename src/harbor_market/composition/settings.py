"""Local scaffold settings; credentials come from the process, never source code."""

import os
from pathlib import Path

DATABASE_PATH = os.environ.get("HARBOR_MARKET_DB_PATH", "test-results/harbor-market.sqlite3")
Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATABASE_PATH,
    }
}
SECRET_KEY = os.environ["HARBOR_MARKET_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = ["localhost", "testserver"]
ROOT_URLCONF = "harbor_market.composition.urls"
INSTALLED_APPS = ["harbor_market.infrastructure.apps.InfrastructureConfig"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
