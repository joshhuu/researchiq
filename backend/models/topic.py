from sqlalchemy import Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Topic(Base):
    __tablename__ = "topics"

    topic_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("research_papers.paper_id"))
    domain: Mapped[str] = mapped_column(String(200))
    sub_domain: Mapped[str | None] = mapped_column(String(200))
    confidence: Mapped[float | None] = mapped_column(Float)

    paper: Mapped["ResearchPaper"] = relationship(back_populates="topics")


class Gap(Base):
    __tablename__ = "gaps"

    gap_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("research_papers.paper_id"))
    gap_text: Mapped[str] = mapped_column(Text)
    priority: Mapped[str | None] = mapped_column(String(20))  # high | medium | low

    paper: Mapped["ResearchPaper"] = relationship(back_populates="gaps")
