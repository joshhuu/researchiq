import streamlit as st
import httpx
import pandas as pd

API_URL = "http://localhost:8000"

st.header("🔍 Insights & Keywords")

paper_id = st.number_input("Paper ID", min_value=1, value=st.session_state.get("last_paper_id", 1), step=1)

if st.button("Extract Insights", type="primary"):
    with st.spinner("Extracting insights with AI..."):
        try:
            r = httpx.get(f"{API_URL}/papers/{paper_id}/insights", timeout=120)
            r.raise_for_status()
            result = r.json()

            if result.get("cached"):
                st.caption("⚡ Loaded from cache")

            df = pd.DataFrame(result["data"])
            if not df.empty:
                categories = ["All"] + df["category"].unique().tolist()
                selected = st.selectbox("Filter by category", categories)
                filtered = df if selected == "All" else df[df["category"] == selected]
                st.dataframe(filtered.sort_values("score", ascending=False), use_container_width=True)

                # Show keyword summary per category
                st.subheader("Breakdown by Category")
                for cat in df["category"].unique():
                    items = df[df["category"] == cat]["keyword"].tolist()
                    st.markdown(f"**{cat.title()}**: {', '.join(items)}")
        except httpx.HTTPStatusError as e:
            st.error(f"Error: {e.response.text}")
        except Exception as e:
            st.error(f"Error: {str(e)}")
