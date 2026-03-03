import streamlit as st
import httpx

API_URL = "http://localhost:8000"

st.header("🏷️ Topics & Research Gaps")

paper_id = st.number_input("Paper ID", min_value=1, value=st.session_state.get("last_paper_id", 1), step=1)

col1, col2 = st.columns(2)

with col1:
    if st.button("Classify Topics", type="primary"):
        with st.spinner("Classifying..."):
            try:
                r = httpx.get(f"{API_URL}/papers/{paper_id}/topics", timeout=60)
                r.raise_for_status()
                result = r.json()
                if result.get("cached"):
                    st.caption("⚡ Cached")
                st.subheader("Topic Classification")
                for t in result["data"]:
                    confidence = t.get("confidence", 0) or 0
                    st.markdown(f"**{t['domain']}** › {t.get('sub_domain', 'N/A')}")
                    st.progress(confidence)
            except Exception as e:
                st.error(str(e))

with col2:
    if st.button("Detect Research Gaps", type="primary"):
        with st.spinner("Detecting gaps..."):
            try:
                r = httpx.get(f"{API_URL}/papers/{paper_id}/gaps", timeout=60)
                r.raise_for_status()
                result = r.json()
                if result.get("cached"):
                    st.caption("⚡ Cached")
                st.subheader("Research Gaps")
                priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                for g in result["data"]:
                    icon = priority_color.get(g.get("priority", ""), "⚪")
                    st.markdown(f"{icon} {g['gap_text']}")
            except Exception as e:
                st.error(str(e))
