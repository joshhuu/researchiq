from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db
from backend.routers import papers, summary, insights, topics, compare, export, analyze


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="PaperIQ API",
    description="AI-powered research paper analysis — summarization, insights, topic classification, and gap detection.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers.router)
app.include_router(summary.router)
app.include_router(insights.router)
app.include_router(topics.router)
app.include_router(compare.router)
app.include_router(export.router)
app.include_router(analyze.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "PaperIQ"}
