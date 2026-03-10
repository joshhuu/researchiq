"""
trend_analyzer.py
Cross-paper trend analysis using sentence-transformer embeddings + TF-IDF.

Identifies common themes, diverging focuses, and trending keywords across a
set of research papers without calling any external API.
"""
from typing import List, Dict

import numpy as np
from sentence_transformers import SentenceTransformer, util
from sklearn.feature_extraction.text import TfidfVectorizer

# Lazy singleton
_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def analyze_trends(papers: List[Dict]) -> Dict:
    """
    Analyse trends across multiple papers.

    Args:
        papers: list of dicts with keys:
            - title        (str)
            - full_summary (str)
            - keywords     (list[str], optional)

    Returns:
        dict with keys: trends, gaps, similarities, differences
    """
    if not papers:
        return {"trends": [], "gaps": [], "similarities": [], "differences": []}

    model = _get_model()

    # Build text representations
    texts = []
    for p in papers:
        kws = ", ".join(p.get("keywords", [])[:15])
        texts.append(f"{p.get('title', '')}. {p.get('full_summary', '')} {kws}")

    n = len(texts)
    embs = model.encode(texts, convert_to_tensor=True)
    sim_matrix = util.cos_sim(embs, embs).cpu().numpy()

    # ── TF-IDF ─────────────────────────────────────────────────────────────────
    trends:      List[str] = []
    gaps:        List[str] = []
    differences: List[str] = []

    try:
        vec   = TfidfVectorizer(stop_words="english", max_features=300, ngram_range=(1, 2))
        tfidf = vec.fit_transform(texts).toarray()
        names = vec.get_feature_names_out()

        avg = tfidf.mean(axis=0)
        var = tfidf.var(axis=0)

        # Trends = highest average TF-IDF (common across papers)
        top_avg = np.argsort(avg)[::-1][:6]
        trends = [f"Recurring theme across papers: '{names[i]}'" for i in top_avg if avg[i] > 0][:5]

        # Differences = highest variance (exclusive to one paper)
        top_var = np.argsort(var)[::-1][:6]
        differences = [f"Paper-specific focus: '{names[i]}'" for i in top_var][:4]

        # Gap proxy: terms that appear in only one paper and are semantically unique
        paper_term_counts = (tfidf > 0).sum(axis=0)
        unique_idx = np.where(paper_term_counts == 1)[0]
        unique_terms = [names[i] for i in unique_idx if avg[i] > 0.02][:5]
        gaps = [
            f"Topic '{t}' is addressed by only one paper — potential gap in collective coverage."
            for t in unique_terms
        ]

    except Exception:
        pass

    # ── Similarities ───────────────────────────────────────────────────────────
    similarities: List[str] = []
    for i in range(n):
        for j in range(i + 1, n):
            score = float(sim_matrix[i][j])
            if score > 0.50:
                t1 = papers[i].get("title", f"Paper {i + 1}")
                t2 = papers[j].get("title", f"Paper {j + 1}")
                similarities.append(
                    f'"{t1}" and "{t2}" share strong thematic overlap ({score:.0%} similarity).'
                )

    if not similarities:
        similarities = ["No strongly similar paper pairs found among the selected set."]

    return {
        "trends":      trends      or ["No strong recurring themes detected."],
        "gaps":        gaps        or ["No obvious coverage gaps detected."],
        "similarities": similarities,
        "differences": differences or ["Papers address clearly distinct sub-domains."],
    }
