import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models.paper import ResearchPaper
from backend.models.topic import Topic, Gap
from backend.services.topic_classifier import classify_topics
from backend.services.gap_detector import detect_gaps

router = APIRouter(prefix="/papers", tags=["topics"])


@router.get("/{paper_id}/topics")
async def get_topics(paper_id: int, db: AsyncSession = Depends(get_db)):
    paper = await db.get(ResearchPaper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found.")

    result = await db.execute(select(Topic).where(Topic.paper_id == paper_id))
    existing = result.scalars().all()
    if existing:
        return {
            "paper_id": paper_id, "status": "success", "cached": True,
            "data": [{"domain": t.domain, "sub_domain": t.sub_domain, "confidence": t.confidence} for t in existing],
        }

    sections = json.loads(paper.sections or "{}")
    abstract = sections.get("abstract", paper.extracted_text[:1500] if paper.extracted_text else "")
    text_for_classification = f"{paper.title or ''}\n\n{abstract}"
    try:
        items = await classify_topics(text_for_classification)
    except Exception as e:
        raise HTTPException(500, f"Topic classification failed: {str(e)}")

    for item in items:
        db.add(Topic(paper_id=paper_id, domain=item.get("domain", ""), sub_domain=item.get("sub_domain"), confidence=item.get("confidence")))
    await db.commit()

    return {"paper_id": paper_id, "status": "success", "cached": False, "data": items}


@router.get("/{paper_id}/gaps")
async def get_gaps(paper_id: int, db: AsyncSession = Depends(get_db)):
    paper = await db.get(ResearchPaper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found.")

    result = await db.execute(select(Gap).where(Gap.paper_id == paper_id))
    existing = result.scalars().all()
    if existing:
        return {
            "paper_id": paper_id, "status": "success", "cached": True,
            "data": [{"gap_text": g.gap_text, "priority": g.priority} for g in existing],
        }

    sections = json.loads(paper.sections or "{}")
    results_text = sections.get("results", "")
    conclusion_text = sections.get("conclusion", "")
    try:
        items = await detect_gaps(results_text, conclusion_text)
    except Exception as e:
        raise HTTPException(500, f"Gap detection failed: {str(e)}")

    for item in items:
        db.add(Gap(paper_id=paper_id, gap_text=item.get("gap_text", ""), priority=item.get("priority")))
    await db.commit()

    return {"paper_id": paper_id, "status": "success", "cached": False, "data": items}
