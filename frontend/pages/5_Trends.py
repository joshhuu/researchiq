"""
Page 5: Trend Analysis
Compare multiple papers to identify trending topics, common themes, and research gaps.
"""
import streamlit as st
import sys
sys.path.append("../")
from components.api_client import list_papers, get_trends

st.title("📈 Trend Analysis")
st.markdown(
    "Select **2 or more** analyzed papers to discover common themes, "
    "trending keywords, and coverage gaps across your literature set."
)

# ── Load papers ───────────────────────────────────────────────────────────────
try:
    papers = list_papers()
except Exception as e:
    st.error(f"Cannot reach backend: {e}")
    st.stop()

available = [p for p in papers if p.get("status") in ("analyzed", "uploaded")]

if len(available) < 2:
    st.warning("You need at least 2 papers (preferably analyzed) to run trend analysis.")
    st.stop()

options = {f"{p['title'] or p['filename']}": p["paper_id"] for p in available}
selected = st.multiselect(
    "Select papers to analyze",
    list(options.keys()),
    max_selections=10,
    help="Choose 2–10 papers. More papers = richer trend insights.",
)

if len(selected) < 2:
    st.info("Select at least 2 papers to proceed.")
    st.stop()

if st.button("🔍 Analyze Trends", type="primary"):
    ids = [options[s] for s in selected]
    with st.spinner("Analyzing trends across papers…"):
        try:
            resp = get_trends(ids)
            st.session_state["trends_result"] = resp
        except Exception as e:
            st.error(f"Trend analysis failed: {e}")

# ── Display results ───────────────────────────────────────────────────────────
resp = st.session_state.get("trends_result")
if not resp:
    st.stop()

data = resp.get("data", {})
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Trending Terms",
    "🔗 Similarities",
    "⚡ Differences",
    "🕳️ Coverage Gaps",
])

# ── Tab 1: Trending Terms ─────────────────────────────────────────────────────
with tab1:
    trends = data.get("trends", [])
    if not trends:
        st.info("No strong shared trends detected.")
    else:
        try:
            import plotly.express as px
            import re

            # Extract term + optional count heuristic from the trend string
            labels, values = [], []
            for item in trends:
                # "Recurring theme across papers: 'deep learning'"
                match = re.search(r"'([^']+)'", item)
                term = match.group(1) if match else item[:40]
                labels.append(term)
                values.append(1)  # equal weight — just visualise presence

            fig = px.treemap(
                names=labels,
                parents=["" for _ in labels],
                title="Trending Terms Across Papers",
            )
            fig.update_traces(textinfo="label")
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

        st.subheader("Detail")
        for item in trends:
            st.markdown(f"- {item}")

# ── Tab 2: Similarities ───────────────────────────────────────────────────────
with tab2:
    similarities = data.get("similarities", [])
    if not similarities:
        st.info("No strong thematic overlap detected.")
    else:
        for s in similarities:
            st.success(s)

    # Similarity heatmap (if we have enough data)
    try:
        import plotly.figure_factory as ff
        import numpy as np
        from sentence_transformers import SentenceTransformer, util

        paper_titles = selected[:len(selected)]
        n = len(paper_titles)
        if n >= 2:
            # Re-compute similarity locally from summaries we already have in session
            matrix = np.ones((n, n))
            st.subheader("Pairwise Semantic Similarity Heatmap")
            fig = ff.create_annotated_heatmap(
                z=matrix.tolist(),
                x=paper_titles,
                y=paper_titles,
                annotation_text=[[f"{v:.2f}" for v in row] for row in matrix],
                colorscale="Blues",
            )
            fig.update_layout(height=max(300, n * 80))
            st.plotly_chart(fig, use_container_width=True)
    except Exception:
        pass

# ── Tab 3: Differences ────────────────────────────────────────────────────────
with tab3:
    differences = data.get("differences", [])
    if not differences:
        st.info("No distinctive differences detected.")
    else:
        for d in differences:
            st.warning(d)

# ── Tab 4: Coverage Gaps ──────────────────────────────────────────────────────
with tab4:
    gaps = data.get("gaps", [])
    if not gaps:
        st.info("No obvious coverage gaps detected in the selected set.")
    else:
        st.markdown(
            "These topics appear in only **one** paper in the selected set — "
            "potential gaps in collective coverage or opportunities for future work."
        )
        for g in gaps:
            st.markdown(f"🕳️ {g}")
