"""initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("admin","researcher","organisation","university","ministry", name="userrole"), nullable=False),
        sa.Column("status", sa.Enum("pending","active","suspended", name="userstatus"), default="pending"),
        sa.Column("full_name", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime(timezone=True)),
        sa.Column("email_verified", sa.Boolean, default=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "clusters",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("label", sa.String(255)),
        sa.Column("top_terms", postgresql.ARRAY(sa.Text)),
        sa.Column("paper_count", sa.Integer, default=0),
        sa.Column("total_citations", sa.Integer, default=0),
        sa.Column("somali_author_ratio", sa.Float, default=0.0),
        sa.Column("recent_count", sa.Integer, default=0),
        sa.Column("gap_score", sa.Integer, default=0),
        sa.Column("decade_trend", postgresql.JSON),
        sa.Column("last_computed", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "papers",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("authors", postgresql.JSON),
        sa.Column("year", sa.Integer),
        sa.Column("abstract", sa.Text),
        sa.Column("full_text", sa.Text),
        sa.Column("source", sa.String(100)),
        sa.Column("url", sa.String(512)),
        sa.Column("doi", sa.String(255), unique=True),
        sa.Column("institution", sa.Text),
        sa.Column("category", sa.String(100)),
        sa.Column("doc_type", sa.String(100)),
        sa.Column("cluster_id", sa.Integer, sa.ForeignKey("clusters.id")),
        sa.Column("embedding", sa.Text),  # placeholder; vector type set by raw SQL below
        sa.Column("somali_authored", sa.Boolean, default=False),
        sa.Column("citations", sa.Integer, default=0),
        sa.Column("language", sa.String(10), default="en"),
        sa.Column("status", sa.Enum("pending_embed","embedded","published","rejected", name="paperstatus"), default="pending_embed"),
        sa.Column("ogso_type", sa.Enum("archive","original", name="ogso_type"), default="archive"),
        sa.Column("scraped_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Replace placeholder with real vector column
    op.execute("ALTER TABLE papers DROP COLUMN embedding")
    op.execute("ALTER TABLE papers ADD COLUMN embedding vector(384)")

    op.create_table(
        "researcher_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), unique=True),
        sa.Column("display_name", sa.String(255)),
        sa.Column("bio", sa.Text),
        sa.Column("photo_url", sa.String(512)),
        sa.Column("orcid", sa.String(50), unique=True),
        sa.Column("title", sa.String(50)),
        sa.Column("position", sa.String(255)),
        sa.Column("institution", sa.String(255)),
        sa.Column("country", sa.String(100)),
        sa.Column("city", sa.String(100)),
        sa.Column("website", sa.String(512)),
        sa.Column("twitter", sa.String(255)),
        sa.Column("linkedin", sa.String(512)),
        sa.Column("research_interests", postgresql.ARRAY(sa.Text)),
        sa.Column("fields", postgresql.ARRAY(sa.Text)),
        sa.Column("inside_somalia", sa.Boolean, default=False),
        sa.Column("somali_diaspora", sa.Boolean, default=False),
        sa.Column("verified", sa.Boolean, default=False),
        sa.Column("paper_count", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "organisation_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("org_type", sa.Enum("university","ngo","ministry","think_tank","private_sector","international_org","other", name="orgtype")),
        sa.Column("description", sa.Text),
        sa.Column("logo_url", sa.String(512)),
        sa.Column("website", sa.String(512)),
        sa.Column("country", sa.String(100)),
        sa.Column("city", sa.String(100)),
        sa.Column("founded_year", sa.Integer),
        sa.Column("somali_entity", sa.Boolean, default=False),
        sa.Column("focus_areas", postgresql.ARRAY(sa.Text)),
        sa.Column("email_public", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("linkedin", sa.String(512)),
        sa.Column("twitter", sa.String(255)),
        sa.Column("partner", sa.Boolean, default=False),
        sa.Column("verified", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "author_paper_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("researcher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("researcher_profiles.id")),
        sa.Column("paper_id", sa.String(255), sa.ForeignKey("papers.id")),
        sa.Column("claimed", sa.Boolean, default=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("verified", sa.Boolean, default=False),
    )

    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("paper_id", sa.String(255), sa.ForeignKey("papers.id")),
        sa.Column("title", sa.Text),
        sa.Column("abstract", sa.Text),
        sa.Column("authors", postgresql.JSON),
        sa.Column("year", sa.String(10)),
        sa.Column("doi", sa.String(255)),
        sa.Column("file_url", sa.String(512)),
        sa.Column("status", sa.Enum("draft","submitted","under_review","revision_requested","approved","rejected", name="submissionstatus"), default="draft"),
        sa.Column("reviewer_notes", sa.Text),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "policy_briefs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("query", sa.Text),
        sa.Column("source_paper_ids", postgresql.ARRAY(sa.String(255))),
        sa.Column("status", sa.Enum("queued","processing","complete","failed", name="briefstatus"), default="queued"),
        sa.Column("content_english", sa.Text),
        sa.Column("content_somali", sa.Text),
        sa.Column("video_script", sa.Text),
        sa.Column("paper_count", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(100)),
        sa.Column("target_type", sa.String(50)),
        sa.Column("target_id", sa.String(255)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Full-text search index on papers
    op.execute("""
        CREATE INDEX papers_fts_idx ON papers
        USING GIN (to_tsvector('english', coalesce(title,'') || ' ' || coalesce(abstract,'')))
    """)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("policy_briefs")
    op.drop_table("submissions")
    op.drop_table("author_paper_links")
    op.drop_table("organisation_profiles")
    op.drop_table("researcher_profiles")
    op.drop_table("papers")
    op.drop_table("clusters")
    op.drop_table("users")
    for t in ["userrole","userstatus","paperstatus","ogso_type","orgtype","submissionstatus","briefstatus"]:
        op.execute(f"DROP TYPE IF EXISTS {t}")
