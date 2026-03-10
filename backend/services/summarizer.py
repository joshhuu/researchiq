"""
summarizer.py
Extractive text summarization using spaCy sentence tokenization + TF-IDF sentence scoring.
No external API calls — runs entirely offline.
"""
import asyncio
from typing import Dict, Optional, List

import numpy as np
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer

# Lazy-loaded model — loaded once on first use
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


# Section aliases: canonical_name → (result_key, list of partial-match aliases)
_SECTION_MAP = {
    "abstract":     ("abstract_sum",  ["abstract"]),
    "introduction": ("intro_sum",     ["introduction", "intro", "background"]),
    "methodology":  ("method_sum",    ["methodology", "methods", "method", "approach", "proposed"]),
    "results":      ("results_sum",   ["results", "experiments", "findings", "evaluation", "experiment"]),
    "conclusion":   ("conclusion_sum",["conclusion", "conclusions", "concluding", "summary"]),
}

# How many sentences to extract per section type
_SECTION_N_SENTS = {
    "abstract": 3,
    "introduction": 3,
    "methodology": 4,
    "results": 4,
    "conclusion": 3,
}


def _tfidf_extractive_summary(text: str, n_sentences: int = 5, max_chars: int = 12_000) -> str:
    """
    Rank sentences by TF-IDF importance and return the top-N in original order.
    Falls back gracefully if spaCy or sklearn fail.
    """
    text = text[:max_chars]
    nlp = _get_nlp()
    doc = nlp(text)
    sentences = [s.text.strip() for s in doc.sents if len(s.text.strip()) > 30]

    if not sentences:
        return text[:400]
    if len(sentences) <= n_sentences:
        return " ".join(sentences)

    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
        tfidf = vectorizer.fit_transform(sentences)
        scores = np.asarray(tfidf.sum(axis=1)).flatten()
        top_idx = sorted(np.argsort(scores)[-n_sentences:])
        return " ".join(sentences[i] for i in top_idx)
    except Exception:
        return " ".join(sentences[:n_sentences])


def _summarize_section(canon_name: str, text: str) -> Optional[str]:
    if not text or not text.strip():
        return None
    n = _SECTION_N_SENTS.get(canon_name, 3)
    return _tfidf_extractive_summary(text, n_sentences=n)


def _find_section_text(key_aliases: List[str], sections: Dict[str, str]) -> str:
    """Return the first section value whose key contains any alias string."""
    for alias in key_aliases:
        for sec_key, sec_text in sections.items():
            if alias in sec_key.lower() and sec_text:
                return sec_text
    return ""


async def generate_summary(
    sections: Dict[str, str],
    n_sentences_override: Optional[int] = None,
) -> Dict[str, Optional[str]]:
    """
    Generate structured extractive summaries for each paper section.

    Returns dict with keys:
        full_summary, abstract_sum, intro_sum, method_sum, results_sum, conclusion_sum
    """
    result: Dict[str, Optional[str]] = {
        "abstract_sum":  None,
        "intro_sum":     None,
        "method_sum":    None,
        "results_sum":   None,
        "conclusion_sum": None,
    }

    for canon_name, (key, aliases) in _SECTION_MAP.items():
        text = _find_section_text(aliases, sections)
        if text:
            n = n_sentences_override or _SECTION_N_SENTS.get(canon_name, 3)
            summary = await asyncio.to_thread(_tfidf_extractive_summary, text, n)
            result[key] = summary

    # Full-paper summary: combine all non-empty sections and extract top sentences
    all_text = "\n\n".join(v for v in sections.values() if v)
    full_n = (n_sentences_override or 4) * 2   # full summary is always twice as long
    result["full_summary"] = await asyncio.to_thread(
        _tfidf_extractive_summary, all_text, full_n, 20_000
    )
    return result
