"""
Page 2: Analyze Paper
"""
import streamlit as st
import sys
sys.path.append("../")
from components.api_client import list_papers, run_analysis, get_analysis

st.title("🧠 Analyze Paper")
st.markdown("Select a paper and run AI analysis to get summaries, insights, and topic classification.")

try:
    papers = list_papers()
except Exception as e:
    st.error(f"Cannot reach backend: {e}")
    st.stop()

if not papers:
    st.warning("No papers found. Upload one first.")
    st.stop()

paper_options = {f"{p['title'] or p['filename']} ({p.get('status', 'uploaded')})": p["paper_id"] for p in papers}
selected_label = st.selectbox("Select a paper", list(paper_options.keys()))
paper_id = paper_options[selected_label]

col1, col2 = st.columns(2)

if col1.button("🚀 Run Full Analysis", type="primary"):
    with st.spinner("Running AI analysis... this may take 15–30 seconds"):
        try:
            result = run_analysis(paper_id)
            st.session_state[f"analysis_{paper_id}"] = result
            st.success("✅ Analysis complete!")
        except Exception as e:
            st.error(f"Analysis failed: {e}")

if col2.button("📂 Load Cached Results"):
    try:
        result = get_analysis(paper_id)
        st.session_state[f"analysis_{paper_id}"] = result
    except Exception as e:
        st.error(str(e))

# Display results
result = st.session_state.get(f"analysis_{paper_id}")
if result:
    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Summaries", "💡 Insights & Keywords", "🏷️ Topics", "🔍 Research Gaps"])

    with tab1:
        summaries = result.get("summaries", [])
        if not summaries:
            st.info("No summaries yet.")
        for s in summaries:
            st.subheader(f"{s['summary_type'].replace('_', ' ').title()} Summary")
            st.write(s["summary_text"])
            st.divider()

    with tab2:
        insights = result.get("insights", [])
        if not insights:
            st.info("No insights yet.")

        # Group by category
        categories = sorted(set(i["category"] for i in insights))
        for cat in categories:
            cat_insights = [i for i in insights if i["category"] == cat]
            st.subheader(f"🔹 {cat.title()} ({len(cat_insights)})")
            for ins in sorted(cat_insights, key=lambda x: -x["relevance_score"]):
                score_bar = "█" * int(ins["relevance_score"] * 10)
                st.markdown(f"**{ins['keyword']}** `{score_bar}` {ins['relevance_score']:.2f}")
                if ins.get("context"):
                    st.caption(ins["context"])
            st.divider()

    with tab3:
        topics = result.get("topics", [])
        if not topics:
            st.info("No topics yet.")
        for t in sorted(topics, key=lambda x: -x["confidence"]):
            st.markdown(
                f"**{t['domain']}** › {t.get('sub_domain', 'N/A')}  "
                f"— confidence: `{t['confidence']:.0%}`"
            )
            st.progress(t["confidence"])

    with tab4:
        gaps = result.get("gaps", [])
        if not gaps:
            st.info("No research gaps detected yet.")
        priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        for g in gaps:
            icon = priority_color.get(g.get("priority", "low"), "⚪")
            st.markdown(f"{icon} **[{g.get('priority', 'N/A').upper()}]** {g['gap_text']}")
            st.divider()
