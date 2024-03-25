"""noop

Revision ID: 671ac58d1a3d
Revises: 621df72d3942
Create Date: 2023-03-30 15:33:00.162016

"""

from alembic_utils.pg_extension import PGExtension

from alembic import op

# revision identifiers, used by Alembic.
revision = "671ac58d1a3d"
down_revision = "621df72d3942"
branch_labels = None
depends_on = None


def downgrade():
    public_fuzzystrmatch = PGExtension(schema="public", signature="fuzzystrmatch")
    op.drop_entity(public_fuzzystrmatch)


def upgrade():
    public_fuzzystrmatch = PGExtension(schema="public", signature="fuzzystrmatch")
    op.create_entity(public_fuzzystrmatch)
