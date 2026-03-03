# PaperIQ — Project Structure & Workflow

## Overview

PaperIQ is a FastAPI backend with a Streamlit frontend (upgradeable to React).
All AI analysis is powered by the Claude API (Anthropic).

---

## Directory Structure

```
paperiq/
│
├── backend/                        # FastAPI application
│   ├── main.py                     # App entry point, CORS, router registration
│   ├── config.py                   # Settings (API keys, model names, env vars)
│   ├── dependencies.py             # Shared FastAPI dependencies (e.g. DB session)
│   │
│   ├── routers/                    # One file per feature domain
│   │   ├── papers.py               # Upload, list, delete papers
│   │   ├── analysis.py             # Trigger & fetch analysis (summary, insights, topics)
│   │   └── export.py               # Export results as PDF/CSV
│   │
│   ├── services/                   # Business logic (pure Python, no FastAPI)
│   │   ├── pdf_parser.py           # PDF text extraction & section detection
│   │   ├── summarizer.py           # Claude API: summarization
│   │   ├── insight_extractor.py    # Claude API: keyword & insight extraction
│   │   ├── topic_classifier.py     # Claude API: domain classification
│   │   └── trend_analyzer.py       # Claude API: cross-paper trend analysis
│   │
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── paper.py                # ResearchPaper table
│   │   ├── summary.py              # Summary table
│   │   ├── insight.py              # Insight/Keyword table
│   │   └── topic.py                # Topic/Domain table
│   │
│   ├── schemas/                    # Pydantic request/response models
│   │   ├── paper.py
│   │   ├── analysis.py
│   │   └── export.py
│   │
│   ├── db/
│   │   ├── base.py                 # SQLAlchemy Base
│   │   └── session.py              # DB engine & session factory
│   │
│   └── utils/
│       ├── file_handler.py         # Save/delete uploaded files
│       └── export_utils.py         # PDF/CSV export helpers
│
├── frontend/                       # Streamlit app
│   ├── app.py                      # Main Streamlit entry point
│   ├── pages/
│   │   ├── 1_Upload.py             # Upload & parse paper
│   │   ├── 2_Analyze.py            # Trigger analysis, view results
│   │   ├── 3_Compare.py            # Multi-paper comparison
│   │   └── 4_Export.py             # Export summaries/insights
│   └── components/
│       ├── paper_card.py           # Reusable paper display card
│       ├── keyword_cloud.py        # Word cloud visualization
│       └── api_client.py           # All HTTP calls to FastAPI backend
│
├── uploads/                        # Uploaded PDFs (gitignored)
├── exports/                        # Generated exports (gitignored)
├── paperiq.db                      # SQLite database (dev only)
│
├── requirements.txt
├── .env                            # ANTHROPIC_API_KEY, DATABASE_URL
└── README.md
```

---

## Data Flow & Workflow

```
User (Streamlit UI)
        │
        │  1. Upload PDF
        ▼
[POST /papers/upload]  ←── FastAPI Router (papers.py)
        │
        │  2. Save file to /uploads/
        │  3. Extract text with pdfplumber
        │  4. Detect sections (Abstract, Intro, Methods, Results, Conclusion)
        │  5. Store raw paper record in DB
        ▼
   DB: research_papers (paper_id, title, raw_text, sections_json)
        │
        │  6. User triggers "Analyze"
        ▼
[POST /analysis/{paper_id}]  ←── FastAPI Router (analysis.py)
        │
        ├──► summarizer.py       → Claude API → summaries table
        ├──► insight_extractor.py → Claude API → insights table
        └──► topic_classifier.py  → Claude API → topics table
        │
        │  7. Return combined AnalysisResult to frontend
        ▼
[GET /analysis/{paper_id}]  ←── Fetch cached results anytime
        │
        ▼
   Streamlit renders:
   - Summary cards (per section)
   - Keyword cloud
   - Insight highlights
   - Topic/domain tags
        │
        │  8. (Optional) Compare multiple papers
        ▼
[POST /analysis/compare]
        │
        └──► trend_analyzer.py  → Claude API → gaps, trends, similarities
        │
        │  9. (Optional) Export
        ▼
[GET /export/{paper_id}?format=pdf|csv]
```

---

## API Endpoints

### Papers
| Method | Endpoint              | Description                        |
|--------|-----------------------|------------------------------------|
| POST   | /papers/upload        | Upload a PDF                       |
| GET    | /papers               | List all uploaded papers           |
| GET    | /papers/{paper_id}    | Get paper metadata + raw sections  |
| DELETE | /papers/{paper_id}    | Delete a paper and all its data    |

### Analysis
| Method | Endpoint                      | Description                              |
|--------|-------------------------------|------------------------------------------|
| POST   | /analysis/{paper_id}          | Run full analysis (summary+insights+topics) |
| GET    | /analysis/{paper_id}          | Fetch cached analysis results            |
| POST   | /analysis/{paper_id}/summary  | Re-run only summarization                |
| POST   | /analysis/{paper_id}/insights | Re-run only insight extraction           |
| POST   | /analysis/{paper_id}/topics   | Re-run only topic classification         |
| POST   | /analysis/compare             | Compare 2+ papers (trends, gaps)         |

