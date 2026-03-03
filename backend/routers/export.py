import io
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models.paper import ResearchPaper
from backend.models.summary import Summary
from backend.models.insight import Insight
from backend.models.topic import Topic, Gap

router = APIRouter(prefix="/papers", tags=["export"])


@router.get("/{paper_id}/export")
async def export_paper(
    paper_id: int,
    format: str = "pdf",
    db: AsyncSession = Depends(get_db),
):
    paper = await db.get(ResearchPaper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found.")

    result = await db.execute(select(Summary).where(Summary.paper_id == paper_id))
    summary = result.scalar_one_or_none()

    result = await db.execute(select(Insight).where(Insight.paper_id == paper_id))
    insights = result.scalars().all()

    result = await db.execute(select(Topic).where(Topic.paper_id == paper_id))
    topics = result.scalars().all()

    result = await db.execute(select(Gap).where(Gap.paper_id == paper_id))
    gaps = result.scalars().all()

    if format == "csv":
        return _export_csv(paper, summary, insights, topics, gaps)
    else:
        return _export_pdf(paper, summary, insights, topics, gaps)


def _export_csv(paper, summary, insights, topics, gaps):
    import csv
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["PaperIQ Export"])
    writer.writerow(["Title", paper.title or "Untitled"])
    writer.writerow(["File", paper.filename])
    writer.writerow([])

    if summary:
        writer.writerow(["SUMMARY"])
        writer.writerow(["Full Summary", summary.full_summary or ""])
        writer.writerow([])

    if insights:
        writer.writerow(["INSIGHTS"])
        writer.writerow(["Keyword", "Category", "Score"])
        for i in insights:
            writer.writerow([i.keyword, i.category, i.score])
        writer.writerow([])

    if topics:
        writer.writerow(["TOPICS"])
        writer.writerow(["Domain", "Sub-Domain", "Confidence"])
        for t in topics:
            writer.writerow([t.domain, t.sub_domain, t.confidence])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=paper_{paper.paper_id}_insights.csv"},
    )


def _export_pdf(paper, summary, insights, topics, gaps):
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"PaperIQ Report: {paper.title or 'Untitled'}", styles["Title"]))
    story.append(Spacer(1, 12))

    if summary and summary.full_summary:
        story.append(Paragraph("Summary", styles["Heading1"]))
        story.append(Paragraph(summary.full_summary, styles["Normal"]))
        story.append(Spacer(1, 12))

    if insights:
        story.append(Paragraph("Key Insights", styles["Heading1"]))
        for ins in insights[:15]:
            story.append(Paragraph(f"• [{ins.category}] {ins.keyword}", styles["Normal"]))
        story.append(Spacer(1, 12))

    if topics:
        story.append(Paragraph("Topics", styles["Heading1"]))
        for t in topics:
            story.append(Paragraph(f"• {t.domain} > {t.sub_domain or 'N/A'}", styles["Normal"]))
        story.append(Spacer(1, 12))

    if gaps:
        story.append(Paragraph("Research Gaps", styles["Heading1"]))
        for g in gaps:
            story.append(Paragraph(f"• [{g.priority}] {g.gap_text}", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=paper_{paper.paper_id}_report.pdf"},
    )
