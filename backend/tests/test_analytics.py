from datetime import datetime, timezone
import unittest

from app.analytics import analyze, decision_cutoff
from app.schemas import ActualGeneration, WindForecast


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def actual(start: str, generation: float) -> ActualGeneration:
    return ActualGeneration(
        start_time=dt(start),
        fuel_type="WIND",
        generation_mw=generation,
    )


def forecast(start: str, published: str, generation: float | None) -> WindForecast:
    return WindForecast(
        start_time=dt(start),
        publish_time=dt(published),
        generation_mw=generation,
    )


class AnalyticsTests(unittest.TestCase):
    def test_selects_latest_forecast_before_cutoff_and_matches_hourly_forecast(self) -> None:
        result = analyze(
            [
                actual("2026-01-02T00:00:00", 100),
                actual("2026-01-02T00:30:00", 120),
            ],
            [
                forecast("2026-01-02T00:00:00", "2026-01-01T22:00:00", 90),
                forecast("2026-01-02T00:00:00", "2026-01-01T22:30:00", 110),
                forecast("2026-01-02T00:00:00", "2026-01-01T23:30:00", 999),
            ],
        )

        self.assertEqual(result.matched_count, 2)
        self.assertEqual(result.intervals[0].forecast_mw, 110)
        self.assertEqual(result.intervals[1].forecast_mw, 110)
        self.assertEqual(result.intervals[0].error_mw, 10)

    def test_metrics_and_zero_actual_percentage(self) -> None:
        result = analyze(
            [actual("2026-01-02T00:00:00", 0), actual("2026-01-02T01:00:00", 100)],
            [
                forecast("2026-01-02T00:00:00", "2026-01-01T22:30:00", 20),
                forecast("2026-01-02T01:00:00", "2026-01-01T22:30:00", 120),
            ],
        )

        self.assertEqual(result.mae_mw, 20)
        self.assertEqual(result.rmse_mw, 20)
        self.assertEqual(result.bias_mw, 20)
        self.assertEqual(result.mape_percent, 20)
        self.assertIsNone(result.intervals[0].percentage_error)

    def test_duplicate_actual_uses_latest_published_record(self) -> None:
        result = analyze(
            [
                ActualGeneration(
                    start_time=dt("2026-01-02T00:00:00"),
                    publish_time=dt("2026-01-02T00:30:00"),
                    fuel_type="WIND",
                    generation_mw=100,
                ),
                ActualGeneration(
                    start_time=dt("2026-01-02T00:00:00"),
                    publish_time=dt("2026-01-02T01:00:00"),
                    fuel_type="WIND",
                    generation_mw=120,
                ),
            ],
            [forecast("2026-01-02T00:00:00", "2026-01-01T22:30:00", 100)],
        )

        self.assertEqual(len(result.intervals), 1)
        self.assertEqual(result.intervals[0].actual_mw, 120)

    def test_cutoff_is_previous_delivery_day(self) -> None:
        self.assertEqual(
            decision_cutoff(dt("2026-01-02T00:30:00")),
            dt("2026-01-01T23:00:00"),
        )
