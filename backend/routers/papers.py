import os
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models.paper import ResearchPaper
from backend.services.pdf_parser import parse_pdf
from backend.config import settings

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("/upload")
async def upload_paper(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")

    # Save file
    unique_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(settings.upload_dir, unique_name)
    content = await file.read()

    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.max_file_size_mb}MB limit.")

    with open(file_path, "wb") as f:
        f.write(content)

    # Parse PDF
    try:
        parsed = await parse_pdf(file_path)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(500, f"PDF parsing failed: {str(e)}")

    # Store in DB
    paper = ResearchPaper(
        title=parsed["title"],
        filename=file.filename,
        file_path=file_path,
        extracted_text=parsed["extracted_text"],
        sections=parsed["sections"],
        page_count=parsed["page_count"],
    )
    db.add(paper)
    await db.commit()
    await db.refresh(paper)

    return {
        "paper_id": paper.paper_id,
        "title": paper.title,
        "filename": paper.filename,
        "page_count": paper.page_count,
        "status": "success",
        "message": "Paper uploaded and parsed successfully.",
    }


@router.get("/")
async def list_papers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ResearchPaper).order_by(ResearchPaper.uploaded_at.desc()))
    papers = result.scalars().all()
    return [
        {
            "paper_id": p.paper_id,
            "title": p.title,
            "filename": p.filename,
            "page_count": p.page_count,
            "uploaded_at": p.uploaded_at,
            "status": p.status or "uploaded",
        }
        for p in papers
    ]


@router.get("/{paper_id}")
async def get_paper(paper_id: int, db: AsyncSession = Depends(get_db)):
    paper = await db.get(ResearchPaper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found.")
    return {
        "paper_id": paper.paper_id,
        "title": paper.title,
        "filename": paper.filename,
        "page_count": paper.page_count,
        "uploaded_at": paper.uploaded_at,
        "status": paper.status or "uploaded",
    }


@router.delete("/{paper_id}")
async def delete_paper(paper_id: int, db: AsyncSession = Depends(get_db)):
    paper = await db.get(ResearchPaper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found.")
    if os.path.exists(paper.file_path):
        os.remove(paper.file_path)
    await db.delete(paper)
    await db.commit()
    return {"status": "deleted", "paper_id": paper_id}
