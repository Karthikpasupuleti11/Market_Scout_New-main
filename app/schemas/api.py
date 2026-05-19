"""API request/response models shared across routers."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentRequest(BaseModel):
    company_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Name of the company to analyse",
        examples=["OpenAI", "Google DeepMind", "Anthropic"],
    )
    date_window_days: int = Field(
        7,
        ge=1,
        le=365,
        description="Recency window (in days) used for date validation + scoring + synthesis",
        examples=[7, 14, 30],
    )
    force_refresh: bool = Field(
        False,
        description=(
            "If true, delete this company's cached report (Redis + DB, within "
            "REPORT_CACHE_MAX_AGE) for the date window, then run a full pipeline"
        ),
    )


class FeatureItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rank: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    confidence_score: Optional[float] = None
    impact_assessment: Optional[str] = None
    source_url: Optional[str] = None
    source_count: Optional[int] = None
    key_metrics: Optional[List[str]] = None


def safe_feature(f: dict, idx: int) -> FeatureItem:
    """Build a FeatureItem from a pipeline dict, mapping alternate key names."""
    return FeatureItem(
        rank=f.get("rank", idx + 1),
        title=f.get("title") or f.get("feature_title") or f.get("feature_summary", ""),
        description=f.get("description") or f.get("feature_summary") or f.get("feature_text", ""),
        category=f.get("category"),
        confidence_score=f.get("confidence_score") or f.get("confidence"),
        impact_assessment=f.get("impact_assessment"),
        source_url=f.get("source_url") or f.get("primary_url") or f.get("url"),
        source_count=f.get("source_count"),
        key_metrics=f.get("key_metrics") or f.get("metrics"),
    )


def safe_feature_dict(f: dict, idx: int) -> dict:
    return safe_feature(f, idx).model_dump()


class AgentResponse(BaseModel):
    company_name: str
    generated_at: str
    executive_summary: str
    features: List[FeatureItem] = []
    total_sources_analysed: int = 0
    total_features_verified: int = 0
    all_sources: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


class ReadinessResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    checks: Dict[str, str]


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
