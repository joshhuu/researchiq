from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from backend.database import get_db
from backend.models.paper import ResearchPaper
from backend.models.summary import Summary
from backend.services.gap_detector import compare_papers

router = APIRouter(prefix="/papers", tags=["compare"])


class CompareRequest(BaseModel):
    paper_ids: list[int]


@router.post("/compare")
async def compare(req: CompareRequest, db: AsyncSession = Depends(get_db)):
    if len(req.paper_ids) < 2:
        raise HTTPException(400, "Provide at least 2 paper IDs to compare.")

    summaries = []
    for pid in req.paper_ids:
        paper = await db.get(ResearchPaper, pid)
        if not paper:
            raise HTTPException(404, f"Paper {pid} not found.")
        result = await db.execute(select(Summary).where(Summary.paper_id == pid))
        summary = result.scalar_one_or_none()
        if not summary:
            raise HTTPException(400, f"Paper {pid} has no summary yet. Call /papers/{pid}/summary first.")
        summaries.append({
            "paper_id": pid,
            "title": paper.title or "Untitled",
            "full_summary": summary.full_summary or "",
        })

    try:
        comparison = await compare_papers(summaries)
    except Exception as e:
        raise HTTPException(500, f"Comparison failed: {str(e)}")

    return {"status": "success", "paper_ids": req.paper_ids, "data": comparison}
