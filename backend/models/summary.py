from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Summary(Base):
    __tablename__ = "summaries"

    summary_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("research_papers.paper_id"))
    full_summary: Mapped[str | None] = mapped_column(Text)
    abstract_sum: Mapped[str | None] = mapped_column(Text)
    intro_sum: Mapped[str | None] = mapped_column(Text)
    method_sum: Mapped[str | None] = mapped_column(Text)
    results_sum: Mapped[str | None] = mapped_column(Text)
    conclusion_sum: Mapped[str | None] = mapped_column(Text)

    paper: Mapped["ResearchPaper"] = relationship(back_populates="summaries")
