from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

# ────────────────────────────────────────────────────────────────────
# Request / Response Schemas
# ────────────────────────────────────────────────────────────────────

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
    session_id: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Client-generated session id used to isolate RAG indexes per device/browser",
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