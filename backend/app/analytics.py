from datetime import date, datetime, time, timedelta, timezone
from math import sqrt

from pydantic import BaseModel, ConfigDict

from app.schemas import ActualGeneration, WindForecast


class MatchedInterval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_time: datetime
    forecast_publish_time: datetime | None = None
    forecast_mw: float | None = None
    actual_mw: float
    error_mw: float | None = None
    absolute_error_mw: float | None = None
    percentage_error: float | None = None


class AnalyticsResult(BaseModel):
    intervals: list[MatchedInterval]
    matched_count: int
    unmatched_count: int
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    mape_percent: float | None


def decision_cutoff(delivery_time: datetime, cutoff_hour: int = 23) -> datetime:
    delivery_date = delivery_time.astimezone(timezone.utc).date()
    cutoff_date = delivery_date - timedelta(days=1)
    return datetime.combine(cutoff_date, time(hour=cutoff_hour, tzinfo=timezone.utc))


def _forecast_hour(delivery_time: datetime) -> datetime:
    utc_time = delivery_time.astimezone(timezone.utc)
    return utc_time.replace(minute=0, second=0, microsecond=0)


def _latest_actuals(actuals: list[ActualGeneration]) -> list[ActualGeneration]:
    latest: dict[datetime, ActualGeneration] = {}
    for actual in actuals:
        current = latest.get(actual.start_time)
        if current is None or (actual.publish_time or datetime.min.replace(tzinfo=timezone.utc)) > (
            current.publish_time or datetime.min.replace(tzinfo=timezone.utc)
        ):
            latest[actual.start_time] = actual
    return sorted(latest.values(), key=lambda item: item.start_time)


def _select_forecast(
    delivery_time: datetime,
    forecasts: list[WindForecast],
    cutoff_hour: int,
) -> WindForecast | None:
    cutoff = decision_cutoff(delivery_time, cutoff_hour)
    candidates = [
        forecast
        for forecast in forecasts
        if forecast.generation_mw is not None
        and _forecast_hour(forecast.start_time) == _forecast_hour(delivery_time)
        and forecast.publish_time <= cutoff
    ]
    return max(candidates, key=lambda item: item.publish_time, default=None)


def analyze(
    actuals: list[ActualGeneration],
    forecasts: list[WindForecast],
    cutoff_hour: int = 23,
) -> AnalyticsResult:
    intervals: list[MatchedInterval] = []
    for actual in _latest_actuals(actuals):
        forecast = _select_forecast(actual.start_time, forecasts, cutoff_hour)
        if forecast is None:
            intervals.append(
                MatchedInterval(delivery_time=actual.start_time, actual_mw=actual.generation_mw)
            )
            continue

        error = forecast.generation_mw - actual.generation_mw
        percentage_error = (
            error / actual.generation_mw * 100 if actual.generation_mw != 0 else None
        )
        intervals.append(
            MatchedInterval(
                delivery_time=actual.start_time,
                forecast_publish_time=forecast.publish_time,
                forecast_mw=forecast.generation_mw,
                actual_mw=actual.generation_mw,
                error_mw=error,
                absolute_error_mw=abs(error),
                percentage_error=percentage_error,
            )
        )

    errors = [item.error_mw for item in intervals if item.error_mw is not None]
    absolute_errors = [abs(error) for error in errors]
    percentage_errors = [
        abs(item.percentage_error)
        for item in intervals
        if item.percentage_error is not None
    ]
    return AnalyticsResult(
        intervals=intervals,
        matched_count=len(errors),
        unmatched_count=len(intervals) - len(errors),
        mae_mw=sum(absolute_errors) / len(errors) if errors else None,
        rmse_mw=sqrt(sum(error * error for error in errors) / len(errors)) if errors else None,
        bias_mw=sum(errors) / len(errors) if errors else None,
        mape_percent=sum(percentage_errors) / len(percentage_errors)
        if percentage_errors
        else None,
    )
