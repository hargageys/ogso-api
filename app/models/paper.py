from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, Enum, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.database import Base
import enum


class PaperStatus(str, enum.Enum):
    pending_embed = "pending_embed"
    embedded = "embedded"
    published = "published"
    rejected = "rejected"


class OgsoType(str, enum.Enum):
    archive = "archive"
    original = "original"


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[dict | list | None] = mapped_column(JSON)
    year: Mapped[int | None] = mapped_column(Integer)
    abstract: Mapped[str | None] = mapped_column(Text)
    full_text: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str | None] = mapped_column(String(512))
    doi: Mapped[str | None] = mapped_column(String(255), unique=True)
    institution: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    doc_type: Mapped[str | None] = mapped_column(String(100))
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("clusters.id"))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    somali_authored: Mapped[bool] = mapped_column(Boolean, default=False)
    citations: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str] = mapped_column(String(10), default="en")
    status: Mapped[PaperStatus] = mapped_column(Enum(PaperStatus, name="paperstatus"), default=PaperStatus.pending_embed)
    ogso_type: Mapped[OgsoType] = mapped_column(Enum(OgsoType, name="ogso_type"), default=OgsoType.archive)
    qdrant_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    cluster: Mapped["Cluster"] = relationship(back_populates="papers")
    author_links: Mapped[list["AuthorPaperLink"]] = relationship(back_populates="paper")


from app.models.cluster import Cluster  # noqa: E402
from app.models.author import AuthorPaperLink  # noqa: E402
