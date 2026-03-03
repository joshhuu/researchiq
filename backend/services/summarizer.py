"""
summarizer.py
Generates section-wise and full summaries using Google Gemini API.
"""
import json
import asyncio
from google import genai
from typing import Dict, List
from backend.config import settings


_client = genai.Client(api_key=settings.gemini_api_key)


SUMMARY_PROMPT = """You are an expert research analyst. Given the following section of a research paper, 
generate a concise, accurate summary. Capture the core ideas, key findings, and important details.

Section type: {section_type}
Section content:
{content}

Respond ONLY with a JSON object in this exact format (no markdown, no preamble):
{{
  "summary": "<2-4 sentence summary of this section>"
}}"""


FULL_SUMMARY_PROMPT = """You are an expert research analyst. Given the following research paper sections, 
generate a comprehensive but concise overall summary of the entire paper.

Paper sections:
{sections_text}

Respond ONLY with a JSON object (no markdown, no preamble):
{{
  "summary": "<4-6 sentence overall summary covering objectives, methods, findings, and significance>"
}}"""


def summarize_section(section_type: str, content: str) -> str:
    """Summarize a single section. Returns summary string."""
    # Truncate very long sections to stay within token limits
    content = content[:6000]
    prompt = SUMMARY_PROMPT.format(section_type=section_type, content=content)
    response = _client.models.generate_content(model=settings.gemini_model, contents=prompt)
    raw = response.text.strip()
    data = json.loads(raw)
    return data["summary"]


def summarize_all_sections(sections: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Generate summaries for each section + one full summary.
    Returns list of dicts: [{"type": "abstract", "text": "..."}, ...]
    """
    results = []

    # Section-wise summaries (skip references)
    skip = {"references", "bibliography", "preamble"}
    for section_type, content in sections.items():
        if section_type in skip or not content.strip():
            continue
        summary_text = summarize_section(section_type, content)
        results.append({"type": section_type, "text": summary_text})

    # Full paper summary
    sections_text = "\n\n".join(
        f"[{k.upper()}]\n{v[:2000]}" for k, v in sections.items() if k not in skip
    )
    full_prompt = FULL_SUMMARY_PROMPT.format(sections_text=sections_text[:8000])
    response = _client.models.generate_content(model=settings.gemini_model, contents=full_prompt)
    raw = response.text.strip()
    data = json.loads(raw)
    results.append({"type": "full", "text": data["summary"]})

    return results


STRUCTURED_SUMMARY_PROMPT = """You are a research paper analyst. Analyze the following research paper sections and produce a structured summary.

{sections_text}

Return ONLY a valid JSON object with these exact keys:
{{
  "full_summary": "2-3 paragraph overall summary of the paper",
  "abstract_sum": "1-2 sentence summary of the abstract (or null if not present)",
  "intro_sum": "1-2 sentence summary of the introduction (or null)",
  "method_sum": "1-2 sentence summary of methodology (or null)",
  "results_sum": "1-2 sentence summary of results (or null)",
  "conclusion_sum": "1-2 sentence summary of conclusion (or null)"
}}

Be concise. Output only the JSON, no preamble or markdown."""


async def generate_summary(sections: Dict[str, str]) -> Dict[str, str]:
    """
    Generate a structured summary dict for all sections.
    Returns keys: full_summary, abstract_sum, intro_sum, method_sum, results_sum, conclusion_sum.
    """
    sections_text = "\n\n".join(
        f"=== {k.upper()} ===\n{v[:3000]}" for k, v in sections.items() if v
    )
    prompt = STRUCTURED_SUMMARY_PROMPT.format(sections_text=sections_text[:10000])
    response = await asyncio.to_thread(
        _client.models.generate_content, model=settings.gemini_model, contents=prompt
    )
    raw = response.text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    return json.loads(raw)
