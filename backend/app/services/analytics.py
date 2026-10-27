from datetime import date, datetime, time, timedelta, timezone

from app.analytics import AnalyticsResult, analyze
from app.clients.elexon import ElexonClient
from app.services.data import get_actuals, get_forecasts


async def get_analytics(
    client: ElexonClient,
    start_date: date,
    end_date: date,
    cutoff_hour: int = 23,
) -> AnalyticsResult:
    actuals = await get_actuals(client, start_date, end_date)
    publish_from = datetime.combine(
        start_date - timedelta(days=2), time.min, tzinfo=timezone.utc
    )
    publish_to = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    forecasts = await get_forecasts(client, publish_from, publish_to)
    return analyze(actuals, forecasts, cutoff_hour)
