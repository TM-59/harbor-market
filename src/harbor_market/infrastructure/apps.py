# Copyright 2026 TM-59
"""Django application configuration of the persistence adapter."""

from django.apps import AppConfig


class InfrastructureConfig(AppConfig):
    """Register the persistence models under their own app label."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "harbor_market.infrastructure"
    label = "harbor_market_infrastructure"
