# Copyright 2026 TM-59
"""The HTTP scaffold and the framework-free core."""

import subprocess
import sys
from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.test import Client


def test_req_health_get_returns_json(client: Client) -> None:
    """REQ-HEALTH: GET /health/ answers JSON status ok."""
    response = client.get("/health/")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}


def test_req_health_rejects_post(client: Client) -> None:
    """REQ-HEALTH: POST /health/ is not allowed."""
    assert client.post("/health/").status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_req_core_imports_without_frameworks() -> None:
    """REQ-CORE: domain and application import without site packages."""
    subprocess.run(
        [sys.executable, "-S", "-c", "import harbor_market.domain, harbor_market.application"],
        env={"PYTHONPATH": "src"},
        timeout=10,
        check=True,
    )
