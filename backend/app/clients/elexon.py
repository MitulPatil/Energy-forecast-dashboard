from datetime import date, datetime
from typing import Any

import httpx

from app.config import Settings


class ElexonApiError(RuntimeError):
    pass


class ElexonClient:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None):
        self._settings = settings
        self._http_client = http_client

    async def _get(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(
            base_url=self._settings.elexon_base_url,
            timeout=self._settings.http_timeout_seconds,
        )
        try:
            response = await client.get(path, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ElexonApiError(f"Elexon request failed for {path}") from exc
        finally:
            if owns_client:
                await client.aclose()

        if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
            raise ElexonApiError(f"Elexon returned an invalid response for {path}")
        return payload

    async def fetch_actuals(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        return await self._get(
            "/datasets/FUELHH/stream",
            {
                "settlementDateFrom": start_date.isoformat(),
                "settlementDateTo": end_date.isoformat(),
                "fuelType": "WIND",
            },
        )

    async def fetch_forecasts(
        self, publish_from: datetime, publish_to: datetime
    ) -> list[dict[str, Any]]:
        return await self._get(
            "/datasets/WINDFOR/stream",
            {
                "publishDateTimeFrom": publish_from.isoformat(),
                "publishDateTimeTo": publish_to.isoformat(),
            },
        )
