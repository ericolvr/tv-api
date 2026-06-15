"""FastAPI application — exposes audience and inventory endpoints."""

from datetime import date as date_type

from fastapi import FastAPI, HTTPException, Query

from .repository import get_by_period, get_by_program
from .schemas import PeriodResponse, ProgramResponse

app = FastAPI(
    title="TV Aberta Audience API",
    description="Retorna audiência prevista e disponibilidade de inventário para anúncios.",
    version="1.0.0",
)


@app.get("/program", response_model=list[ProgramResponse])
def program(
    program_code: str = Query(..., description="Código do programa (ex: HUCK)"),
    date: date_type = Query(..., description="Data de exibição (YYYY-MM-DD)"),
):
    """
    Retorna os segundos disponíveis para anúncios e a audiência prevista
    para um programa em uma data específica.
    """
    rows = get_by_program(program_code, date)
    if not rows:
        raise HTTPException(status_code=404, detail="Programa ou data não encontrados.")
    return rows


@app.get("/period", response_model=PeriodResponse)
def period(
    start: date_type = Query(..., description="Data de início do período (YYYY-MM-DD)"),
    end: date_type = Query(..., description="Data de fim do período (YYYY-MM-DD)"),
):
    """
    Retorna todos os programas exibidos no período com segundos disponíveis
    para anúncios e audiência prevista.
    """
    if start > end:
        raise HTTPException(status_code=422, detail="'start' deve ser anterior a 'end'.")
    rows = get_by_period(start, end)
    return {"items": rows, "total": len(rows)}
