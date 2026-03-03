import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models.paper import ResearchPaper
from backend.models.summary import Summary
from backend.services.summarizer import generate_summary

router = APIRouter(prefix="/papers", tags=["summary"])


@router.get("/{paper_id}/summary")
async def get_summary(paper_id: int, db: AsyncSession = Depends(get_db)):
    paper = await db.get(ResearchPaper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found.")

    # Return cached if exists
    result = await db.execute(select(Summary).where(Summary.paper_id == paper_id))
    existing = result.scalar_one_or_none()
    if existing:
        return {
            "paper_id": paper_id,
            "status": "success",
            "cached": True,
            "data": {
                "full_summary": existing.full_summary,
                "abstract_sum": existing.abstract_sum,
                "intro_sum": existing.intro_sum,
                "method_sum": existing.method_sum,
                "results_sum": existing.results_sum,
                "conclusion_sum": existing.conclusion_sum,
            },
        }

    # Generate fresh
    sections = json.loads(paper.sections or "{}")
    try:
        result_data = await generate_summary(sections)
    except Exception as e:
        raise HTTPException(500, f"Summarization failed: {str(e)}")

    summary = Summary(
        paper_id=paper_id,
        full_summary=result_data.get("full_summary"),
        abstract_sum=result_data.get("abstract_sum"),
        intro_sum=result_data.get("intro_sum"),
        method_sum=result_data.get("method_sum"),
        results_sum=result_data.get("results_sum"),
        conclusion_sum=result_data.get("conclusion_sum"),
    )
    db.add(summary)
    paper.status = "analyzed"
    await db.commit()

    return {"paper_id": paper_id, "status": "success", "cached": False, "data": result_data}
