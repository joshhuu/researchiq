"""
topic_classifier.py
Classifies a research paper into domain and sub-domain using Gemini.
"""
import json
import asyncio
from google import genai
from typing import List, Dict
from backend.config import settings


_client = genai.Client(api_key=settings.gemini_api_key)


CLASSIFIER_PROMPT = """You are an expert research librarian. Classify the following research paper 
into academic domains and sub-domains.

Paper text (truncated):
{text}

Respond ONLY with a valid JSON array (no markdown, no preamble). 
Provide 1–3 domain classifications, most confident first. Each item:
- "domain": broad academic field (e.g. "Machine Learning", "Bioinformatics", "NLP")  
- "sub_domain": specific area (e.g. "Object Detection", "Gene Expression", "Question Answering")
- "confidence": float 0.0–1.0

Example:
[
  {{"domain": "Machine Learning", "sub_domain": "Natural Language Processing", "confidence": 0.95}},
  {{"domain": "Computer Science", "sub_domain": "Deep Learning", "confidence": 0.80}}
]"""


async def classify_topics(raw_text: str) -> List[Dict]:
    """
    Classify paper into academic domains.
    Returns list of topic dicts with domain, sub_domain, confidence.
    """
    text = raw_text[:6000]
    prompt = CLASSIFIER_PROMPT.format(text=text)

    response = await asyncio.to_thread(
        _client.models.generate_content, model=settings.gemini_model, contents=prompt
    )
    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    topics = json.loads(raw)
    return topics
