# Copyright 2026 TM-59
"""Transport health only; no trading rules live here."""

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(_request: HttpRequest) -> JsonResponse:
    """Answer GET with a JSON status for liveness checks."""
    return JsonResponse({"status": "ok"})
