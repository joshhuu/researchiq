"""
utils/prompt_templates.py

This module has been converted from LLM prompt templates to plain NLP helpers.
All AI analysis is now performed by:
  • summarizer.py      — spaCy sentence tokenisation + TF-IDF extractive summarisation
  • insight_extractor.py — KeyBERT + YAKE + spaCy NER
  • topic_classifier.py  — sentence-transformers cosine similarity against domain descriptors
  • gap_detector.py      — spaCy sentence detection + sentence-transformers semantic matching
  • trend_analyzer.py    — sentence-transformers + TF-IDF cross-paper analysis

Keeping this file present for import-compatibility; helpers below are utility
functions used by tests or external callers.
"""
from typing import Dict, List


def format_sections_for_display(sections: Dict[str, str]) -> str:
    """Render a sections dict as a human-readable block of text."""
    return "\n\n".join(
        f"=== {k.upper()} ===\n{v[:2000]}"
        for k, v in sections.items()
        if v
    )


def truncate_text(text: str, max_chars: int = 6000) -> str:
    """Safely truncate text to a maximum character count."""
    return text[:max_chars] if text else ""


def build_paper_context(title: str, abstract: str, keywords: List[str]) -> str:
    """Build a compact paper context string for downstream processing."""
    kw_str = ", ".join(keywords[:20]) if keywords else ""
    return f"TITLE: {title}\nABSTRACT: {abstract[:1500]}\nKEYWORDS: {kw_str}"


def summarize_paper_prompt(sections: dict) -> str:
    sections_text = "\n\n".join(
        f"=== {k.upper()} ===\n{v}" for k, v in sections.items() if v
    )
    return f"""You are a research paper analyst. Analyze the following research paper sections and produce a structured summary.

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

Be concise. Output only the JSON, no preamble."""


def extract_insights_prompt(text: str) -> str:
    return f"""You are a research paper analyst. Extract key insights from this research paper text.

TEXT:
{text[:6000]}

Return ONLY a valid JSON array. Each item must have:
{{"keyword": "the term or phrase", "category": "one of: keyword, objective, method, finding", "score": 0.0}}

Extract 10-20 items. Output only the JSON array, no preamble."""


def classify_topics_prompt(title: str, abstract: str) -> str:
    return f"""You are a research classifier. Classify this paper into academic domains.

TITLE: {title}
ABSTRACT: {abstract[:2000]}

Return ONLY a valid JSON array. Each item:
{{"domain": "primary field", "sub_domain": "specific sub-field", "confidence": 0.0}}

List 1-3 domains. Output only the JSON array, no preamble."""


def detect_gaps_prompt(results: str, conclusion: str) -> str:
    return f"""You are a research gap analyst. Identify gaps and future work from results and conclusion.

RESULTS:
{results[:3000]}

CONCLUSION:
{conclusion[:2000]}

Return ONLY a valid JSON array. Each item:
{{"gap_text": "description of gap", "priority": "high|medium|low"}}

List 3-7 gaps. Output only the JSON array, no preamble."""


def compare_papers_prompt(summaries: list) -> str:
    papers_text = "\n\n".join(
        f"PAPER {i+1} (ID:{s['paper_id']}): {s['title']}\n{s['full_summary']}"
        for i, s in enumerate(summaries)
    )
    return f"""You are a research analyst. Compare these papers.

{papers_text}

Return ONLY a valid JSON object:
{{
  "common_themes": ["theme1"],
  "differences": ["diff1"],
  "complementary_aspects": ["aspect1"],
  "recommended_reading_order": [1, 2],
  "comparison_table": [{{"aspect": "Methodology", "papers": {{"1": "desc", "2": "desc"}}}}]
}}

Output only the JSON, no preamble."""
