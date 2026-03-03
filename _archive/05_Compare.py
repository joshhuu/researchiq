import streamlit as st
import httpx

API_URL = "http://localhost:8000"

st.header("⚖️ Compare Papers")
st.info("Enter comma-separated Paper IDs to compare (e.g. 1, 2, 3). Each paper must have a summary generated first.")

ids_input = st.text_input("Paper IDs", placeholder="1, 2")

if st.button("Compare", type="primary"):
    try:
        ids = [int(x.strip()) for x in ids_input.split(",") if x.strip()]
        if len(ids) < 2:
            st.warning("Please enter at least 2 paper IDs.")
        else:
            with st.spinner("Comparing papers with AI..."):
                r = httpx.post(f"{API_URL}/papers/compare", json={"paper_ids": ids}, timeout=120)
                r.raise_for_status()
                result = r.json()["data"]

                st.subheader("Common Themes")
                for theme in result.get("common_themes", []):
                    st.markdown(f"• {theme}")

                st.subheader("Key Differences")
                for diff in result.get("differences", []):
                    st.markdown(f"• {diff}")

                st.subheader("Complementary Aspects")
                for aspect in result.get("complementary_aspects", []):
                    st.markdown(f"• {aspect}")

                if result.get("comparison_table"):
                    st.subheader("Comparison Table")
                    import pandas as pd
                    rows = []
                    for row in result["comparison_table"]:
                        r_dict = {"Aspect": row["aspect"]}
                        for pid, desc in row.get("papers", {}).items():
                            r_dict[f"Paper {pid}"] = desc
                        rows.append(r_dict)
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    except ValueError:
        st.error("Invalid IDs — enter numbers separated by commas.")
    except httpx.HTTPStatusError as e:
        st.error(f"API error: {e.response.text}")
    except Exception as e:
        st.error(str(e))
