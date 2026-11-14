import os
import secrets
from pathlib import Path

import django

Path("test-results").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "harbor_market.composition.settings")
os.environ.setdefault("HARBOR_MARKET_SECRET_KEY", secrets.token_urlsafe(48))
django.setup()