### Export
| Method | Endpoint                         | Description              |
|--------|----------------------------------|--------------------------|
| GET    | /export/{paper_id}?format=pdf    | Export results as PDF    |
| GET    | /export/{paper_id}?format=csv    | Export results as CSV    |

---

## Database Schema

```sql
-- Users (optional auth layer)
CREATE TABLE users (
    user_id     TEXT PRIMARY KEY,
    name        TEXT,
    role        TEXT DEFAULT 'researcher'
);

-- Uploaded papers
CREATE TABLE research_papers (
    paper_id        TEXT PRIMARY KEY,       -- UUID
    user_id         TEXT REFERENCES users,
    title           TEXT,
    filename        TEXT,
    file_path       TEXT,
    raw_text        TEXT,
    sections_json   TEXT,                   -- {"abstract": "...", "methods": "..."}
    page_count      INTEGER,
    uploaded_at     DATETIME DEFAULT NOW(),
    status          TEXT DEFAULT 'uploaded' -- uploaded | analyzed | error
);

-- Summaries
CREATE TABLE summaries (
    summary_id      TEXT PRIMARY KEY,
    paper_id        TEXT REFERENCES research_papers,
    summary_type    TEXT,                   -- 'full' | 'abstract' | 'methods' | 'results'
    summary_text    TEXT,
    created_at      DATETIME DEFAULT NOW()
);

-- Insights & Keywords
CREATE TABLE insights (
    insight_id      TEXT PRIMARY KEY,
    paper_id        TEXT REFERENCES research_papers,
    keyword         TEXT,
    category        TEXT,                   -- 'methodology' | 'finding' | 'tool' | 'concept'
    relevance_score REAL,
    context         TEXT,
    created_at      DATETIME DEFAULT NOW()
);

-- Topics & Domains
CREATE TABLE topics (
    topic_id        TEXT PRIMARY KEY,
    paper_id        TEXT REFERENCES research_papers,
    domain          TEXT,                   -- e.g. 'Machine Learning'
    sub_domain      TEXT,                   -- e.g. 'Computer Vision'
    confidence      REAL,
    created_at      DATETIME DEFAULT NOW()
);

-- Research Gaps & Trends (multi-paper)
CREATE TABLE comparisons (
    comparison_id   TEXT PRIMARY KEY,
    paper_ids       TEXT,                   -- JSON array of paper_ids
    gaps            TEXT,                   -- JSON: identified research gaps
    trends          TEXT,                   -- JSON: common trends
    similarities    TEXT,                   -- JSON: overlap summary
    created_at      DATETIME DEFAULT NOW()
);
```

---

## Claude API Usage Per Service

| Service               | Prompt Goal                                              | Output Format     |
|-----------------------|----------------------------------------------------------|-------------------|
| `summarizer.py`       | Summarize each section + produce 1 overall summary       | JSON              |
| `insight_extractor.py`| Extract keywords, methodologies, findings, tools used    | JSON array        |
| `topic_classifier.py` | Classify into domain/sub-domain with confidence scores   | JSON              |
| `trend_analyzer.py`   | Given N paper summaries, identify gaps/trends/overlaps   | JSON              |

All Claude calls return **structured JSON** parsed server-side before DB storage.

---

## Implementation Milestones

### Week 1–2: Foundation
- [x] Project scaffolding (folders, config, DB setup)
- [ ] `pdf_parser.py` — extract text, detect sections
- [ ] `POST /papers/upload` endpoint
- [ ] Streamlit: Upload page

### Week 3–4: AI Summarization
- [ ] `summarizer.py` with Claude API
- [ ] `POST /analysis/{id}/summary` endpoint
- [ ] Streamlit: Summary view page

### Week 5–6: Insights & Classification
- [ ] `insight_extractor.py` with Claude API
- [ ] `topic_classifier.py` with Claude API
- [ ] Full `POST /analysis/{id}` endpoint
- [ ] Streamlit: Insights + keyword cloud + topic tags

### Week 7–8: Compare, Export & Polish
- [ ] `trend_analyzer.py` for multi-paper comparison
- [ ] `POST /analysis/compare` endpoint
- [ ] Export endpoints (PDF/CSV)
- [ ] Streamlit: Compare & Export pages
- [ ] End-to-end testing

---

## Key Libraries

### Backend
```
fastapi
uvicorn
pdfplumber          # PDF text extraction
anthropic           # Claude API
sqlalchemy          # ORM
alembic             # DB migrations
python-multipart    # File uploads
python-dotenv       # .env support
reportlab           # PDF export
pandas              # CSV export
```

### Frontend (Streamlit)
```
streamlit
requests            # HTTP calls to FastAPI
wordcloud           # Keyword cloud visualization
matplotlib          # Charts
pandas              # Data tables
```

---

## Environment Variables (.env)

```env
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=sqlite:///./paperiq.db
UPLOAD_DIR=./uploads
EXPORT_DIR=./exports
MAX_FILE_SIZE_MB=20
CLAUDE_MODEL=claude-sonnet-4-20250514
```
