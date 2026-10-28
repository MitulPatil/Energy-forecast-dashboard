import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any

from pydantic import ValidationError

from app.clients.elexon import ElexonClient
from app.schemas import ActualGeneration, WindForecast

MAX_ACTUALS_CHUNK_DAYS = 7


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone information")
    return parsed.astimezone(timezone.utc)


def normalize_actuals(rows: list[dict[str, Any]]) -> list[ActualGeneration]:
    records: list[ActualGeneration] = []
    for row in rows:
        if row.get("fuelType") != "WIND":
            continue
        try:
            records.append(
                ActualGeneration(
                    start_time=_parse_utc(row["startTime"]),
                    publish_time=_parse_utc(row["publishTime"]) if row.get("publishTime") else None,
                    settlement_date=row.get("settlementDate"),
                    settlement_period=row.get("settlementPeriod"),
                    fuel_type=row["fuelType"],
                    generation_mw=float(row["generation"]),
                )
            )
        except (KeyError, TypeError, ValueError, ValidationError):
            continue
    return records


def normalize_forecasts(rows: list[dict[str, Any]]) -> list[WindForecast]:
    records: list[WindForecast] = []
    for row in rows:
        try:
            records.append(
                WindForecast(
                    start_time=_parse_utc(row["startTime"]),
                    publish_time=_parse_utc(row["publishTime"]),
                    generation_mw=(
                        float(row["generation"]) if row.get("generation") is not None else None
                    ),
                )
            )
        except (KeyError, TypeError, ValueError, ValidationError):
            continue
    return records


async def get_actuals(
    client: ElexonClient, start_date: date, end_date: date
) -> list[ActualGeneration]:
    chunks: list[tuple[date, date]] = []
    chunk_start = start_date
    while chunk_start <= end_date:
        chunk_end = min(
            chunk_start + timedelta(days=MAX_ACTUALS_CHUNK_DAYS - 1),
            end_date,
        )
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end + timedelta(days=1)

    semaphore = asyncio.Semaphore(4)

    async def fetch_chunk(chunk_start: date, chunk_end: date) -> list[dict[str, Any]]:
        async with semaphore:
            return await client.fetch_actuals(chunk_start, chunk_end)

    responses = await asyncio.gather(
        *[fetch_chunk(chunk_start, chunk_end) for chunk_start, chunk_end in chunks]
    )
    return normalize_actuals([row for response in responses for row in response])


async def get_forecasts(
    client: ElexonClient, publish_from: datetime, publish_to: datetime
) -> list[WindForecast]:
    return normalize_forecasts(await client.fetch_forecasts(publish_from, publish_to))
