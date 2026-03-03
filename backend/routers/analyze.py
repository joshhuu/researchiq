"""
analyze.py
Unified endpoint: runs summary + insights + topics + gaps in one call.
GET  /papers/{id}/analyze  — fetch cached results
POST /papers/{id}/analyze  — run (or re-run) full analysis
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.paper import ResearchPaper
from backend.models.summary import Summary
from backend.models.insight import Insight
from backend.models.topic import Topic, Gap
from backend.services.summarizer import generate_summary
from backend.services.insight_extractor import extract_insights
from backend.services.topic_classifier import classify_topics
from backend.services.gap_detector import detect_gaps

router = APIRouter(prefix="/papers", tags=["analyze"])


def _build_response(paper_id, summaries_row, insights_rows, topics_rows, gaps_rows, cached: bool):
    summaries = []
    if summaries_row:
        mapping = {
            "full": summaries_row.full_summary,
            "abstract": summaries_row.abstract_sum,
            "introduction": summaries_row.intro_sum,
            "methodology": summaries_row.method_sum,
            "results": summaries_row.results_sum,
            "conclusion": summaries_row.conclusion_sum,
        }
        for stype, stext in mapping.items():
            if stext:
                summaries.append({"summary_type": stype, "summary_text": stext})

    insights = [
        {
            "keyword": i.keyword,
            "category": i.category,
            "relevance_score": i.score or 0.0,
            "context": "",
        }
        for i in insights_rows
    ]

    topics = [
        {"domain": t.domain, "sub_domain": t.sub_domain, "confidence": t.confidence or 0.0}
        for t in topics_rows
    ]

    gaps = [
        {"gap_text": g.gap_text, "priority": g.priority}
        for g in gaps_rows
    ]

    return {
        "paper_id": paper_id,
        "status": "success",
        "cached": cached,
        "summaries": summaries,
        "insights": insights,
        "topics": topics,
        "gaps": gaps,
    }


@router.get("/{paper_id}/analyze")
async def get_analysis(paper_id: int, db: AsyncSession = Depends(get_db)):
    """Return cached analysis results for a paper."""
    paper = await db.get(ResearchPaper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found.")

    summary_row = (await db.execute(select(Summary).where(Summary.paper_id == paper_id))).scalar_one_or_none()
    insights_rows = (await db.execute(select(Insight).where(Insight.paper_id == paper_id))).scalars().all()
    topics_rows = (await db.execute(select(Topic).where(Topic.paper_id == paper_id))).scalars().all()
    gaps_rows = (await db.execute(select(Gap).where(Gap.paper_id == paper_id))).scalars().all()

    if not summary_row and not insights_rows:
        raise HTTPException(404, "No analysis found. Run POST /papers/{id}/analyze first.")

    return _build_response(paper_id, summary_row, insights_rows, topics_rows, gaps_rows, cached=True)


@router.post("/{paper_id}/analyze")
async def run_analysis(
    paper_id: int,
    n_sentences: int = 3,
    db: AsyncSession = Depends(get_db),
):
    """Run full AI analysis: summary + insights + topics + gaps. Overwrites any cached results.
    
    Query params:
      n_sentences (int, default 3): sentences per section in the summary (1–10).
    """
    n_sentences = max(1, min(10, n_sentences))  # clamp to valid range
    paper = await db.get(ResearchPaper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found.")

    sections = json.loads(paper.sections or "{}")
    raw_text = paper.extracted_text or ""

    # ── 1. Summary ─────────────────────────────────────────────────────────────
    try:
        summary_data = await generate_summary(sections, n_sentences_override=n_sentences)
    except Exception as e:
        raise HTTPException(500, f"Summarization failed: {e}")

    # Delete old summary if exists
    old = (await db.execute(select(Summary).where(Summary.paper_id == paper_id))).scalar_one_or_none()
    if old:
        await db.delete(old)

    summary_row = Summary(
        paper_id=paper_id,
        full_summary=summary_data.get("full_summary"),
        abstract_sum=summary_data.get("abstract_sum"),
        intro_sum=summary_data.get("intro_sum"),
        method_sum=summary_data.get("method_sum"),
        results_sum=summary_data.get("results_sum"),
        conclusion_sum=summary_data.get("conclusion_sum"),
    )
    db.add(summary_row)

    # ── 2. Insights ────────────────────────────────────────────────────────────
    try:
        insight_items = await extract_insights(raw_text)
    except Exception as e:
        insight_items = []

    old_insights = (await db.execute(select(Insight).where(Insight.paper_id == paper_id))).scalars().all()
    for old_i in old_insights:
        await db.delete(old_i)

    insight_rows = []
    for item in insight_items:
        row = Insight(
            paper_id=paper_id,
            keyword=item.get("keyword", ""),
            category=item.get("category", "concept"),
            score=item.get("relevance_score", item.get("score")),
        )
        db.add(row)
        insight_rows.append(row)

    # ── 3. Topics ──────────────────────────────────────────────────────────────
    abstract = sections.get("abstract", raw_text[:1500])
    text_for_classification = f"{paper.title or ''}\n\n{abstract}"
    try:
        topic_items = await classify_topics(text_for_classification)
    except Exception as e:
        topic_items = []

    old_topics = (await db.execute(select(Topic).where(Topic.paper_id == paper_id))).scalars().all()
    for old_t in old_topics:
        await db.delete(old_t)

    topic_rows = []
    for item in topic_items:
        row = Topic(
            paper_id=paper_id,
            domain=item.get("domain", ""),
            sub_domain=item.get("sub_domain"),
            confidence=item.get("confidence"),
        )
        db.add(row)
        topic_rows.append(row)

    # ── 4. Gaps ────────────────────────────────────────────────────────────────
    results_text = sections.get("results", "")
    conclusion_text = sections.get("conclusion", "")
    try:
        gap_items = await detect_gaps(results_text, conclusion_text)
    except Exception as e:
        gap_items = []

    old_gaps = (await db.execute(select(Gap).where(Gap.paper_id == paper_id))).scalars().all()
    for old_g in old_gaps:
        await db.delete(old_g)

    gap_rows = []
    for item in gap_items:
        row = Gap(
            paper_id=paper_id,
            gap_text=item.get("gap_text", ""),
            priority=item.get("priority"),
        )
        db.add(row)
        gap_rows.append(row)

    # ── Save & update status ───────────────────────────────────────────────────
    paper.status = "analyzed"
    await db.commit()
    await db.refresh(summary_row)

    return _build_response(paper_id, summary_row, insight_rows, topic_rows, gap_rows, cached=False)
