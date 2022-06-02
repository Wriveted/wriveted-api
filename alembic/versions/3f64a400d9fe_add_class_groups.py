"""add class groups

Revision ID: 3f64a400d9fe
Revises: 35112b0ae03e
Create Date: 2022-06-02 21:49:17.901142

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3f64a400d9fe'
down_revision = '35112b0ae03e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('class_groups',
    sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('school_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.Column('join_code', sa.String(length=6), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['school_id'], ['schools.wriveted_identifier'], name='fk_class_groups_school'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_class_groups_school_id'), 'class_groups', ['school_id'], unique=False)
    op.alter_column('readers', 'username',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.add_column('students', sa.Column('class_group_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_students_class_group_id'), 'students', ['class_group_id'], unique=False)
    op.create_foreign_key('fk_student_class_group', 'students', 'class_groups', ['class_group_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('fk_student_class_group', 'students', type_='foreignkey')
    op.drop_index(op.f('ix_students_class_group_id'), table_name='students')
    op.drop_column('students', 'class_group_id')
    op.alter_column('readers', 'username',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.drop_index(op.f('ix_class_groups_school_id'), table_name='class_groups')
    op.drop_table('class_groups')
    # ### end Alembic commands ###
