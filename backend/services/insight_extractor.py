"""
insight_extractor.py
Extracts keywords, methodologies, findings, and tools from a paper.
"""
import json
import asyncio
from google import genai
from typing import List, Dict
from backend.config import settings


_client = genai.Client(api_key=settings.gemini_api_key)


INSIGHT_PROMPT = """You are a research insight extraction expert. Analyze this research paper text 
and extract structured insights.

Paper text (truncated):
{text}

Respond ONLY with a valid JSON array (no markdown, no preamble). Each item must have:
- "keyword": the term or phrase (string)
- "category": one of ["methodology", "finding", "tool", "concept", "dataset", "metric"]
- "relevance_score": float between 0.0 and 1.0 (higher = more important)
- "context": one sentence explaining why this keyword matters in the paper

Extract 10–20 of the most important insights. Example format:
[
  {{
    "keyword": "transformer architecture",
    "category": "methodology",
    "relevance_score": 0.95,
    "context": "The paper proposes a modified transformer architecture as its core contribution."
  }}
]"""


async def extract_insights(raw_text: str) -> List[Dict]:
    """
    Extract keywords, findings, methodologies, tools from paper text.
    Returns list of insight dicts.
    """
    text = raw_text[:8000]  # Trim to fit context
    prompt = INSIGHT_PROMPT.format(text=text)

    response = await asyncio.to_thread(
        _client.models.generate_content, model=settings.gemini_model, contents=prompt
    )
    raw = response.text.strip()

    # Strip any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    insights = json.loads(raw)
    return insights
