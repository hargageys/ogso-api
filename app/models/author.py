import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, ARRAY, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ResearcherProfile(Base):
    __tablename__ = "researcher_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    bio: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(String(512))
    orcid: Mapped[str | None] = mapped_column(String(50), unique=True)
    title: Mapped[str | None] = mapped_column(String(50))
    position: Mapped[str | None] = mapped_column(String(255))
    institution: Mapped[str | None] = mapped_column(String(255))
    country: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    website: Mapped[str | None] = mapped_column(String(512))
    twitter: Mapped[str | None] = mapped_column(String(255))
    linkedin: Mapped[str | None] = mapped_column(String(512))
    research_interests: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    fields: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    inside_somalia: Mapped[bool] = mapped_column(Boolean, default=False)
    somali_diaspora: Mapped[bool] = mapped_column(Boolean, default=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    paper_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="researcher_profile")
    paper_links: Mapped[list["AuthorPaperLink"]] = relationship(back_populates="researcher")


class AuthorPaperLink(Base):
    __tablename__ = "author_paper_links"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    researcher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("researcher_profiles.id"))
    paper_id: Mapped[str] = mapped_column(String(255), ForeignKey("papers.id"))
    claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    researcher: Mapped["ResearcherProfile"] = relationship(back_populates="paper_links")
    paper: Mapped["Paper"] = relationship(back_populates="author_links")


from app.models.user import User  # noqa: E402
from app.models.paper import Paper  # noqa: E402
