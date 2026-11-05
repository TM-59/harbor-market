"""Local scaffold settings; credentials come from the process, never source code."""

import os

SECRET_KEY = os.environ["HARBOR_MARKET_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = ["localhost", "testserver"]
ROOT_URLCONF = "harbor_market.composition.urls"
INSTALLED_APPS = ["harbor_market.infrastructure"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
