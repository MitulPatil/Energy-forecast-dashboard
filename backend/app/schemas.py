from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ActualGeneration(BaseModel):
    model_config = ConfigDict(extra="ignore")

    start_time: datetime
    publish_time: datetime | None = None
    settlement_date: str | None = None
    settlement_period: int | None = None
    fuel_type: str
    generation_mw: float


class WindForecast(BaseModel):
    model_config = ConfigDict(extra="ignore")

    start_time: datetime
    publish_time: datetime
    generation_mw: float | None = None


class DateRange(BaseModel):
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
