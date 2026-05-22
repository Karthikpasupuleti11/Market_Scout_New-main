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

# ── Node-to-stage mapping for PROGRESS tracking ─────────────
# The graph nodes in execution order
NODE_ORDER = [
    "guardrails",
    "search_agent",
    "scraper_agent",
    "date_validation",
    "content_filter",
    "authority_check",
    "feature_extraction",
    "verification",
    "scoring",
    "synthesis",
]

graph = build_graph()

@celery.task(bind=True)
def run_market_pipeline(self, company_name, date_window_days, session_id):

    # ── Report progress before starting ────────────────
    self.update_state(
        state="PROGRESS",
        meta={"current_node": "guardrails", "progress": 0}
    )

    async def run_and_stream():
        final_report = {}
        final_error = None
        
        async for event in graph.astream(
            {"company_name": company_name, "date_window_days": date_window_days},
            stream_mode="updates"
        ):
            for node_name, state_updates in event.items():
                
                try:
                    idx = NODE_ORDER.index(node_name)
                    next_idx = idx + 1
                    if next_idx < len(NODE_ORDER):
                        next_node = NODE_ORDER[next_idx]
                    else:
                        next_node = node_name
                except ValueError:
                    next_node = node_name

                self.update_state(
                    state="PROGRESS",
                    meta={"current_node": next_node, "progress": 0}
                )
                if "synthesis_report" in state_updates:
                    final_report = state_updates["synthesis_report"]
                if "error" in state_updates:
                    final_error = state_updates["error"]
                    
        return {"synthesis_report": final_report, "error": final_error}

    result = asyncio.run(run_and_stream())

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



    # ── Save DB + Cache (only if pipeline produced actual features) ──
    if safe_features:
        try:
            db = next(get_db())
            crud.save_report(db, company_name, report)
        except Exception as e:
            print("DB save failed:", e)

        # ── Warm the report cache (L1) ─────────────────────
        try:
            from cache.report_cache import set_report_in_redis
            set_report_in_redis(company_name, date_window_days, response)
        except Exception as e:
            print("Report cache warming failed:", e)
    else:
        print(f"SKIP SAVE — No features extracted for '{company_name}', not saving empty report to DB or cache.")

    return response