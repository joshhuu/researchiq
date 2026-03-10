"""
trends.py — POST /papers/trends
Cross-paper trend analysis using sentence-transformers + TF-IDF.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.paper import ResearchPaper
from backend.models.summary import Summary
from backend.models.insight import Insight
from backend.services.trend_analyzer import analyze_trends

router = APIRouter(prefix="/papers", tags=["trends"])


class TrendsRequest(BaseModel):
    paper_ids: list[int]


@router.post("/trends")
async def get_trends(req: TrendsRequest, db: AsyncSession = Depends(get_db)):
    if len(req.paper_ids) < 2:
        raise HTTPException(400, "Provide at least 2 paper IDs for trend analysis.")

    papers_data = []
    for pid in req.paper_ids:
        paper = await db.get(ResearchPaper, pid)
        if not paper:
            raise HTTPException(404, f"Paper {pid} not found.")

        # Get full_summary from DB if available
        summary_row = (
            await db.execute(select(Summary).where(Summary.paper_id == pid))
        ).scalar_one_or_none()
        full_summary = summary_row.full_summary if summary_row else (paper.extracted_text or "")[:1000]

        # Get top keywords from DB
        insight_rows = (
            await db.execute(select(Insight).where(Insight.paper_id == pid))
        ).scalars().all()
        keywords = [i.keyword for i in sorted(insight_rows, key=lambda x: -(x.score or 0))[:15]]

        papers_data.append({
            "paper_id": pid,
            "title": paper.title or paper.filename,
            "full_summary": full_summary,
            "keywords": keywords,
        })

    try:
        result = analyze_trends(papers_data)
    except Exception as e:
        raise HTTPException(500, f"Trend analysis failed: {str(e)}")

    return {
        "status": "success",
        "paper_ids": req.paper_ids,
        "data": result,
    }
