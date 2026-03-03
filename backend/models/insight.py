from sqlalchemy import Integer, String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Insight(Base):
    __tablename__ = "insights"

    insight_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("research_papers.paper_id"))
    keyword: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(50))  # keyword | objective | method | finding
    score: Mapped[float | None] = mapped_column(Float)

    paper: Mapped["ResearchPaper"] = relationship(back_populates="insights")
