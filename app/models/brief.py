import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Enum, Integer, ARRAY, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class BriefStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class PolicyBrief(Base):
    __tablename__ = "policy_briefs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    query: Mapped[str] = mapped_column(Text)
    source_paper_ids: Mapped[list[str] | None] = mapped_column(ARRAY(String(255)))
    status: Mapped[BriefStatus] = mapped_column(Enum(BriefStatus), default=BriefStatus.queued)
    content_english: Mapped[str | None] = mapped_column(Text)
    content_somali: Mapped[str | None] = mapped_column(Text)
    video_script: Mapped[str | None] = mapped_column(Text)
    paper_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    requester: Mapped["User"] = relationship("User", foreign_keys=[requested_by])


from app.models.user import User  # noqa: E402
