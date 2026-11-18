import subprocess
import sys
from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.test import Client


def test_req_health_get_returns_json(client: Client) -> None:
    response = client.get("/health/")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}


def test_req_health_rejects_post(client: Client) -> None:
    assert client.post("/health/").status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_req_core_imports_without_frameworks() -> None:
    subprocess.run(
        [sys.executable, "-S", "-c", "import harbor_market.domain, harbor_market.application"],
        env={"PYTHONPATH": "src"},
        timeout=10,
        check=True,
    )
