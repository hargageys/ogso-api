import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Enum, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class SubmissionStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    under_review = "under_review"
    revision_requested = "revision_requested"
    approved = "approved"
    rejected = "rejected"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    submitted_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    paper_id: Mapped[str | None] = mapped_column(String(255), ForeignKey("papers.id"))
    title: Mapped[str | None] = mapped_column(Text)
    abstract: Mapped[str | None] = mapped_column(Text)
    authors: Mapped[dict | list | None] = mapped_column(JSON)
    year: Mapped[int | None] = mapped_column(String(10))
    doi: Mapped[str | None] = mapped_column(String(255))
    file_url: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[SubmissionStatus] = mapped_column(Enum(SubmissionStatus), default=SubmissionStatus.draft)
    reviewer_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submitter: Mapped["User"] = relationship("User", foreign_keys=[submitted_by])
    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewed_by])


from app.models.user import User  # noqa: E402
