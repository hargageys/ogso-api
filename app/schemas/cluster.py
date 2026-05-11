from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class ClusterOut(BaseModel):
    id: int
    label: str | None
    top_terms: list[str] | None
    paper_count: int
    total_citations: int
    somali_author_ratio: float
    recent_count: int
    gap_score: int
    decade_trend: dict | None
    last_computed: datetime | None

    model_config = {"from_attributes": True}
