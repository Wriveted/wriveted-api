"""index and updates to collectionitemactivity

Revision ID: 700693098e41
Revises: f7e6dc77ee86
Create Date: 2023-01-19 13:31:19.213145

"""

from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "700693098e41"
down_revision = "f7e6dc77ee86"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "collection_item_activity_log",
        "reader_id",
        existing_type=postgresql.UUID(),
        nullable=False,
    )
    op.create_index(
        "idx_collection_item_activity_log_timestamp_reader_id",
        "collection_item_activity_log",
        ["timestamp", "reader_id"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        "idx_collection_item_activity_log_timestamp_reader_id",
        table_name="collection_item_activity_log",
    )
    op.alter_column(
        "collection_item_activity_log",
        "reader_id",
        existing_type=postgresql.UUID(),
        nullable=True,
    )
    # ### end Alembic commands ###
