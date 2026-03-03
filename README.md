# PaperIQ — AI Research Paper Analyzer

## Setup

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY

# 3. Run backend (from project root)
uvicorn backend.main:app --reload --port 8000

# 4. Run frontend (separate terminal)
streamlit run frontend/app.py
```

- API docs: http://localhost:8000/docs
- Streamlit UI: http://localhost:8501

## Quick API Test

```bash
# Upload a paper
curl -X POST http://localhost:8000/papers/upload \
  -F "file=@your_paper.pdf"

# Get summary (replace 1 with your paper_id)
curl http://localhost:8000/papers/1/summary

# Get insights
curl http://localhost:8000/papers/1/insights

# Get topics
curl http://localhost:8000/papers/1/topics

# Get research gaps
curl http://localhost:8000/papers/1/gaps

# Export as PDF
curl http://localhost:8000/papers/1/export?format=pdf --output report.pdf
```
