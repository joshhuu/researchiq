"""
chat_service.py
Conversational Q&A about a research paper — powered by Gemini, grounded on paper content.

Pipeline:
  1. RETRIEVE  — sentence-transformers semantic search finds the most relevant
                 chunks from the paper for the current question
  2. GROUND    — retrieved chunks are injected into Gemini's context as the
                 ONLY allowed knowledge source (the model is explicitly told
                 not to use outside knowledge)
  3. RESPOND   — Gemini generates a fluent, paper-grounded answer
  4. FALLBACK  — if GEMINI_API_KEY is not set, return the raw retrieved passages
                 so the feature still works without an API key
"""
import asyncio
from typing import List, Tuple, Optional

import numpy as np
from sentence_transformers import SentenceTransformer, util

from backend.config import settings

# ── Lazy singleton ─────────────────────────────────────────────────────────────
_st_model: Optional[SentenceTransformer] = None


def _get_st_model() -> SentenceTransformer:
    global _st_model
    if _st_model is None:
        _st_model = SentenceTransformer(settings.sentence_transformer_model)
    return _st_model


# ── Text chunking ──────────────────────────────────────────────────────────────
def _chunk_text(text: str, chunk_size: int = 250, overlap: int = 40) -> List[str]:
    """Split text into overlapping word-level chunks for retrieval."""
    words = text.split()
    chunks, step = [], chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i: i + chunk_size]).strip()
        if len(chunk) > 30:
            chunks.append(chunk)
    return chunks


# ── Semantic retrieval ─────────────────────────────────────────────────────────
def _retrieve(question: str, text: str, top_k: int = 5) -> List[Tuple[float, str]]:
    """Return top-K (score, chunk) pairs most relevant to the question."""
    model = _get_st_model()
    chunks = _chunk_text(text)
    if not chunks:
        return []

    q_emb  = model.encode(question, convert_to_tensor=True)
    c_embs = model.encode(chunks,   convert_to_tensor=True)
    scores = util.cos_sim(q_emb, c_embs)[0].cpu().numpy()

    top_idx = np.argsort(scores)[::-1][:top_k]
    return [(float(scores[i]), chunks[i]) for i in top_idx if scores[i] > 0.10]


# ── Gemini grounded answer ─────────────────────────────────────────────────────
_SYSTEM_PROMPT = """\
You are a helpful research paper assistant. Your job is to answer questions about \
the research paper whose relevant excerpts are provided below as CONTEXT.

STRICT RULES you must follow:
1. Base your answers ONLY on the CONTEXT provided. Do not use any outside knowledge.
2. If the answer is not in the CONTEXT, say clearly: \
   "This information is not covered in the provided paper."
3. Quote or paraphrase specific parts of the CONTEXT to support your answer.
4. Keep answers clear, concise, and academic in tone.
5. If asked to summarise or explain a concept from the paper, do so in plain language.\
"""


def _gemini_answer(
    question: str,
    context: str,
    history: List[dict],  # [{"role": "user"|"model", "parts": [str]}, ...]
) -> str:
    """Call Gemini with retrieved context + conversation history."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)

    # Inject system prompt + context directly into the user turn so it works
    # with both Gemini models (support system_instruction) and Gemma models
    # (system_instruction is not supported).
    grounded_question = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"CONTEXT FROM THE PAPER:\n"
        f"{'=' * 60}\n"
        f"{context}\n"
        f"{'=' * 60}\n\n"
        f"QUESTION: {question}"
    )

    # Rebuild conversation with grounded question replacing the last user turn
    contents = []
    for msg in history:
        contents.append(
            types.Content(role=msg["role"], parts=[types.Part(text=msg["parts"][0])])
        )
    contents.append(
        types.Content(role="user", parts=[types.Part(text=grounded_question)])
    )

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.2,        # low temperature = more faithful to context
            max_output_tokens=1024,
        ),
    )
    return response.text.strip()


# ── Fallback: formatted passages ───────────────────────────────────────────────
def _format_passages(chunks: List[Tuple[float, str]]) -> str:
    if not chunks:
        return "I could not find relevant content in this paper to answer your question."
    lines = ["Here are the most relevant passages from the paper:\n"]
    for rank, (score, chunk) in enumerate(chunks, 1):
        lines.append(f"**Passage {rank}** _(relevance: {score:.0%})_")
        lines.append(f"> {chunk}\n")
    return "\n".join(lines)


# ── Public async API ───────────────────────────────────────────────────────────
async def answer_question(
    paper_text: str,
    question: str,
    history: Optional[List[dict]] = None,
) -> dict:
    """
    Answer a question about a paper, grounded on its content.

    Args:
        paper_text: full extracted text of the paper
        question:   user's question
        history:    previous turns as list of
                    {"role": "user"|"model", "parts": ["text"]}

    Returns:
        {"answer": str, "source": "gemini" | "local"}
    """
    history = history or []

    # 1. Retrieve relevant chunks
    chunks = await asyncio.to_thread(_retrieve, question, paper_text)
    context = "\n\n---\n\n".join(chunk for _, chunk in chunks)

    # 2. Try Gemini (primary)
    if settings.gemini_api_key:
        try:
            answer = await asyncio.to_thread(
                _gemini_answer, question, context, history
            )
            return {"answer": answer, "source": "gemini"}
        except Exception as e:
            # Log and fall through to local fallback
            import logging
            logging.getLogger(__name__).warning(f"Gemini chat failed: {e}")

    # 3. Fallback: return raw passages
    return {"answer": _format_passages(chunks), "source": "local"}

