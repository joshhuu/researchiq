# PaperIQ — Project Structure & Workflow

## Overview

PaperIQ is a FastAPI backend that accepts research paper PDFs and returns AI-powered analysis:
summaries, keywords, insights, topic classification, and gap detection. The Streamlit frontend
consumes the API directly. Later, the backend stays identical while the frontend is swapped to React.

---

## Directory Structure

```
paperiq/
│
├── backend/                        # FastAPI app
│   ├── main.py                     # App entry point, registers all routers
│   ├── config.py                   # Settings (API keys, model names, DB URL)
│   ├── database.py                 # SQLite/PostgreSQL setup via SQLAlchemy
│   │
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── paper.py                # ResearchPaper table
│   │   ├── summary.py              # Summary table
│   │   ├── insight.py              # Insight / Keyword table
│   │   └── topic.py                # Topic classification table
│   │
│   ├── schemas/                    # Pydantic request/response schemas
│   │   ├── paper.py
│   │   ├── summary.py
│   │   ├── insight.py
│   │   └── topic.py
│   │
│   ├── routers/                    # One file per feature domain
│   │   ├── upload.py               # POST /papers/upload
│   │   ├── summary.py              # GET  /papers/{id}/summary
│   │   ├── insights.py             # GET  /papers/{id}/insights
│   │   ├── topics.py               # GET  /papers/{id}/topics
│   │   ├── compare.py              # POST /papers/compare
│   │   └── export.py               # GET  /papers/{id}/export
│   │
│   ├── services/                   # Business logic (pure Python, no FastAPI)
│   │   ├── pdf_parser.py           # PDF → structured text
│   │   ├── summarizer.py           # Claude API → summaries
│   │   ├── insight_extractor.py    # Claude API → keywords + insights
│   │   ├── topic_classifier.py     # Claude API → domain classification
│   │   └── gap_detector.py         # Claude API → research gap analysis
│   │
│   └── utils/
│       ├── text_cleaner.py         # Noise removal, section splitter
│       └── prompt_templates.py     # All LLM prompt strings in one place
│
├── frontend/                       # Streamlit app (Phase 1)
│   ├── app.py                      # Main Streamlit entry point
│   └── pages/
│       ├── 01_Upload.py
│       ├── 02_Summary.py
│       ├── 03_Insights.py
│       ├── 04_Topics.py
│       └── 05_Compare.py
│
├── tests/
│   ├── test_upload.py
│   ├── test_summarizer.py
│   └── test_insights.py
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## API Endpoints

| Method | Endpoint                    | Description                              |
|--------|-----------------------------|------------------------------------------|
| POST   | `/papers/upload`            | Upload PDF, parse, store, return paper_id |
| GET    | `/papers/`                  | List all uploaded papers                  |
| GET    | `/papers/{id}`              | Get paper metadata                        |
| GET    | `/papers/{id}/summary`      | Get full + section-wise summary           |
| GET    | `/papers/{id}/insights`     | Get keywords, objectives, methods        |
| GET    | `/papers/{id}/topics`       | Get domain + sub-domain classification   |
| GET    | `/papers/{id}/gaps`         | Get research gap analysis                |
| POST   | `/papers/compare`           | Compare 2+ papers side-by-side           |
| GET    | `/papers/{id}/export`       | Download summary as PDF or CSV           |
| DELETE | `/papers/{id}`              | Delete a paper and its analysis          |

---

## Data Flow / Workflow

```
[User uploads PDF]
        │
        ▼
┌─────────────────────────────┐
│  POST /papers/upload        │
│  • Validate file type/size  │
│  • Save PDF to disk         │
│  • Extract raw text (pypdf) │
│  • Split into sections      │
│  • Clean text               │
│  • Store in DB              │
│  • Return paper_id          │
└─────────────┬───────────────┘
              │  paper_id
              ▼
┌─────────────────────────────┐      ┌──────────────────────┐
│  GET /papers/{id}/summary   │─────▶│  Claude API          │
│  • Load text from DB        │      │  prompt_templates.py  │
│  • Send to summarizer svc   │      │  returns JSON         │
│  • Cache result in DB       │◀─────│                      │
│  • Return summary JSON      │      └──────────────────────┘
└─────────────────────────────┘

[Same pattern for /insights, /topics, /gaps]

