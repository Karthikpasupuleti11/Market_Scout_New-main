"""Intelligence pipeline — Celery enqueue and task polling."""

from fastapi import APIRouter

from app.schemas.api import AgentRequest, TaskStatusResponse
from app.services.pipeline_enqueue import enqueue_pipeline_or_cache

router = APIRouter(tags=["Intelligence"])


@router.post(
    "/run-agent",
    summary="Submit Market Intelligence Pipeline (async via Celery)",
)
async def run_agent(request: AgentRequest):
    """Enqueue the pipeline. Poll ``GET /task/{task_id}`` for progress and results."""
    return enqueue_pipeline_or_cache(
        request.company_name,
        request.date_window_days,
        request.force_refresh,
    )


@router.get(
    "/task/{task_id}",
    response_model=TaskStatusResponse,
    summary="Poll pipeline task status",
)
async def get_task_status(task_id: str):
    """Status values: PENDING, STARTED, PROGRESS, SUCCESS, FAILURE, RETRY, REVOKED."""
    from tasks.pipeline_tasks import run_pipeline_task

    result = run_pipeline_task.AsyncResult(task_id)
    response: dict = {"task_id": task_id, "status": result.status}

    if result.status == "PROGRESS":
        response["progress"] = result.info or {}
    elif result.status == "SUCCESS":
        response["result"] = result.result
    elif result.status == "FAILURE":
        detail = str(result.result) if result.result else "Task failed"
        response["error"] = detail
    elif result.status == "RETRY":
        response["progress"] = {"message": "Task is being retried"}

    return response
