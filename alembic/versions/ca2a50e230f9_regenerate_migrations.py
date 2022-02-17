"""Regenerate migrations

Revision ID: ca2a50e230f9
Revises: 9e2c2d162ac7
Create Date: 2021-12-27 17:22:58.622274

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ca2a50e230f9"
down_revision = "9e2c2d162ac7"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "authors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("last_name", sa.String(length=200), nullable=False),
        sa.Column("full_name", sa.String(length=400), nullable=False),
        sa.Column("info", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_authors_last_name"), "authors", ["last_name"], unique=False
    )
    op.create_table(
        "illustrators",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("first_name", sa.String(length=200), nullable=True),
        sa.Column("last_name", sa.String(length=200), nullable=False),
        sa.Column(
            "full_name",
            sa.String(length=400),
            sa.Computed(
                "COALESCE(first_name || ' ', '') || last_name",
            ),
            nullable=True,
        ),
        sa.Column("info", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "series",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("info", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_series_title"), "series", ["title"], unique=True)
    op.create_table(
        "works",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("type", sa.Enum("BOOK", "PODCAST", name="worktype"), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("info", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_works_title"), "works", ["title"], unique=False)
    op.create_table(
        "author_work_association",
        sa.Column("work_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_id"], ["authors.id"], name="fk_author_works_association_author_id"
        ),
        sa.ForeignKeyConstraint(
            ["work_id"], ["works.id"], name="fk_author_works_association_work_id"
        ),
        sa.PrimaryKeyConstraint("work_id", "author_id"),
    )
    op.create_table(
        "editions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("work_id", sa.Integer(), nullable=False),
        sa.Column("edition_title", sa.String(length=512), nullable=True),
        sa.Column("ISBN", sa.String(length=200), nullable=False),
        sa.Column("cover_url", sa.String(length=200), nullable=True),
        sa.Column("info", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["work_id"], ["works.id"], name="fk_editions_works"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_editions_ISBN"), "editions", ["ISBN"], unique=False)
    op.create_index(op.f("ix_editions_work_id"), "editions", ["work_id"], unique=False)
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("country_code", sa.String(length=3), nullable=True),
        sa.Column("official_identifier", sa.String(length=64), nullable=True),
        sa.Column(
            "state", sa.Enum("ACTIVE", "INACTIVE", name="schoolstate"), nullable=False
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("student_domain", sa.String(length=100), nullable=True),
        sa.Column("teacher_domain", sa.String(length=100), nullable=True),
        sa.Column("info", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["country_code"], ["countries.id"], name="fk_school_country"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "index_schools_by_country",
        "schools",
        ["country_code", "official_identifier"],
        unique=True,
    )
    op.create_index(
        op.f("ix_schools_country_code"), "schools", ["country_code"], unique=False
    )
    op.create_table(
        "series_works_association",
        sa.Column("series_id", sa.Integer(), nullable=False),
        sa.Column("work_id", sa.Integer(), nullable=False),
        sa.Column("primary_works", sa.Boolean(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["series_id"],
            ["series.id"],
            name="fk_illustrator_editions_assoc_illustrator_id",
        ),
        sa.ForeignKeyConstraint(
            ["work_id"], ["works.id"], name="fk_series_works_assoc_work_id"
        ),
        sa.PrimaryKeyConstraint("series_id", "work_id"),
    )
    op.create_table(
        "collection_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=True),
        sa.Column("work_id", sa.Integer(), nullable=True),
        sa.Column("edition_id", sa.Integer(), nullable=True),
        sa.Column("info", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["edition_id"], ["editions.id"], name="fk_collection_items_edition_id"
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"], name="fk_collection_items_school_id"
        ),
        sa.ForeignKeyConstraint(
            ["work_id"], ["works.id"], name="fk_collection_items_work_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_collection_items_school_id"),
        "collection_items",
        ["school_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_collection_items_work_id"),
        "collection_items",
        ["work_id"],
        unique=False,
    )
    op.create_table(
        "illustrator_edition_association",
        sa.Column("edition_id", sa.Integer(), nullable=False),
        sa.Column("illustrator_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["edition_id"],
            ["editions.id"],
            name="fk_illustrator_editions_assoc_edition_id",
        ),
        sa.ForeignKeyConstraint(
            ["illustrator_id"],
            ["illustrators.id"],
            name="fk_illustrator_editions_assoc_illustrator_id",
        ),
        sa.PrimaryKeyConstraint("edition_id", "illustrator_id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("illustrator_edition_association")
    op.drop_index(op.f("ix_collection_items_work_id"), table_name="collection_items")
    op.drop_index(op.f("ix_collection_items_school_id"), table_name="collection_items")
    op.drop_table("collection_items")
    op.drop_table("series_works_association")
    op.drop_index(op.f("ix_schools_country_code"), table_name="schools")
    op.drop_index("index_schools_by_country", table_name="schools")
    op.drop_table("schools")
    op.drop_index(op.f("ix_editions_work_id"), table_name="editions")
    op.drop_index(op.f("ix_editions_ISBN"), table_name="editions")
    op.drop_table("editions")
    op.drop_table("author_work_association")
    op.drop_index(op.f("ix_works_title"), table_name="works")
    op.drop_table("works")
    op.drop_index(op.f("ix_series_title"), table_name="series")
    op.drop_table("series")
    op.drop_table("illustrators")
    op.drop_index(op.f("ix_authors_last_name"), table_name="authors")
    op.drop_table("authors")
    op.execute("DROP TYPE worktype")
    op.execute("DROP TYPE schoolstate")

    # ### end Alembic commands ###
