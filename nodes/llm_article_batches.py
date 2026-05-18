"""
Shared helpers for batched article LLM calls — fewer round-trips vs one call per article.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def chunk_list(items: List[T], size: int) -> List[List[T]]:
    if size <= 0:
        size = 1
    return [items[i : i + size] for i in range(0, len(items), size)]


def strip_markdown_fences(raw: str) -> str:
    return re.sub(r"```json\s?|\s?```", "", (raw or "").strip())


def parse_json_array(raw: str) -> List[Any]:
    cleaned = strip_markdown_fences(raw)
    start = cleaned.find("[")
    end = cleaned.rfind("]") + 1
    if start == -1 or end <= start:
        raise ValueError("No JSON array in model output")
    return json.loads(cleaned[start:end])


def parse_json_object(raw: str) -> Dict[str, Any]:
    cleaned = strip_markdown_fences(raw)
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end <= start:
        raise ValueError("No JSON object in model output")
    return json.loads(cleaned[start:end])
