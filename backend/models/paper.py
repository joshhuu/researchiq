from sqlalchemy import Integer, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class ResearchPaper(Base):
    __tablename__ = "research_papers"

    paper_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column(String(500))
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    extracted_text: Mapped[str | None] = mapped_column(Text)
    sections: Mapped[str | None] = mapped_column(Text)  # JSON string of section dict
    page_count: Mapped[int | None] = mapped_column(Integer)
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(50), default="uploaded")  # uploaded | analyzed | error

    summaries: Mapped[list["Summary"]] = relationship(back_populates="paper", cascade="all, delete")
    insights: Mapped[list["Insight"]] = relationship(back_populates="paper", cascade="all, delete")
    topics: Mapped[list["Topic"]] = relationship(back_populates="paper", cascade="all, delete")
    gaps: Mapped[list["Gap"]] = relationship(back_populates="paper", cascade="all, delete")
