from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base


class ResearchPaper(Base):
    __tablename__ = "research_papers"

    paper_id = Column(String, primary_key=True)
    title = Column(String, nullable=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    raw_text = Column(Text, nullable=True)
    sections_json = Column(Text, nullable=True)   # JSON string
    page_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="uploaded")   # uploaded | analyzed | error

    summaries = relationship("Summary", back_populates="paper", cascade="all, delete")
    insights = relationship("Insight", back_populates="paper", cascade="all, delete")
    topics = relationship("Topic", back_populates="paper", cascade="all, delete")


class Summary(Base):
    __tablename__ = "summaries"

    summary_id = Column(String, primary_key=True)
    paper_id = Column(String, ForeignKey("research_papers.paper_id"))
    summary_type = Column(String)   # full | abstract | methods | results
    summary_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    paper = relationship("ResearchPaper", back_populates="summaries")


class Insight(Base):
    __tablename__ = "insights"

    insight_id = Column(String, primary_key=True)
    paper_id = Column(String, ForeignKey("research_papers.paper_id"))
    keyword = Column(String)
    category = Column(String)        # methodology | finding | tool | concept
    relevance_score = Column(Float, default=1.0)
    context = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    paper = relationship("ResearchPaper", back_populates="insights")


class Topic(Base):
    __tablename__ = "topics"

    topic_id = Column(String, primary_key=True)
    paper_id = Column(String, ForeignKey("research_papers.paper_id"))
    domain = Column(String)
    sub_domain = Column(String, nullable=True)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    paper = relationship("ResearchPaper", back_populates="topics")


class Comparison(Base):
    __tablename__ = "comparisons"

    comparison_id = Column(String, primary_key=True)
    paper_ids = Column(Text)         # JSON array
    gaps = Column(Text, nullable=True)
    trends = Column(Text, nullable=True)
    similarities = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
