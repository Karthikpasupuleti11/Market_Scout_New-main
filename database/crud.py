"""
Market Intelligence Scout — Database CRUD Operations

Enterprise data access layer for PostgreSQL.
Handles: Competitor lookups, Feature saves, and Report persistence.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload

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


def delete_cached_reports_for_company(
    db: Session,
    company_name: str,
    date_window_days: int,
    max_age_seconds: int,
) -> int:
    """Delete report rows used by the cache fast-path (within max_age, matching window)."""
    competitor = db.query(Competitor).filter(
        Competitor.name.ilike(company_name.strip())
    ).first()
    if not competitor:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
    candidates = (
        db.query(Report)
        .filter(
            Report.competitor_id == competitor.id,
            Report.created_at >= cutoff,
        )
        .all()
    )

    target_days = int(date_window_days)
    deleted = 0
    for report in candidates:
        meta = report.metadata_ or {}
        stored_days = meta.get("date_window_days")
        if stored_days is None or int(stored_days) == target_days:
            db.delete(report)
            deleted += 1

    if deleted:
        db.commit()
    return deleted


def get_latest_report_matching_window(
    db: Session,
    company_name: str,
    date_window_days: int,
    max_age_seconds: int,
) -> Optional[Report]:
    """Latest report for a company matching the recency window, within max_age."""
    competitor = db.query(Competitor).filter(
        Competitor.name.ilike(company_name.strip())
    ).first()
    if not competitor:
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
    candidates = (
        db.query(Report)
        .options(joinedload(Report.features))
        .filter(
            Report.competitor_id == competitor.id,
            Report.created_at >= cutoff,
        )
        .order_by(Report.created_at.desc())
        .limit(20)
        .all()
    )

    target_days = int(date_window_days)
    for report in candidates:
        meta = report.metadata_ or {}
        stored_days = meta.get("date_window_days")
        if stored_days is None or int(stored_days) == target_days:
            return report
    return None


def report_to_synthesis_dict(report: Report, company_name: str) -> dict:
    """Reconstruct pipeline synthesis_report JSON from a persisted Report."""
    features = []
    for i, f in enumerate(report.features or []):
        features.append({
            "rank": i + 1,
            "title": f.feature_title or f.feature_text or "",
            "description": f.description or f.feature_text or "",
            "category": f.category,
            "confidence_score": f.confidence_score,
            "impact_assessment": f.impact_assessment,
            "source_url": f.source_url,
            "source_count": f.source_count,
            "key_metrics": f.metrics if isinstance(f.metrics, list) else [],
        })

    meta = dict(report.metadata_ or {})
    generated_at = (
        report.created_at.isoformat()
        if report.created_at
        else datetime.now(timezone.utc).isoformat()
    )

    return {
        "company_name": company_name,
        "generated_at": generated_at,
        "executive_summary": report.executive_summary or "",
        "features": features,
        "total_sources_analysed": report.total_sources or 0,
        "total_features_verified": report.total_features or len(features),
        "all_sources": report.all_sources or [],
        "metadata": meta,
    }


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


def get_latest_report(db: Session) -> dict | None:
    """Get the most recent report across ALL companies.

    Returns a dict with report info + company name, or None.
    """
    result = (
        db.query(Report, Competitor.name)
        .join(Competitor, Report.competitor_id == Competitor.id)
        .order_by(Report.created_at.desc())
        .first()
    )
    if not result:
        return None
    report, company_name = result
    return {
        "id": report.id,
        "company_name": company_name,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "total_features": report.total_features,
        "total_sources": report.total_sources,
        "executive_summary": report.executive_summary,
    }
