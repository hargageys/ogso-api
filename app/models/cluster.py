from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ARRAY, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str | None] = mapped_column(String(255))
    top_terms: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    paper_count: Mapped[int] = mapped_column(Integer, default=0)
    total_citations: Mapped[int] = mapped_column(Integer, default=0)
    somali_author_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    recent_count: Mapped[int] = mapped_column(Integer, default=0)
    gap_score: Mapped[int] = mapped_column(Integer, default=0)
    decade_trend: Mapped[dict | None] = mapped_column(JSON)
    last_computed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    papers: Mapped[list["Paper"]] = relationship(back_populates="cluster")


from app.models.paper import Paper  # noqa: E402
