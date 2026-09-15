"""HTTP client for the local Psydekik API."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from frontend_console.api.models import SystemStatus


class PsydekikApiError(RuntimeError):
    """Raised when the Psydekik API cannot be reached."""


class PsydekikApiClient:
    """Small synchronous client for Psydekik's local API.

    Bootstack must call this client from a worker thread so
    network activity never blocks Tk's graphical event loop.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        timeout_seconds: float = 3.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_system_status(self) -> SystemStatus:
        """Retrieve and parse the latest system status."""

        payload = self._get_json(
            "/api/system/status"
        )

        return SystemStatus.from_dict(payload)

    def health_check(self) -> bool:
        """Return whether the API health endpoint responds."""

        payload = self._get_json("/health")
        return payload.get("status") == "healthy"

    def _get_json(
        self,
        path: str,
    ) -> dict:
        """Perform a JSON GET request."""

        request = Request(
            f"{self.base_url}{path}",
            headers={
                "Accept": "application/json",
                "User-Agent": (
                    "Psydekik-Bootstack-Console/0.1"
                ),
            },
            method="GET",
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                body = response.read()

        except HTTPError as exc:
            raise PsydekikApiError(
                f"API returned HTTP {exc.code}."
            ) from exc

        except URLError as exc:
            raise PsydekikApiError(
                "Psydekik API is unavailable."
            ) from exc

        except TimeoutError as exc:
            raise PsydekikApiError(
                "Psydekik API request timed out."
            ) from exc

        try:
            payload = json.loads(body)

        except json.JSONDecodeError as exc:
            raise PsydekikApiError(
                "Psydekik API returned invalid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise PsydekikApiError(
                "Psydekik API returned an unexpected response."
            )

        return payload
