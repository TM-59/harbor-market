import os
import secrets

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "harbor_market.composition.settings")
os.environ.setdefault("HARBOR_MARKET_SECRET_KEY", secrets.token_urlsafe(48))
django.setup()
