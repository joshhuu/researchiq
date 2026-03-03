"""
Page 4: Export Results
"""
import streamlit as st
import sys
sys.path.append("../")
from components.api_client import list_papers, export_paper

st.title("📥 Export Results")
st.markdown("Download analysis results as a PDF report or CSV file.")

try:
    papers = list_papers()
except Exception as e:
    st.error(f"Cannot reach backend: {e}")
    st.stop()

analyzed = [p for p in papers if p.get("status", "uploaded") in ("analyzed", "uploaded")]
if not analyzed:
    st.warning("No analyzed papers found. Run analysis first.")
    st.stop()

options = {f"{p['title'] or p['filename']}": p["paper_id"] for p in analyzed}
selected = st.selectbox("Select a paper to export", list(options.keys()))
paper_id = options[selected]

col1, col2 = st.columns(2)

with col1:
    if st.button("📄 Export as PDF"):
        with st.spinner("Generating PDF..."):
            try:
                data = export_paper(paper_id, "pdf")
                st.download_button(
                    "⬇️ Download PDF",
                    data=data,
                    file_name=f"{selected}_analysis.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(str(e))

with col2:
    if st.button("📊 Export as CSV"):
        with st.spinner("Generating CSV..."):
            try:
                data = export_paper(paper_id, "csv")
                st.download_button(
                    "⬇️ Download CSV",
                    data=data,
                    file_name=f"{selected}_analysis.csv",
                    mime="text/csv",
                )
            except Exception as e:
                st.error(str(e))
