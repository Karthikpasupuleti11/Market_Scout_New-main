"""Competitor (watchlist) CRUD routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import crud, schemas
from database.session import get_db

router = APIRouter(tags=["Database"])


@router.post("/competitors", response_model=schemas.CompetitorResponse)
def create_competitor(
    competitor: schemas.CompetitorCreate, db: Session = Depends(get_db)
):
    return crud.create_competitor(db, name=competitor.name, industry=competitor.industry)


@router.get("/competitors", response_model=list[schemas.CompetitorResponse])
def read_competitors(db: Session = Depends(get_db)):
    return crud.get_competitors(db)


@router.delete(
    "/competitors/{competitor_id}",
    status_code=204,
    summary="Delete a competitor and all its reports/features",
)
def delete_competitor(competitor_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_competitor(db, competitor_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Competitor {competitor_id} not found."
        )
