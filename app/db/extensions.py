from alembic_utils.pg_extension import PGExtension

public_fuzzystrmatch = PGExtension(schema="public", signature="fuzzystrmatch")
