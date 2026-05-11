import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, ARRAY, Text, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class OrgType(str, enum.Enum):
    university = "university"
    ngo = "ngo"
    ministry = "ministry"
    think_tank = "think_tank"
    private_sector = "private_sector"
    international_org = "international_org"
    other = "other"


class OrganisationProfile(Base):
    __tablename__ = "organisation_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    org_type: Mapped[OrgType] = mapped_column(Enum(OrgType))
    description: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(512))
    website: Mapped[str | None] = mapped_column(String(512))
    country: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    founded_year: Mapped[int | None] = mapped_column(Integer)
    somali_entity: Mapped[bool] = mapped_column(Boolean, default=False)
    focus_areas: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    email_public: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    linkedin: Mapped[str | None] = mapped_column(String(512))
    twitter: Mapped[str | None] = mapped_column(String(255))
    partner: Mapped[bool] = mapped_column(Boolean, default=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="organisation_profile")


from app.models.user import User  # noqa: E402
