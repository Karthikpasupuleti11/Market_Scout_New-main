"""Scheduled report jobs."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import crud, schemas
from database.session import SessionLocal, get_db
from scheduler import scheduler

router = APIRouter(tags=["Schedules"])


@router.post("/schedules", response_model=schemas.ScheduledJobResponse)
def create_schedule(
    job: schemas.ScheduledJobCreate, request: Request, db: Session = Depends(get_db)
):
    if job.scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400, detail="Scheduled time must be in the future."
        )

    db_job = crud.create_scheduled_job(
        db, job.company_name, job.email, job.scheduled_at
    )

    if settings_enable_scheduler():
        scheduler.schedule_job(
            job_id=db_job.id,
            run_at=job.scheduled_at,
            company_name=job.company_name,
            email=job.email,
            db_factory=SessionLocal,
            graph=request.app.state.graph,
        )

    return db_job


@router.get("/schedules", response_model=list[schemas.ScheduledJobResponse])
def get_schedules(db: Session = Depends(get_db)):
    return crud.get_scheduled_jobs(db)


@router.delete("/schedules/{job_id}", status_code=204)
def delete_schedule(job_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_scheduled_job(db, job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    if settings_enable_scheduler():
        scheduler.cancel_job(job_id)


def settings_enable_scheduler() -> bool:
    from app.config import settings

    return settings.ENABLE_SCHEDULER
