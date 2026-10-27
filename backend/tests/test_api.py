from fastapi.testclient import TestClient
import unittest

from app.clients.elexon import ElexonClient
from app.main import app


class FakeElexonClient(ElexonClient):
    def __init__(self):
        pass

    async def fetch_actuals(self, start_date, end_date):
        return [
            {
                "startTime": "2026-01-02T00:00:00Z",
                "publishTime": "2026-01-02T00:30:00Z",
                "fuelType": "WIND",
                "generation": 100,
            }
        ]

    async def fetch_forecasts(self, publish_from, publish_to):
        return [
            {
                "startTime": "2026-01-02T00:00:00Z",
                "publishTime": "2026-01-01T22:30:00Z",
                "generation": 120,
            }
        ]


class ApiTests(unittest.TestCase):
    def test_health_endpoint(self) -> None:
        response = TestClient(app).get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_date_range_validation(self) -> None:
        response = TestClient(app).get(
            "/api/data/actuals",
            params={"start_date": "2026-01-02", "end_date": "2026-01-01"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("end_date", response.json()["detail"])

    def test_summary_returns_typed_analytics_payload(self) -> None:
        from app.api import get_client

        app.dependency_overrides[get_client] = lambda: FakeElexonClient()
        try:
            response = TestClient(app).get(
                "/api/analytics/summary",
                params={"start_date": "2026-01-02", "end_date": "2026-01-02"},
            )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["matched_count"], 1)
        self.assertEqual(payload["intervals"][0]["error_mw"], 20)
        self.assertEqual(payload["intervals"][0]["forecast_publish_time"], "2026-01-01T22:30:00Z")

    def test_summary_rejects_invalid_cutoff(self) -> None:
        response = TestClient(app).get(
            "/api/analytics/summary",
            params={
                "start_date": "2026-01-02",
                "end_date": "2026-01-02",
                "cutoff_hour": 24,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("cutoff_hour", response.json()["detail"])

    def test_cors_allows_local_frontend(self) -> None:
        response = TestClient(app).options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")
