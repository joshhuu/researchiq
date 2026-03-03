import uuid
import json

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from db.session import get_db
from models.models import ResearchPaper, Summary, Insight, Topic, Comparison
from schemas.schemas import AnalysisResult, CompareRequest, CompareResult
from services.summarizer import summarize_all_sections
from services.insight_extractor import extract_insights
from services.topic_classifier import classify_topics
from services.trend_analyzer import analyze_trends

router = APIRouter()


def _get_paper_or_404(paper_id: str, db: Session) -> ResearchPaper:
    paper = db.query(ResearchPaper).filter(ResearchPaper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return paper


@router.post("/{paper_id}", response_model=AnalysisResult)
def run_full_analysis(paper_id: str, db: Session = Depends(get_db)):
    """Run full AI analysis: summarization + insights + topic classification."""
    paper = _get_paper_or_404(paper_id, db)
    sections = json.loads(paper.sections_json) if paper.sections_json else {"full_text": paper.raw_text}

    # Clear existing analysis
    db.query(Summary).filter(Summary.paper_id == paper_id).delete()
    db.query(Insight).filter(Insight.paper_id == paper_id).delete()
    db.query(Topic).filter(Topic.paper_id == paper_id).delete()

    try:
        # 1. Summaries
        summaries_data = summarize_all_sections(sections)
        summaries = []
        for s in summaries_data:
            obj = Summary(
                summary_id=str(uuid.uuid4()),
                paper_id=paper_id,
                summary_type=s["type"],
                summary_text=s["text"],
            )
            db.add(obj)
            summaries.append(obj)

        # 2. Insights
        insights_data = extract_insights(paper.raw_text)
        insights = []
        for item in insights_data:
            obj = Insight(
                insight_id=str(uuid.uuid4()),
                paper_id=paper_id,
                keyword=item.get("keyword", ""),
                category=item.get("category", "concept"),
                relevance_score=float(item.get("relevance_score", 1.0)),
                context=item.get("context", ""),
            )
            db.add(obj)
            insights.append(obj)

        # 3. Topics
        topics_data = classify_topics(paper.raw_text)
        topics = []
        for item in topics_data:
            obj = Topic(
                topic_id=str(uuid.uuid4()),
                paper_id=paper_id,
                domain=item.get("domain", ""),
                sub_domain=item.get("sub_domain", ""),
                confidence=float(item.get("confidence", 1.0)),
            )
            db.add(obj)
            topics.append(obj)

        paper.status = "analyzed"
        db.commit()

        return AnalysisResult(
            paper_id=paper_id,
            status="analyzed",
            summaries=summaries,
            insights=insights,
            topics=topics,
        )

    except Exception as e:
        paper.status = "error"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/{paper_id}", response_model=AnalysisResult)
def get_analysis(paper_id: str, db: Session = Depends(get_db)):
    """Fetch cached analysis results for a paper."""
    paper = _get_paper_or_404(paper_id, db)
    return AnalysisResult(
        paper_id=paper_id,
        status=paper.status,
        summaries=paper.summaries,
        insights=paper.insights,
        topics=paper.topics,
    )


@router.post("/compare/run", response_model=CompareResult)
def compare_papers(req: CompareRequest, db: Session = Depends(get_db)):
    """Compare 2+ papers to find trends, gaps, and similarities."""
    if len(req.paper_ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 paper IDs to compare.")

    papers_input = []
    for pid in req.paper_ids:
        paper = _get_paper_or_404(pid, db)
        full_summary = next(
            (s.summary_text for s in paper.summaries if s.summary_type == "full"), ""
        )
        keywords = [i.keyword for i in paper.insights[:20]]
        papers_input.append({
            "title": paper.title,
            "full_summary": full_summary,
            "keywords": keywords,
        })

    try:
        result = analyze_trends(papers_input)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")

    comparison = Comparison(
        comparison_id=str(uuid.uuid4()),
        paper_ids=json.dumps(req.paper_ids),
        gaps=json.dumps(result.get("gaps", [])),
        trends=json.dumps(result.get("trends", [])),
        similarities=json.dumps(result.get("similarities", [])),
    )
    db.add(comparison)
    db.commit()

    return CompareResult(
        comparison_id=comparison.comparison_id,
        paper_ids=req.paper_ids,
        gaps=result.get("gaps"),
        trends=result.get("trends"),
        similarities=result.get("similarities"),
    )
