from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.analytics import AnalyticsResult, MatchedInterval
from app.clients.elexon import ElexonApiError, ElexonClient
from app.config import Settings, get_settings
from app.schemas import ActualGeneration, WindForecast
from app.services.analytics import get_analytics
from app.services.data import get_actuals, get_forecasts

router = APIRouter(prefix="/api")


def get_client(settings: Settings = Depends(get_settings)) -> ElexonClient:
    return ElexonClient(settings)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/data/actuals", response_model=list[ActualGeneration])
async def actuals(
    start_date: date = Query(...),
    end_date: date = Query(...),
    client: ElexonClient = Depends(get_client),
) -> list[ActualGeneration]:
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must not be before start_date")
    try:
        return await get_actuals(client, start_date, end_date)
    except ElexonApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/data/forecasts", response_model=list[WindForecast])
async def forecasts(
    publish_from: datetime = Query(...),
    publish_to: datetime = Query(...),
    client: ElexonClient = Depends(get_client),
) -> list[WindForecast]:
    if publish_from.tzinfo is None or publish_to.tzinfo is None:
        raise HTTPException(status_code=400, detail="forecast timestamps must include a timezone")
    if publish_to < publish_from:
        raise HTTPException(status_code=400, detail="publish_to must not be before publish_from")
    try:
        return await get_forecasts(
            client,
            publish_from.astimezone(timezone.utc),
            publish_to.astimezone(timezone.utc),
        )
    except ElexonApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


async def _analytics(
    start_date: date,
    end_date: date,
    cutoff_hour: int,
    client: ElexonClient,
) -> AnalyticsResult:
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must not be before start_date")
    if not 0 <= cutoff_hour <= 23:
        raise HTTPException(status_code=400, detail="cutoff_hour must be between 0 and 23")
    try:
        return await get_analytics(client, start_date, end_date, cutoff_hour)
    except ElexonApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/analytics/summary", response_model=AnalyticsResult)
async def summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    cutoff_hour: int = Query(23),
    client: ElexonClient = Depends(get_client),
) -> AnalyticsResult:
    return await _analytics(start_date, end_date, cutoff_hour, client)


@router.get("/analytics/timeseries", response_model=list[MatchedInterval])
async def timeseries(
    start_date: date = Query(...),
    end_date: date = Query(...),
    cutoff_hour: int = Query(23),
    client: ElexonClient = Depends(get_client),
) -> list[MatchedInterval]:
    result = await _analytics(start_date, end_date, cutoff_hour, client)
    return result.intervals


@router.get("/analytics/errors", response_model=list[MatchedInterval])
async def errors(
    start_date: date = Query(...),
    end_date: date = Query(...),
    cutoff_hour: int = Query(23),
    client: ElexonClient = Depends(get_client),
) -> list[MatchedInterval]:
    result = await _analytics(start_date, end_date, cutoff_hour, client)
    return sorted(
        [interval for interval in result.intervals if interval.absolute_error_mw is not None],
        key=lambda interval: interval.absolute_error_mw or 0,
        reverse=True,
    )
