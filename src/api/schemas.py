"""Pydantic schemas for API request/response validation."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator


class ProgramResponse(BaseModel):
    """Response schema for a single program inventory record."""

    signal: str
    program_code: str
    date: date
    weekday: int
    available_time: int
    predicted_audience: Optional[int]

    @field_validator("predicted_audience", mode="before")
    @classmethod
    def round_audience(cls, v):
        """Round predicted audience to nearest integer."""
        if v is None:
            return v
        return round(v)


class PeriodResponse(BaseModel):
    """Response schema for a period query."""

    items: list[ProgramResponse]
    total: int
