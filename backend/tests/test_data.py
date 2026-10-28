from datetime import date, datetime, timezone
import unittest

import httpx

from app.clients.elexon import ElexonApiError, ElexonClient
from app.config import Settings
from app.services.data import normalize_actuals, normalize_forecasts


class DataNormalizationTests(unittest.TestCase):
    def test_actuals_are_fetched_in_seven_day_chunks(self) -> None:
        class FakeClient:
            def __init__(self) -> None:
                self.ranges = []

            async def fetch_actuals(self, start_date, end_date):
                self.ranges.append((start_date, end_date))
                return []

        async def run() -> None:
            from app.services.data import get_actuals

            client = FakeClient()
            await get_actuals(client, date(2026, 1, 1), date(2026, 1, 20))
            self.assertEqual(
                sorted(client.ranges),
                [
                    (date(2026, 1, 1), date(2026, 1, 7)),
                    (date(2026, 1, 8), date(2026, 1, 14)),
                    (date(2026, 1, 15), date(2026, 1, 20)),
                ],
            )

        import asyncio

        asyncio.run(run())

    def test_normalize_actuals_keeps_wind_rows_and_normalizes_timestamps(self) -> None:
        rows = [
            {
                "startTime": "2026-01-01T00:00:00Z",
                "publishTime": "2026-01-01T00:30:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 13756,
            },
            {"startTime": "2026-01-01T00:00:00Z", "fuelType": "CCGT", "generation": 100},
            {"startTime": "not-a-time", "fuelType": "WIND", "generation": 100},
        ]

        actuals = normalize_actuals(rows)

        self.assertEqual(len(actuals), 1)
        self.assertEqual(actuals[0].start_time, datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(actuals[0].generation_mw, 13756)

    def test_normalize_forecasts_allows_missing_generation_but_rejects_bad_rows(self) -> None:
        rows = [
            {
                "startTime": "2026-01-01T00:00:00Z",
                "publishTime": "2025-12-31T23:00:00Z",
                "generation": None,
            },
            {"startTime": "2026-01-01T01:00:00Z", "generation": 10},
        ]

        forecasts = normalize_forecasts(rows)

        self.assertEqual(len(forecasts), 1)
        self.assertIsNone(forecasts[0].generation_mw)

    def test_upstream_http_failure_is_explicit(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, request=request)

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(
                base_url="https://example.test",
                transport=transport,
            ) as http_client:
                client = ElexonClient(Settings(), http_client)
                with self.assertRaises(ElexonApiError):
                    await client.fetch_actuals(date(2026, 1, 1), date(2026, 1, 1))

        import asyncio

        asyncio.run(run())
