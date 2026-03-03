from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── Paper schemas ──────────────────────────────────────────────────────────────

class PaperOut(BaseModel):
    paper_id: str
    title: Optional[str]
    filename: str
    page_count: int
    uploaded_at: datetime
    status: str

    class Config:
        from_attributes = True


class PaperDetail(PaperOut):
    sections: Optional[Dict[str, str]] = None   # parsed from sections_json


# ── Summary schemas ────────────────────────────────────────────────────────────

class SummaryOut(BaseModel):
    summary_id: str
    summary_type: str
    summary_text: str

    class Config:
        from_attributes = True


# ── Insight schemas ────────────────────────────────────────────────────────────

class InsightOut(BaseModel):
    insight_id: str
    keyword: str
    category: str
    relevance_score: float
    context: Optional[str]

    class Config:
        from_attributes = True


# ── Topic schemas ──────────────────────────────────────────────────────────────

class TopicOut(BaseModel):
    topic_id: str
    domain: str
    sub_domain: Optional[str]
    confidence: float

    class Config:
        from_attributes = True


# ── Full analysis response ─────────────────────────────────────────────────────

class AnalysisResult(BaseModel):
    paper_id: str
    status: str
    summaries: List[SummaryOut]
    insights: List[InsightOut]
    topics: List[TopicOut]


# ── Comparison schemas ─────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    paper_ids: List[str]


class CompareResult(BaseModel):
    comparison_id: str
    paper_ids: List[str]
    gaps: Optional[List[str]]
    trends: Optional[List[str]]
    similarities: Optional[List[str]]
