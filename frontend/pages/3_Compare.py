"""
Page 3: Compare Papers
"""
import streamlit as st
import sys
sys.path.append("../")
from components.api_client import list_papers, compare_papers

st.title("🔀 Compare Papers")
st.markdown("Select 2 or more analyzed papers to identify trends, research gaps, and similarities.")

try:
    papers = list_papers()
except Exception as e:
    st.error(f"Cannot reach backend: {e}")
    st.stop()

analyzed = [p for p in papers if p.get("status", "uploaded") in ("analyzed", "uploaded")]

if len(analyzed) < 2:
    st.warning("You need at least 2 analyzed papers to compare. Run analysis on more papers first.")
    st.stop()

options = {f"{p['title'] or p['filename']}": p["paper_id"] for p in analyzed}
selected = st.multiselect("Select papers to compare", list(options.keys()), max_selections=5)

if len(selected) >= 2:
    if st.button("🔍 Compare Selected Papers", type="primary"):
        ids = [options[s] for s in selected]
        with st.spinner("Analyzing across papers..."):
            try:
                result = compare_papers(ids)
                st.session_state["compare_result"] = result
            except Exception as e:
                st.error(f"Comparison failed: {e}")

result = st.session_state.get("compare_result")
if result:
    data = result.get("data", {})
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Common Themes")
        for t in data.get("common_themes") or []:
            st.markdown(f"- {t}")

        st.subheader("🔗 Complementary Aspects")
        for s in data.get("complementary_aspects") or []:
            st.markdown(f"- {s}")

    with col2:
        st.subheader("⚡ Key Differences")
        for g in data.get("differences") or []:
            st.markdown(f"- {g}")

    table = data.get("comparison_table") or []
    if table:
        st.markdown("---")
        st.subheader("📊 Comparison Table")
        import pandas as pd
        rows = []
        for entry in table:
            row = {"Aspect": entry.get("aspect", "")}
            for paper_num, desc in (entry.get("papers") or {}).items():
                row[f"Paper {paper_num}"] = desc
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
