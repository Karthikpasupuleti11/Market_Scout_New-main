from app.api_models import FeatureItem

def _safe_feature(f: dict, idx: int) -> FeatureItem:
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
