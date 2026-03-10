"""
insight_extractor.py
Extracts keywords, methodologies, findings, and named entities from paper text.

Pipeline:
  1. KeyBERT  — semantic keyphrases using sentence-transformer embeddings
  2. YAKE     — statistical, language-model-free keyword extraction
  3. spaCy NER — named entities (tools, datasets, metrics, organisations)

No external API calls after models are first loaded.
"""
import asyncio
from typing import List, Dict

import spacy
from keybert import KeyBERT
import yake

# ── Lazy singletons ────────────────────────────────────────────────────────────
_nlp = None
_kw_model = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def _get_kw_model():
    global _kw_model
    if _kw_model is None:
        _kw_model = KeyBERT()   # uses all-MiniLM-L6-v2 by default
    return _kw_model


# ── Heuristic category helpers ─────────────────────────────────────────────────
_METHOD_HINTS = [
    "we propose", "we present", "we introduce", "proposed method",
    "our approach", "we use", "we leverage", "algorithm",
    "framework", "architecture", "technique", "pipeline",
]
_FINDING_HINTS = [
    "we show", "we demonstrate", "results show", "outperform",
    "achieve", "accuracy", "performance", "improvement",
    "state-of-the-art", "we observe", "significant",
]
_NER_LABEL_MAP = {
    "ORG":        "tool",
    "PRODUCT":    "tool",
    "WORK_OF_ART":"dataset",
    "PERCENT":    "metric",
    "QUANTITY":   "metric",
    "LAW":        "concept",
    "NORP":       "concept",
}


def _guess_category(keyword: str, text_lower: str) -> str:
    if any(h in text_lower for h in _METHOD_HINTS):
        return "methodology"
    if any(h in text_lower for h in _FINDING_HINTS):
        return "finding"
    return "concept"


# ── Core synchronous extraction ────────────────────────────────────────────────
def _extract_sync(raw_text: str) -> List[Dict]:
    text = raw_text[:8000]
    text_lower = text.lower()
    insights: List[Dict] = []
    seen: set = set()

    # ── 1. KeyBERT: semantic keyphrases ────────────────────────────────────────
    try:
        kw_model = _get_kw_model()
        kws = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),
            stop_words="english",
            use_maxsum=True,
            nr_candidates=25,
            top_n=15,
        )
        for kw, score in kws:
            kw = kw.strip()
            if kw.lower() not in seen and len(kw) > 2:
                seen.add(kw.lower())
                insights.append({
                    "keyword": kw,
                    "category": _guess_category(kw, text_lower),
                    "relevance_score": round(float(score), 3),
                    "context": "Semantically significant keyphrase extracted from paper content.",
                })
    except Exception:
        pass

    # ── 2. YAKE: statistical keyphrases ────────────────────────────────────────
    try:
        extractor = yake.KeywordExtractor(lan="en", n=2, dedupLim=0.7, top=15)
        for kw, score in extractor.extract_keywords(text):
            kw = kw.strip()
            if kw.lower() not in seen and len(kw) > 2:
                seen.add(kw.lower())
                # YAKE: lower score → more relevant; invert to [0,1]
                norm = round(max(0.0, min(1.0, 1.0 - score)), 3)
                insights.append({
                    "keyword": kw,
                    "category": "keyword",
                    "relevance_score": norm,
                    "context": "Statistically frequent and distinctive term in the paper.",
                })
    except Exception:
        pass

    # ── 3. spaCy NER: tools, datasets, metrics ─────────────────────────────────
    try:
        nlp = _get_nlp()
        doc = nlp(text[:5000])
        for ent in doc.ents:
            cat = _NER_LABEL_MAP.get(ent.label_)
            if cat and ent.text.strip().lower() not in seen and len(ent.text.strip()) > 2:
                seen.add(ent.text.strip().lower())
                insights.append({
                    "keyword": ent.text.strip(),
                    "category": cat,
                    "relevance_score": 0.65,
                    "context": f"Named entity detected ({ent.label_}) in paper text.",
                })
    except Exception:
        pass

    return sorted(insights, key=lambda x: -x["relevance_score"])[:20]


async def extract_insights(raw_text: str) -> List[Dict]:
    """Async wrapper — runs extraction in a thread pool to avoid blocking."""
    return await asyncio.to_thread(_extract_sync, raw_text)
