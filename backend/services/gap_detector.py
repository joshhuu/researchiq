import json
from google import genai
from backend.config import settings
from backend.utils.prompt_templates import detect_gaps_prompt, compare_papers_prompt

_client = genai.Client(api_key=settings.gemini_api_key)


async def detect_gaps(results: str, conclusion: str) -> list:
    """Returns list of gap dicts: {gap_text, priority}."""
    prompt = detect_gaps_prompt(results, conclusion)
    response = _client.models.generate_content(model=settings.gemini_model, contents=prompt)
    raw = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


async def compare_papers(summaries: list) -> dict:
    """Returns comparison analysis dict."""
    prompt = compare_papers_prompt(summaries)
    response = _client.models.generate_content(model=settings.gemini_model, contents=prompt)
    raw = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)
