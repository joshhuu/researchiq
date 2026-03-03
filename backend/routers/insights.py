from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models.paper import ResearchPaper
from backend.models.insight import Insight
from backend.services.insight_extractor import extract_insights

router = APIRouter(prefix="/papers", tags=["insights"])


@router.get("/{paper_id}/insights")
async def get_insights(paper_id: int, db: AsyncSession = Depends(get_db)):
    paper = await db.get(ResearchPaper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found.")

    result = await db.execute(select(Insight).where(Insight.paper_id == paper_id))
    existing = result.scalars().all()
    if existing:
        return {
            "paper_id": paper_id,
            "status": "success",
            "cached": True,
            "data": [{"keyword": i.keyword, "category": i.category, "score": i.score} for i in existing],
        }

    try:
        items = await extract_insights(paper.extracted_text or "")
    except Exception as e:
        raise HTTPException(500, f"Insight extraction failed: {str(e)}")

    for item in items:
        db.add(Insight(
            paper_id=paper_id,
            keyword=item.get("keyword", ""),
            category=item.get("category", "keyword"),
            score=item.get("relevance_score", item.get("score")),
        ))
    await db.commit()

    return {"paper_id": paper_id, "status": "success", "cached": False, "data": items}