┌─────────────────────────────┐
│  POST /papers/compare       │
│  • Load 2+ papers by ID     │
│  • Send all summaries to AI │
│  • Return comparison table  │
└─────────────────────────────┘

┌─────────────────────────────┐
│  GET /papers/{id}/export    │
│  • Fetch all stored results │
│  • Build PDF/CSV            │
│  • Stream file to client    │
└─────────────────────────────┘
```

---

## Database Schema

```sql
-- Users (optional for Phase 1, add auth later)
CREATE TABLE users (
    user_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT,
    role      TEXT DEFAULT 'researcher'
);

-- Core paper record
CREATE TABLE research_papers (
    paper_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT,
    filename       TEXT,
    file_path      TEXT,
    extracted_text TEXT,
    page_count     INTEGER,
    uploaded_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id        INTEGER REFERENCES users(user_id)
);

-- Summaries (one row per paper; JSON stored in columns)
CREATE TABLE summaries (
    summary_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id      INTEGER REFERENCES research_papers(paper_id),
    abstract_sum  TEXT,
    intro_sum     TEXT,
    method_sum    TEXT,
    results_sum   TEXT,
    conclusion_sum TEXT,
    full_summary  TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Extracted keywords and insights
CREATE TABLE insights (
    insight_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id    INTEGER REFERENCES research_papers(paper_id),
    keyword     TEXT,
    category    TEXT,   -- 'keyword' | 'objective' | 'method' | 'finding'
    score       REAL    -- relevance score 0–1
);

-- Topic classification
CREATE TABLE topics (
    topic_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id    INTEGER REFERENCES research_papers(paper_id),
    domain      TEXT,
    sub_domain  TEXT,
    confidence  REAL
);

-- Research gaps
CREATE TABLE gaps (
    gap_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id    INTEGER REFERENCES research_papers(paper_id),
    gap_text    TEXT,
    priority    TEXT    -- 'high' | 'medium' | 'low'
);
```

---

## Key Design Decisions

**1. Lazy AI Analysis**
AI calls are NOT triggered on upload. Each endpoint (`/summary`, `/insights`, `/topics`) calls the
AI service on first request and caches the result in the DB. Subsequent requests return cached data
instantly. This keeps upload fast and lets users choose what analysis to run.

**2. Prompt Templates Centralized**
All Claude prompts live in `utils/prompt_templates.py`. This makes it easy to tune prompts without
touching business logic.

**3. Section-Aware Parsing**
`services/pdf_parser.py` uses regex heuristics to detect Abstract, Introduction, Methodology,
Results, and Conclusion sections. Each section is stored and passed individually to the summarizer.

**4. React-Ready API**
All responses are clean JSON with consistent envelope:
```json
{
  "paper_id": 1,
  "status": "success",
  "data": { ... },
  "cached": true
}
```
No Streamlit-specific logic leaks into the backend — the frontend is purely a consumer.

**5. Streaming Support (Optional)**
The `/summary` endpoint supports `?stream=true` via Server-Sent Events so the Streamlit or React
UI can show tokens as they arrive.

---

## Claude API Prompt Strategy

| Endpoint   | Prompt Input                        | Expected Output          |
|------------|-------------------------------------|--------------------------|
| /summary   | Full paper text (chunked if long)   | Section-wise summaries   |
| /insights  | Abstract + Conclusion               | JSON list of keywords    |
| /topics    | Title + Abstract                    | Domain + sub-domain      |
| /gaps      | Results + Conclusion                | Bulleted gap list        |
| /compare   | Multiple summaries concatenated     | Comparison table JSON    |

---

## Phase Roadmap

**Phase 1 (Now) — FastAPI + Streamlit**
- All backend endpoints working
- Streamlit pages consuming the API
- SQLite database
- Basic auth (API key header)

**Phase 2 — Polish**
- Switch DB to PostgreSQL
- Add user accounts + JWT auth
- Add paper tagging and search
- Batch upload support

**Phase 3 — React Frontend**
- Keep FastAPI backend 100% unchanged
- Build React SPA consuming same endpoints
- Add keyword cloud visualization (D3.js)
- Multi-paper comparison dashboard

---

## Running the App

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
streamlit run app.py
```

API docs auto-generated at: `http://localhost:8000/docs`
