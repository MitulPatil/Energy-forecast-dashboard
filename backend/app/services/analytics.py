import asyncio
from datetime import date, datetime, time, timedelta, timezone

from app.analytics import AnalyticsResult, analyze
from app.clients.elexon import ElexonClient
from app.schemas import WindForecast
from app.services.data import get_actuals, get_forecasts


async def _get_forecasts_in_chunks(
    client: ElexonClient,
    publish_from: datetime,
    publish_to: datetime,
) -> list[WindForecast]:
    chunks: list[tuple[datetime, datetime]] = []
    chunk_start = publish_from
    while chunk_start < publish_to:
        chunk_end = min(chunk_start + timedelta(days=1), publish_to)
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end

    semaphore = asyncio.Semaphore(4)

    async def fetch_chunk(chunk_start: datetime, chunk_end: datetime) -> list[WindForecast]:
        async with semaphore:
            return await get_forecasts(client, chunk_start, chunk_end)

    responses = await asyncio.gather(
        *[fetch_chunk(chunk_start, chunk_end) for chunk_start, chunk_end in chunks]
    )
    return [forecast for response in responses for forecast in response]


async def get_analytics(
    client: ElexonClient,
    start_date: date,
    end_date: date,
    cutoff_hour: int = 23,
) -> AnalyticsResult:
    actuals = await get_actuals(client, start_date, end_date)
    publish_from = datetime.combine(
        start_date - timedelta(days=1), time.min, tzinfo=timezone.utc
    )
    publish_to = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    forecasts = await _get_forecasts_in_chunks(client, publish_from, publish_to)
    return analyze(actuals, forecasts, cutoff_hour)
