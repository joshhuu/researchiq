"""
trend_analyzer.py
Compares multiple papers to identify trends, gaps, and similarities.
"""
import json
from google import genai
from typing import List, Dict
from backend.config import settings


_client = genai.Client(api_key=settings.gemini_api_key)


COMPARE_PROMPT = """You are a senior research analyst conducting a literature review.
You have been given summaries and key insights from {n} research papers.

{papers_text}

Analyze these papers together and respond ONLY with a valid JSON object (no markdown, no preamble):
{{
  "trends": [
    "Common trend or theme observed across papers (list 3–5 items)"
  ],
  "gaps": [
    "Research gap or open problem identified (list 3–5 items)"
  ],
  "similarities": [
    "Key similarity between papers (list 3–5 items)"
  ],
  "differences": [
    "Key difference in approach or scope (list 2–4 items)"
  ]
}}"""


def analyze_trends(papers: List[Dict]) -> Dict:
    """
    papers: list of dicts with keys: title, full_summary, keywords (list of strings)
    Returns dict with trends, gaps, similarities, differences.
    """
    papers_text_parts = []
    for i, paper in enumerate(papers, 1):
        keywords_str = ", ".join(paper.get("keywords", [])[:15])
        papers_text_parts.append(
            f"PAPER {i}: {paper.get('title', 'Unknown')}\n"
            f"Summary: {paper.get('full_summary', '')[:1000]}\n"
            f"Key terms: {keywords_str}"
        )

    papers_text = "\n\n---\n\n".join(papers_text_parts)
    prompt = COMPARE_PROMPT.format(n=len(papers), papers_text=papers_text[:10000])

    response = _client.models.generate_content(model=settings.gemini_model, contents=prompt)
    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)
