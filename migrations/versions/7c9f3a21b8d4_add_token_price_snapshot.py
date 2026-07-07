"""add token price snapshot

Revision ID: 7c9f3a21b8d4
Revises: fe9c613cafe5
Create Date: 2026-07-06 20:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7c9f3a21b8d4"
down_revision = "fe9c613cafe5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "token_price_snapshot",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=32), nullable=False),
        sa.Column("price_hive", sa.Float(), nullable=True),
        sa.Column("price_usd", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("token_price_snapshot", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_token_price_snapshot_created_at"),
            ["created_at"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_token_price_snapshot_token"),
            ["token"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("token_price_snapshot", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_token_price_snapshot_token"))
        batch_op.drop_index(batch_op.f("ix_token_price_snapshot_created_at"))

    op.drop_table("token_price_snapshot")
