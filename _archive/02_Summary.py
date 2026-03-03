import streamlit as st
import httpx

API_URL = "http://localhost:8000"

st.header("📝 Paper Summary")

paper_id = st.number_input("Paper ID", min_value=1, value=st.session_state.get("last_paper_id", 1), step=1)

if st.button("Generate Summary", type="primary"):
    with st.spinner("Calling AI to summarize..."):
        try:
            r = httpx.get(f"{API_URL}/papers/{paper_id}/summary", timeout=120)
            r.raise_for_status()
            result = r.json()
            data = result["data"]

            if result.get("cached"):
                st.caption("⚡ Loaded from cache")

            st.subheader("Full Summary")
            st.write(data.get("full_summary", "N/A"))

            col1, col2 = st.columns(2)
            with col1:
                if data.get("abstract_sum"):
                    st.markdown("**Abstract**")
                    st.info(data["abstract_sum"])
                if data.get("method_sum"):
                    st.markdown("**Methodology**")
                    st.info(data["method_sum"])
                if data.get("results_sum"):
                    st.markdown("**Results**")
                    st.info(data["results_sum"])
            with col2:
                if data.get("intro_sum"):
                    st.markdown("**Introduction**")
                    st.info(data["intro_sum"])
                if data.get("conclusion_sum"):
                    st.markdown("**Conclusion**")
                    st.info(data["conclusion_sum"])

        except httpx.HTTPStatusError as e:
            st.error(f"Error: {e.response.text}")
        except Exception as e:
            st.error(f"Error: {str(e)}")
