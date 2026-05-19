import asyncio

from app.celery_app import celery
from graph.builder import build_graph
from database.session import get_db
from database import crud
from observability.metrics import (
    PIPELINE_RUNS,
    FEATURES_EXTRACTED,
)

from utils.feature_utils import _safe_feature
from app.rag.service import process_report

import asyncio

graph = build_graph()

@celery.task(bind=True)
def run_market_pipeline(self, company_name, date_window_days, session_id):

    result = asyncio.run (
        graph.ainvoke({
            "company_name": company_name,
            "date_window_days": date_window_days,
        })
    )

    report = result.get("synthesis_report", {})

    if not report:
        raise Exception("Pipeline produced no report")

    # ── Metrics ──────────────────────────────
    error = result.get("error") or report.get("metadata", {}).get("error")
    features = report.get("features", [])

    if error and not features:
        PIPELINE_RUNS.labels(status="error").inc()
    else:
        PIPELINE_RUNS.labels(status="completed").inc()

    for f in features:
        cat = f.get("category", "unknown")
        FEATURES_EXTRACTED.labels(
            company=company_name,
            category=cat
        ).inc()

    # ── Safe Features ───────────────────────
    safe_features = []

    for i, f in enumerate(features):
        try:
            safe_features.append(
                _safe_feature(f, i).model_dump()
            )
        except Exception:
            pass

    # ── Response ────────────────────────────
    response = {
        "company_name": report.get("company_name"),
        "generated_at": report.get("generated_at"),
        "executive_summary": report.get("executive_summary"),
        "features": safe_features,
        "total_sources_analysed":
            report.get("total_sources_analysed", 0),
        "total_features_verified":
            report.get("total_features_verified", 0),
        "all_sources": report.get("all_sources", []),
        "metadata": report.get("metadata"),
    }

    # ── Build conversational RAG index ─────────────────

    try:
        asyncio.run(process_report(response, session_id))
    except Exception as e:
        print("RAG processing failed:", e)

    # ── Save DB ─────────────────────────────
    try:
        db = next(get_db())
        crud.save_report(db, company_name, report)
    except Exception as e:
        print("DB save failed:", e)

    return response