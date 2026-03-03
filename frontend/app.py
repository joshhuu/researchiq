import streamlit as st

st.set_page_config(
    page_title="PaperIQ",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📄 PaperIQ — AI Research Analyzer")
st.markdown("""
Welcome to **PaperIQ**. Upload a research paper PDF to get:
- ✅ Automated section-wise summaries
- ✅ Key insights and keywords
- ✅ Topic and domain classification
- ✅ Research gap detection
- ✅ Multi-paper comparison
""")

st.info("👈 Use the sidebar to navigate between pages.")

# Show API status
import httpx
API_URL = "http://localhost:8000"
try:
    r = httpx.get(f"{API_URL}/health", timeout=2)
    if r.status_code == 200:
        st.success("✅ API is running")
    else:
        st.error("⚠️ API returned an error")
except Exception:
    st.error("❌ Cannot reach API at http://localhost:8000 — make sure the backend is running.")
