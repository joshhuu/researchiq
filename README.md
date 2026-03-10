# PaperIQ — AI Research Paper Analyzer

PaperIQ is a comprehensive AI-powered research paper analysis tool built with a FastAPI backend and a Streamlit frontend. It leverages Anthropic's Claude API to automatically extract text from PDFs, detect sections, and generate deep insights, summaries, and topic classifications.

## 🌟 Features

* **Intelligent Summarization**: Context-aware summaries for each section (Abstract, Intro, Methods, Results, Conclusion) and an overall paper summary.
* **Insight & Keyword Extraction**: Extracts key methodologies, findings, tools, and concepts with an assigned relevance score.
* **Topic Classification**: Automatically classifies papers into domains and sub-domains with confidence scores.
* **Cross-Paper Trend Analysis**: Compare multiple papers to identify research gaps, emerging trends, and overlaps.
* **Export Capabilities**: Export the analysis results into beautifully formatted PDFs or CSV files.
* **Interactive UI**: A sleek Streamlit application for uploading, analyzing, and visualizing data (including keyword clouds).

## 🛠️ Technology Stack

* **Backend**: FastAPI, Uvicorn, Python
* **Database**: SQLite (dev) with SQLAlchemy ORM and Alembic for migrations
* **AI Engine**: Anthropic Claude API (specifically `claude-3-5-sonnet-20241022` or equivalent)
* **PDF Processing**: `pdfplumber` for text extraction and section detection
* **Frontend**: Streamlit, with `wordcloud`, `matplotlib`, and `pandas` for visualization
* **Exporting**: `reportlab` (PDF) and `pandas` (CSV)

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have Python 3.9+ installed. You will also need an Anthropic API key.

### 2. Setup

Clone the repository and install the required dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy the example environment file and configure it:
```bash
cp .env.example .env
```
Open `.env` and configure your keys, specifically:
```env
ANTHROPIC_API_KEY=your-api-key-here
DATABASE_URL=sqlite:///./paperiq.db
CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

### 4. Running the Application

You need to run both the FastAPI backend and the Streamlit frontend. It is recommended to run these in separate terminal windows.

**Start the Backend (FastAPI):**
```bash
uvicorn backend.main:app --reload --port 8000
```
*The API will be accessible at http://localhost:8000*
*Interactive API documentation is available at http://localhost:8000/docs*

**Start the Frontend (Streamlit):**
```bash
streamlit run frontend/app.py
```
*The interactive UI will open at http://localhost:8501*

## 📖 API Usage Example

You can also interact directly with the FastAPI backend using standard HTTP clients like `curl`:

```bash
# Upload a paper
curl -X POST http://localhost:8000/papers/upload -F "file=@your_paper.pdf"

# Get summary (replace {paper_id} with the ID returned from upload)
curl http://localhost:8000/papers/{paper_id}/summary

# Get insights
curl http://localhost:8000/papers/{paper_id}/insights

# Export as PDF
curl "http://localhost:8000/export/{paper_id}?format=pdf" --output report.pdf
```

## 📁 Directory Structure
* `/backend` - FastAPI application, database models, and AI business logic
* `/frontend` - Streamlit application pages and UI components
* `/uploads` - Temporary storage for uploaded PDFs
* `/exports` - Generated exports (PDFs, CSVs)
