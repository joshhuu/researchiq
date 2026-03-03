"""
Page 1: Upload & Parse
"""
import streamlit as st
import sys
sys.path.append("../")
from components.api_client import upload_paper, list_papers, delete_paper

st.title("📄 Upload Research Paper")
st.markdown("Upload a PDF research paper. PaperIQ will extract and parse its sections automatically.")

uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

if uploaded_file:
    st.info(f"**File:** {uploaded_file.name}  |  **Size:** {len(uploaded_file.getvalue()) / 1024:.1f} KB")
    if st.button("📤 Upload & Parse", type="primary"):
        with st.spinner("Uploading and parsing paper..."):
            try:
                result = upload_paper(uploaded_file.getvalue(), uploaded_file.name)
                st.success(f"✅ Paper uploaded successfully!")
                st.json(result)
                st.session_state["last_paper_id"] = result["paper_id"]
            except Exception as e:
                st.error(f"Upload failed: {e}")

st.markdown("---")
st.subheader("📚 Uploaded Papers")

try:
    papers = list_papers()
    if not papers:
        st.info("No papers uploaded yet.")
    else:
        for paper in papers:
            with st.expander(f"📄 {paper['title'] or paper['filename']} — {paper['status'].upper()}"):
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"**ID:** `{paper['paper_id']}`")
                col2.write(f"**Pages:** {paper['page_count']}")
                col3.write(f"**Status:** {paper['status']}")
                if col3.button("🗑️ Delete", key=f"del_{paper['paper_id']}"):
                    try:
                        delete_paper(paper["paper_id"])
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
except Exception as e:
    st.error(f"Could not connect to backend: {e}")
    st.info("Make sure the FastAPI backend is running: `uvicorn main:app --reload`")
