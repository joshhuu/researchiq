"""
chat.py — POST /papers/{id}/chat
Answers questions about a specific paper using Gemini grounded on paper content.
Supports multi-turn conversation via history passed by the client.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.paper import ResearchPaper
from backend.services.chat_service import answer_question

router = APIRouter(prefix="/papers", tags=["chat"])


class HistoryMessage(BaseModel):
    role: str          # "user" or "model"
    parts: List[str]   # single-element list with the message text


class ChatRequest(BaseModel):
    question: str
    history: Optional[List[HistoryMessage]] = []


@router.post("/{paper_id}/chat")
async def chat(
    paper_id: int,
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    paper = await db.get(ResearchPaper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found.")
    if not paper.extracted_text:
        raise HTTPException(400, "Paper has no extracted text. Upload and parse it first.")
    if not req.question.strip():
        raise HTTPException(400, "Question must not be empty.")

    # Convert Pydantic models to plain dicts for the service
    history = [{"role": m.role, "parts": m.parts} for m in (req.history or [])]

    result = await answer_question(
        paper_text=paper.extracted_text,
        question=req.question.strip(),
        history=history,
    )
    return {
        "paper_id": paper_id,
        "question": req.question,
        **result,
    }
