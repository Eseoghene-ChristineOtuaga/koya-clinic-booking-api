"""Initial clinic booking schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-02
"""
from alembic import op
import sqlalchemy as sa

SCHEMA = "koya_clinic"

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slots",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("provider", sa.String(255), nullable=False),
        sa.Column("start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('"end" > start', name="ck_slots_end_after_start"),
        schema=SCHEMA,
    )
    op.create_index("ix_slots_start", "slots", ["start", "id"], schema=SCHEMA)
    op.create_table(
        "bookings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slot_id", sa.String(255), sa.ForeignKey(f"{SCHEMA}.slots.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('confirmed', 'cancelled')", name="ck_bookings_status"),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_one_confirmed_booking_per_slot", "bookings", ["slot_id"],
        unique=True, postgresql_where=sa.text("status = 'confirmed'"), schema=SCHEMA,
    )
    op.create_index("ix_bookings_email_created", "bookings", ["email", "created_at", "id"], schema=SCHEMA)
    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema=SCHEMA,
    )
    op.create_table(
        "booking_attempts",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_attempts_email_time", "booking_attempts", ["email", "attempted_at"], schema=SCHEMA)
    op.create_table(
        "rate_limit_locks",
        sa.Column("email", sa.String(320), primary_key=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("rate_limit_locks", schema=SCHEMA)
    op.drop_index("ix_attempts_email_time", table_name="booking_attempts", schema=SCHEMA)
    op.drop_table("booking_attempts", schema=SCHEMA)
    op.drop_table("idempotency_keys", schema=SCHEMA)
    op.drop_index("ix_bookings_email_created", table_name="bookings", schema=SCHEMA)
    op.drop_index("uq_one_confirmed_booking_per_slot", table_name="bookings", schema=SCHEMA)
    op.drop_table("bookings", schema=SCHEMA)
    op.drop_index("ix_slots_start", table_name="slots", schema=SCHEMA)
    op.drop_table("slots", schema=SCHEMA)
