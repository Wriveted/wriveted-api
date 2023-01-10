"""add collection update trigger

Revision ID: 97cd77cff343
Revises: 1e26ba3d64a3
Create Date: 2023-01-10 14:19:39.499659

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "97cd77cff343"
down_revision = "1e26ba3d64a3"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute(
        """
        CREATE TRIGGER update_collections_trigger
        AFTER INSERT OR UPDATE ON collection_items
        FOR EACH ROW
        EXECUTE PROCEDURE update_collections_function();
    """
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("DROP TRIGGER update_collections_trigger ON collection_items")
    # ### end Alembic commands ###
