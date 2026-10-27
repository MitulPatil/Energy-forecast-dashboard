from datetime import date, datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.clients.elexon import ElexonClient
from app.schemas import ActualGeneration, WindForecast


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
    return normalize_actuals(await client.fetch_actuals(start_date, end_date))


async def get_forecasts(
    client: ElexonClient, publish_from: datetime, publish_to: datetime
) -> list[WindForecast]:
    return normalize_forecasts(await client.fetch_forecasts(publish_from, publish_to))
