"""Report and feature history routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import crud, schemas
from database.session import get_db

router = APIRouter(tags=["History"])


@router.get(
    "/reports/{company_name}",
    response_model=list[schemas.ReportResponse],
    summary="Get historical reports for a company",
)
def get_reports(company_name: str, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_reports_for_competitor(db, company_name, limit=limit)


@router.get(
    "/features/{company_name}",
    response_model=list[schemas.FeatureResponse],
    summary="Get all features ever extracted for a company",
)
def get_features(company_name: str, limit: int = 50, db: Session = Depends(get_db)):
    return crud.get_all_features_for_competitor(db, company_name, limit=limit)


@router.delete(
    "/reports/{report_id}",
    status_code=204,
    summary="Delete a report and all its features",
)
def delete_report(report_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_report(db, report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found.")
