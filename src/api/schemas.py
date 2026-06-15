from pydantic import BaseModel, field_validator
from datetime import date
from typing import Optional


class ProgramResponse(BaseModel):
    signal: str
    program_code: str
    date: date
    weekday: int
    available_time: int
    predicted_audience: Optional[int]

    @field_validator("predicted_audience", mode="before")
    @classmethod
    def round_audience(cls, v):
        if v is None:
            return v
        return round(v)


class PeriodResponse(BaseModel):
    items: list[ProgramResponse]
    total: int
