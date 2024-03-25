"""add to label origin enum

Revision ID: 621df72d3942
Revises: c3a621ca192a
Create Date: 2023-03-24 14:05:22.961238

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "621df72d3942"
down_revision = "c3a621ca192a"
branch_labels = None
depends_on = None

old = sa.Enum(
    "HUMAN",
    "PREDICTED_NIELSEN",
    "NIELSEN_CBMC",
    "NIELSEN_BIC",
    "NIELSEN_THEMA",
    "NIELSEN_IA",
    "NIELSEN_RA",
    "CLUSTER_RELEVANCE",
    "CLUSTER_ZAINAB",
    "OTHER",
    name="labelorigin",
)
new = sa.Enum(
    "HUMAN",
    "GPT4",  # new key
    "PREDICTED_NIELSEN",
    "NIELSEN_CBMC",
    "NIELSEN_BIC",
    "NIELSEN_THEMA",
    "NIELSEN_IA",
    "NIELSEN_RA",
    "CLUSTER_RELEVANCE",
    "CLUSTER_ZAINAB",
    "OTHER",
    name="labelorigin",
)


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("ALTER TYPE labelorigin RENAME TO labelorigin_old")
    op.execute(
        "CREATE TYPE labelorigin AS ENUM('HUMAN', 'GPT4', 'PREDICTED_NIELSEN', 'NIELSEN_CBMC', 'NIELSEN_BIC', 'NIELSEN_THEMA', 'NIELSEN_IA', 'NIELSEN_RA', 'CLUSTER_RELEVANCE', 'CLUSTER_ZAINAB', 'OTHER')"
    )
    op.alter_column(
        "labelsets",
        "age_origin",
        type_=new,
        postgresql_using="age_origin::text::labelorigin",
    )
    op.alter_column(
        "labelsets",
        "reading_ability_origin",
        type_=new,
        postgresql_using="reading_ability_origin::text::labelorigin",
    )
    op.alter_column(
        "labelsets",
        "summary_origin",
        type_=new,
        postgresql_using="summary_origin::text::labelorigin",
    )
    op.alter_column(
        "labelsets",
        "hue_origin",
        type_=new,
        postgresql_using="hue_origin::text::labelorigin",
    )
    op.alter_column(
        "labelsets",
        "recommend_status_origin",
        type_=new,
        postgresql_using="recommend_status_origin::text::labelorigin",
    )
    op.execute("DROP TYPE labelorigin_old")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("ALTER TYPE labelorigin RENAME TO labelorigin_old")
    op.execute(
        "CREATE TYPE labelorigin AS ENUM('HUMAN', 'PREDICTED_NIELSEN', 'CLUSTER_RELEVANCE', 'CLUSTER_ZAINAB', 'OTHER')"
    )
    op.alter_column(
        "labelsets",
        "age_origin",
        type_=old,
        postgresql_using="age_origin::text::labelorigin",
    )
    op.alter_column(
        "labelsets",
        "reading_ability_origin",
        type_=old,
        postgresql_using="reading_ability_origin::text::labelorigin",
    )
    op.alter_column(
        "labelsets",
        "summary_origin",
        type_=old,
        postgresql_using="summary_origin::text::text::labelorigin",
    )
    op.alter_column(
        "labelsets",
        "hue_origin",
        type_=old,
        postgresql_using="hue_origin::text::labelorigin",
    )
    op.alter_column(
        "labelsets",
        "recommend_status_origin",
        type_=old,
        postgresql_using="recommend_status_origin::text::labelorigin",
    )
    op.execute("DROP TYPE labelorigin_old")
    # ### end Alembic commands ###
