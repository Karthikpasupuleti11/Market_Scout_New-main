"""
Market Intelligence Scout — Database CRUD Operations

Enterprise data access layer for PostgreSQL.
Handles: Competitor lookups, Feature saves, and Report persistence.
"""

from sqlalchemy.orm import Session
from .models import Competitor, Feature, Report
from .scheduled_job_model import ScheduledJob


# ────────────────────────────────────────────────────────────────────
# Scheduled Jobs
# ────────────────────────────────────────────────────────────────────

def create_scheduled_job(db: Session, company_name: str, email: str, scheduled_at) -> ScheduledJob:
    """Persist a new scheduled job (status=pending)."""
    job = ScheduledJob(company_name=company_name, email=email, scheduled_at=scheduled_at)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_scheduled_jobs(db: Session) -> list:
    """Return all scheduled jobs, newest first."""
    return db.query(ScheduledJob).order_by(ScheduledJob.created_at.desc()).all()


def delete_scheduled_job(db: Session, job_id: int) -> bool:
    """Delete a scheduled job record. Returns True if found."""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        return False
    db.delete(job)
    db.commit()
    return True


def update_job_status(db: Session, job_id: int, status: str,
                      report_id: int = None, error_msg: str = None) -> None:
    """Update job lifecycle fields after the runner fires."""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if job:
        job.status = status
        if report_id is not None:
            job.report_id = report_id
        if error_msg is not None:
            job.error_msg = error_msg
        db.commit()


# ────────────────────────────────────────────────────────────────────
# Competitors
# ────────────────────────────────────────────────────────────────────

def create_competitor(db: Session, name: str, industry: str = "technology") -> Competitor:
    """Create a new competitor record."""
    competitor = Competitor(name=name, industry=industry)
    db.add(competitor)
    db.commit()
    db.refresh(competitor)
    return competitor


def get_competitors(db: Session) -> list:
    """Retrieve all competitors."""
    return db.query(Competitor).all()


def get_or_create_competitor(db: Session, name: str) -> Competitor:
    """Find an existing competitor by name, or create a new one."""
    competitor = db.query(Competitor).filter(
        Competitor.name.ilike(name)
    ).first()

    if not competitor:
        competitor = Competitor(name=name, industry="technology")
        db.add(competitor)
        db.commit()
        db.refresh(competitor)

    return competitor


def delete_competitor(db: Session, competitor_id: int) -> bool:
    """Delete a competitor and all associated reports and features (cascade).

    Returns True if the competitor was found and deleted, False otherwise.
    """
    competitor = db.query(Competitor).filter(Competitor.id == competitor_id).first()
    if not competitor:
        return False
    db.delete(competitor)
    db.commit()
    return True


# ────────────────────────────────────────────────────────────────────
# Reports (Full Pipeline Run Persistence)
# ────────────────────────────────────────────────────────────────────

def save_report(db: Session, company_name: str, report_data: dict) -> Report:
    """Persist a complete pipeline run to PostgreSQL.

    Creates the competitor if it doesn't exist, saves the report,
    and saves each feature linked to both the report and competitor.
    """
    # Get or create competitor
    competitor = get_or_create_competitor(db, company_name)

    # Create the report
    report = Report(
        competitor_id=competitor.id,
        executive_summary=report_data.get("executive_summary", ""),
        total_sources=report_data.get("total_sources_analysed", 0),
        total_features=report_data.get("total_features_verified", 0),
        all_sources=report_data.get("all_sources", []),
        metadata_=report_data.get("metadata"),
    )
    db.add(report)
    db.flush()  # Get report.id without committing

    # Save each feature
    for f in report_data.get("features", []):
        if isinstance(f, dict):
            conf = f.get("confidence_score", 0.0) or 0.0
            # Derive importance from confidence if not explicitly set
            importance = f.get("importance")
            if not importance:
                if conf >= 0.7:
                    importance = "high"
                elif conf >= 0.4:
                    importance = "medium"
                else:
                    importance = "low"

            feature = Feature(
                competitor_id=competitor.id,
                report_id=report.id,
                feature_title=f.get("title", ""),
                feature_text=f.get("title") or f.get("description", ""),
                description=f.get("description", ""),
                category=f.get("category", ""),
                confidence_score=conf,
                impact_assessment=f.get("impact_assessment", ""),
                importance=importance,
                source_count=f.get("source_count", 1),
                source_url=f.get("source_url", ""),
                evidence=f.get("evidence", ""),
                metrics=f.get("key_metrics", []),
            )
            db.add(feature)

    db.commit()
    db.refresh(report)
    return report


def get_reports_for_competitor(db: Session, company_name: str, limit: int = 10) -> list:
    """Get the most recent reports for a company."""
    competitor = db.query(Competitor).filter(
        Competitor.name.ilike(company_name)
    ).first()

    if not competitor:
        return []

    return (
        db.query(Report)
        .filter(Report.competitor_id == competitor.id)
        .order_by(Report.created_at.desc())
        .limit(limit)
        .all()
    )


def get_all_features_for_competitor(db: Session, company_name: str, limit: int = 50) -> list:
    """Get all features ever extracted for a company (across all reports)."""
    competitor = db.query(Competitor).filter(
        Competitor.name.ilike(company_name)
    ).first()

    if not competitor:
        return []

    return (
        db.query(Feature)
        .filter(Feature.competitor_id == competitor.id)
        .order_by(Feature.created_at.desc())
        .limit(limit)
        .all()
    )


def delete_report(db: Session, report_id: int) -> bool:
    """Delete a report and all its associated features (cascade).

    Returns True if the report was found and deleted, False otherwise.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        return False
    db.delete(report)
    db.commit()
    return True


def get_latest_report_matching_window(
    db: Session,
    company_name: str,
    max_age_seconds: int = 21600,
) -> Report | None:
    """L2 cache lookup — find the most recent report within the time window.

    Returns the Report ORM object (with features loaded) or None.
    Used by the caching layer to re-warm Redis when L1 misses.
    """
    from datetime import datetime, timezone, timedelta

    competitor = db.query(Competitor).filter(
        Competitor.name.ilike(company_name)
    ).first()

    if not competitor:
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)

    return (
        db.query(Report)
        .filter(
            Report.competitor_id == competitor.id,
            Report.created_at >= cutoff,
        )
        .order_by(Report.created_at.desc())
        .first()
    )