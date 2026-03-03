import streamlit as st
import httpx

API_URL = "http://localhost:8000"

st.header("📤 Upload Research Paper")

uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

if uploaded_file:
    st.write(f"**File:** {uploaded_file.name} ({uploaded_file.size // 1024} KB)")

    if st.button("Upload & Parse", type="primary"):
        with st.spinner("Uploading and extracting text..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            try:
                r = httpx.post(f"{API_URL}/papers/upload", files=files, timeout=60)
                r.raise_for_status()
                data = r.json()
                st.success(f"✅ Uploaded! Paper ID: **{data['paper_id']}**")
                st.json(data)
                st.session_state["last_paper_id"] = data["paper_id"]
                st.info("Now go to the Summary, Insights, or Topics pages to analyze this paper.")
            except httpx.HTTPStatusError as e:
                st.error(f"Upload failed: {e.response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

st.divider()
st.subheader("Previously Uploaded Papers")
try:
    r = httpx.get(f"{API_URL}/papers/", timeout=10)
    papers = r.json()
    if papers:
        for p in papers:
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.write(f"📄 **{p['title'] or p['filename']}** (ID: {p['paper_id']})")
            col2.write(f"{p['page_count']} pages" if p['page_count'] else "")
            if col3.button("Select", key=f"sel_{p['paper_id']}"):
                st.session_state["last_paper_id"] = p["paper_id"]
                st.success(f"Selected paper ID {p['paper_id']}")
    else:
        st.info("No papers uploaded yet.")
except Exception as e:
    st.error(f"Could not load papers: {e}")
