"""
gap_detector.py
Detects research gaps / limitations and compares multiple papers.

Gap detection pipeline:
  1. spaCy sentence tokenisation of results + conclusion text
  2. Sentence-transformer similarity against curated gap-seed phrases
  3. Explicit lexical pattern matching as a safety net
  4. Lightweight semantic deduplication

Paper comparison pipeline:
  1. Sentence-transformer embeddings per paper summary
  2. Cosine similarity matrix
  3. TF-IDF for common / distinctive terms across papers

No external API calls after models are first downloaded/cached.
"""
import asyncio
from typing import List, Dict

import numpy as np
import spacy
from sentence_transformers import SentenceTransformer, util
from sklearn.feature_extraction.text import TfidfVectorizer

# ── Lazy singletons ────────────────────────────────────────────────────────────
_nlp = None
_model = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


# ── Gap detection helpers ──────────────────────────────────────────────────────
_GAP_SEEDS = [
    "future work", "future research", "in the future", "in future work",
    "limitation", "limitations of", "we do not", "did not address",
    "remains a challenge", "open problem", "not yet addressed",
    "further study", "further research", "need to be explored",
    "could be improved", "leave for future", "beyond the scope",
    "has not been studied", "lack of", "insufficient data",
    "restricted to", "we cannot", "does not generalise",
]

_HIGH_PRIORITY_HINTS = ["limitation", "cannot", "fail", "did not", "lack", "restricted"]
_LOW_PRIORITY_HINTS  = ["future", "further", "could", "may", "potential", "explore"]


def _priority(sentence: str) -> str:
    s = sentence.lower()
    if any(p in s for p in _HIGH_PRIORITY_HINTS):
        return "high"
    if any(p in s for p in _LOW_PRIORITY_HINTS):
        return "low"
    return "medium"


def _detect_gaps_sync(results_text: str, conclusion_text: str) -> List[Dict]:
    combined = f"{results_text}\n\n{conclusion_text}".strip()
    if not combined:
        return []

    nlp    = _get_nlp()
    model  = _get_model()

    doc = nlp(combined[:8000])
    sentences = [s.text.strip() for s in doc.sents if len(s.text.strip()) > 30]
    if not sentences:
        return []

    # Embed seeds and sentences
    seed_embs = model.encode(_GAP_SEEDS,  convert_to_tensor=True)
    sent_embs = model.encode(sentences,   convert_to_tensor=True)

    # Each sentence's max-similarity to any gap seed
    sim_matrix  = util.cos_sim(sent_embs, seed_embs).cpu().numpy()
    max_sim     = sim_matrix.max(axis=1)

    # Select sentences that are semantically close to gaps OR match keywords
    gap_indices: list = []
    for i, sent in enumerate(sentences):
        s_lower = sent.lower()
        lexical_match = any(phrase in s_lower for phrase in _GAP_SEEDS)
        semantic_match = max_sim[i] > 0.35
        if lexical_match or semantic_match:
            gap_indices.append(i)

    if not gap_indices:
        return []

    gaps = [{"gap_text": sentences[i], "priority": _priority(sentences[i])}
            for i in gap_indices]

    # Semantic deduplication — keep sentences that are <85 % similar to already-kept ones
    if len(gaps) > 7:
        texts = [g["gap_text"] for g in gaps]
        g_embs = model.encode(texts, convert_to_tensor=True)
        sim = util.cos_sim(g_embs, g_embs).cpu().numpy()
        kept, kept_idx = [], []
        for i, gap in enumerate(gaps):
            if not any(sim[i][j] > 0.85 for j in kept_idx):
                kept.append(gap)
                kept_idx.append(i)
            if len(kept) >= 7:
                break
        gaps = kept

    return gaps[:7]


# ── Paper comparison helpers ───────────────────────────────────────────────────
def _compare_papers_sync(summaries: List[Dict]) -> Dict:
    model = _get_model()
    n = len(summaries)

    texts = [
        f"{s.get('title', '')}. {s.get('full_summary', '')}"
        for s in summaries
    ]

    embs = model.encode(texts, convert_to_tensor=True)
    sim_matrix = util.cos_sim(embs, embs).cpu().numpy()

    # ── TF-IDF: common and distinctive terms ──────────────────────────────────
    common_themes: List[str] = []
    diff_terms:    List[str] = []
    try:
        vec = TfidfVectorizer(stop_words="english", max_features=300, ngram_range=(1, 2))
        tfidf  = vec.fit_transform(texts).toarray()
        names  = vec.get_feature_names_out()

        avg    = tfidf.mean(axis=0)
        var    = tfidf.var(axis=0)

        top_avg_idx = np.argsort(avg)[::-1][:8]
        common_themes = [
            f"Shared focus on: {names[i]}"
            for i in top_avg_idx if avg[i] > 0
        ][:5]

        top_var_idx = np.argsort(var)[::-1][:8]
        diff_terms = [
            f"Distinctive term: {names[i]}"
            for i in top_var_idx
        ][:5]
    except Exception:
        pass

    # ── Complementary pairs (moderate similarity) ─────────────────────────────
    complementary: List[str] = []
    for i in range(n):
        for j in range(i + 1, n):
            score = float(sim_matrix[i][j])
            if 0.25 < score < 0.80:
                t1 = summaries[i].get("title", f"Paper {i + 1}")
                t2 = summaries[j].get("title", f"Paper {j + 1}")
                complementary.append(
                    f'"{t1}" and "{t2}" address related but distinct aspects '
                    f"(semantic similarity: {score:.0%})"
                )

    # ── Comparison table ───────────────────────────────────────────────────────
    comparison_table = [
        {
            "aspect": "Research Focus",
            "papers": {str(i + 1): s.get("title", "Untitled") for i, s in enumerate(summaries)},
        },
        {
            "aspect": "Similarity to Paper 1",
            "papers": {
                str(i + 1): (
                    "baseline" if i == 0
                    else f"{float(sim_matrix[0][i]):.0%}"
                )
                for i in range(n)
            },
        },
    ]

    # Recommended reading order: most content-dense summary first
    order = sorted(range(n), key=lambda i: len(summaries[i].get("full_summary", "")), reverse=True)

    return {
        "common_themes":             common_themes or ["Overlapping research areas identified."],
        "differences":               diff_terms    or ["Papers address distinct sub-problems."],
        "complementary_aspects":     complementary or ["Papers complement each other in scope."],
        "recommended_reading_order": [o + 1 for o in order],
        "comparison_table":          comparison_table,
    }


# ── Public async API ───────────────────────────────────────────────────────────
async def detect_gaps(results: str, conclusion: str) -> List[Dict]:
    """Detect research gaps from a paper's results + conclusion text."""
    return await asyncio.to_thread(_detect_gaps_sync, results, conclusion)


async def compare_papers(summaries: List[Dict]) -> Dict:
    """Compare multiple papers semantically and return structured analysis."""
    return await asyncio.to_thread(_compare_papers_sync, summaries)
