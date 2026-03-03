import uuid
import json
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from db.session import get_db
from models.models import ResearchPaper
from schemas.schemas import PaperOut, PaperDetail
from services.pdf_parser import extract_text_from_pdf, detect_sections, infer_title
from config import settings

router = APIRouter()


@router.post("/upload", response_model=PaperOut, status_code=201)
async def upload_paper(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a PDF research paper. Extracts text and detects sections."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_file_size_mb}MB limit.")

    paper_id = str(uuid.uuid4())
    save_path = Path(settings.upload_dir) / f"{paper_id}.pdf"
    save_path.write_bytes(content)

    try:
        raw_text, page_count = extract_text_from_pdf(str(save_path))
        sections = detect_sections(raw_text)
        title = infer_title(raw_text)
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"PDF parsing failed: {str(e)}")

    paper = ResearchPaper(
        paper_id=paper_id,
        title=title,
        filename=file.filename,
        file_path=str(save_path),
        raw_text=raw_text,
        sections_json=json.dumps(sections),
        page_count=page_count,
        status="uploaded",
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


@router.get("", response_model=List[PaperOut])
def list_papers(db: Session = Depends(get_db)):
    """List all uploaded papers."""
    return db.query(ResearchPaper).order_by(ResearchPaper.uploaded_at.desc()).all()


@router.get("/{paper_id}", response_model=PaperDetail)
def get_paper(paper_id: str, db: Session = Depends(get_db)):
    """Get paper metadata and parsed sections."""
    paper = db.query(ResearchPaper).filter(ResearchPaper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    detail = PaperDetail.model_validate(paper)
    if paper.sections_json:
        detail.sections = json.loads(paper.sections_json)
    return detail


@router.delete("/{paper_id}", status_code=204)
def delete_paper(paper_id: str, db: Session = Depends(get_db)):
    """Delete a paper and all associated data."""
    paper = db.query(ResearchPaper).filter(ResearchPaper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    Path(paper.file_path).unlink(missing_ok=True)
    db.delete(paper)
    db.commit()
