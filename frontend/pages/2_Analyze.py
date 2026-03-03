"""
Page 2: Analyze Paper
Tabs: Summaries | Insights & Keywords | Keyword Cloud | Topics | Research Gaps | Chat
"""
import streamlit as st
import sys
sys.path.append("../")
from components.api_client import list_papers, run_analysis, get_analysis, chat_with_paper

st.title("🧠 Analyze Paper")
st.markdown("Select a paper and run NLP analysis to get summaries, insights, and topic classification.")

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

# ── Summary length control ────────────────────────────────────────────────────
with st.expander("⚙️ Analysis Settings", expanded=False):
    n_sentences = st.slider(
        "Sentences per section in summary",
        min_value=1, max_value=10, value=3,
        help="Controls how many sentences are extracted per paper section. Higher = more detail."
    )

col1, col2 = st.columns(2)

if col1.button("🚀 Run Full Analysis", type="primary"):
    with st.spinner("Running NLP analysis… this usually takes a few seconds"):
        try:
            result = run_analysis(paper_id, n_sentences=n_sentences)
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

# ── Display results ───────────────────────────────────────────────────────────
result = st.session_state.get(f"analysis_{paper_id}")
if result:
    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📝 Summaries",
        "💡 Insights & Keywords",
        "☁️ Keyword Cloud",
        "🏷️ Topics",
        "🔍 Research Gaps",
        "💬 Chat with Paper",
    ])

    # ── Tab 1: Summaries ──────────────────────────────────────────────────────
    with tab1:
        summaries = result.get("summaries", [])
        if not summaries:
            st.info("No summaries yet.")
        else:
            order = ["full", "abstract", "introduction", "methodology", "results", "conclusion"]
            sorted_summaries = sorted(
                summaries,
                key=lambda s: order.index(s["summary_type"]) if s["summary_type"] in order else 99,
            )
            for s in sorted_summaries:
                label = s["summary_type"].replace("_", " ").title()
                with st.expander(f"📄 {label} Summary", expanded=(s["summary_type"] == "full")):
                    st.write(s["summary_text"])

    # ── Tab 2: Insights ───────────────────────────────────────────────────────
    with tab2:
        insights = result.get("insights", [])
        if not insights:
            st.info("No insights yet.")
        else:
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

    # ── Tab 3: Keyword Cloud ──────────────────────────────────────────────────
    with tab3:
        insights = result.get("insights", [])
        if not insights:
            st.info("Run analysis first to generate a keyword cloud.")
        else:
            try:
                from wordcloud import WordCloud
                import matplotlib.pyplot as plt

                freq = {i["keyword"]: max(1, int(i["relevance_score"] * 100)) for i in insights}

                wc = WordCloud(
                    width=900,
                    height=450,
                    background_color="white",
                    colormap="viridis",
                    max_words=60,
                    prefer_horizontal=0.8,
                ).generate_from_frequencies(freq)

                fig, ax = plt.subplots(figsize=(11, 5))
                ax.imshow(wc, interpolation="bilinear")
                ax.axis("off")
                st.pyplot(fig)
                plt.close(fig)

            except ImportError:
                # Fallback: horizontal bar chart
                import pandas as pd
                df = (
                    sorted(insights, key=lambda x: -x["relevance_score"])[:20]
                )
                st.bar_chart(
                    data={i["keyword"]: i["relevance_score"] for i in df},
                    use_container_width=True,
                )

            # Also show a plotly bar chart for filtering by category
            st.markdown("---")
            st.subheader("Top Keywords by Relevance")
            try:
                import plotly.express as px
                import pandas as pd
                df = pd.DataFrame(insights).sort_values("relevance_score", ascending=False).head(20)
                fig2 = px.bar(
                    df,
                    x="relevance_score",
                    y="keyword",
                    color="category",
                    orientation="h",
                    labels={"relevance_score": "Relevance", "keyword": "Keyword"},
                    title="Keyword Relevance Scores",
                    height=500,
                )
                fig2.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig2, use_container_width=True)
            except Exception:
                pass

    # ── Tab 4: Topics ─────────────────────────────────────────────────────────
    with tab4:
        topics = result.get("topics", [])
        if not topics:
            st.info("No topics yet.")
        else:
            try:
                import plotly.express as px
                import pandas as pd
                df = pd.DataFrame(topics).sort_values("confidence", ascending=False)
                fig = px.bar(
                    df,
                    x="confidence",
                    y="sub_domain",
                    color="domain",
                    orientation="h",
                    labels={"confidence": "Confidence", "sub_domain": "Sub-domain"},
                    title="Domain Classification",
                    range_x=[0, 1],
                    height=350,
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                for t in sorted(topics, key=lambda x: -x["confidence"]):
                    st.markdown(
                        f"**{t['domain']}** › {t.get('sub_domain', 'N/A')}  "
                        f"— confidence: `{t['confidence']:.0%}`"
                    )
                    st.progress(t["confidence"])

    # ── Tab 5: Research Gaps ──────────────────────────────────────────────────
    with tab5:
        gaps = result.get("gaps", [])
        if not gaps:
            st.info("No research gaps detected yet.")
        else:
            priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            # Sort: high → medium → low
            order_p = {"high": 0, "medium": 1, "low": 2}
            for g in sorted(gaps, key=lambda x: order_p.get(x.get("priority", "low"), 2)):
                icon = priority_color.get(g.get("priority", "low"), "⚪")
                st.markdown(f"{icon} **[{g.get('priority', 'N/A').upper()}]** {g['gap_text']}")
                st.divider()

    # ── Tab 6: Chat with Paper ────────────────────────────────────────────────
    with tab6:
        st.markdown(
            "**Ask anything about this paper.** "
            "Gemini reads the most relevant sections and gives you a grounded answer — "
            "it won't make things up beyond what the paper says."
        )

        # Per-paper history stored in session state
        chat_key = f"chat_history_{paper_id}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = []   # list of {role, content}
        history = st.session_state[chat_key]

        # Clear chat button
        if history and st.button("🗑️ Clear conversation", key=f"clear_chat_{paper_id}"):
            st.session_state[chat_key] = []
            st.rerun()

        # Display existing messages
        for msg in history:
            role_display = "assistant" if msg["role"] == "model" else msg["role"]
            with st.chat_message(role_display):
                st.markdown(msg["content"])

        question = st.chat_input("Ask a question about this paper…")
        if question:
            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                with st.spinner("Gemini is reading the paper…"):
                    try:
                        # Convert our history format → Gemini format for backend
                        gemini_history = [
                            {"role": m["role"], "parts": [m["content"]]}
                            for m in history
                        ]
                        resp = chat_with_paper(paper_id, question, gemini_history)
                        answer = resp.get("answer", "No answer returned.")
                        source = resp.get("source", "local")

                        st.markdown(answer)
                        if source == "gemini":
                            st.caption("✨ _Powered by Gemini — grounded on paper content_")
                        else:
                            st.caption("📄 _Local retrieval (set GEMINI_API_KEY for AI answers)_")

                        # Append both turns to history
                        history.append({"role": "user",  "content": question})
                        history.append({"role": "model", "content": answer})
                    except Exception as e:
                        st.error(f"Chat failed: {e}")

