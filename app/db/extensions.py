from alembic_utils.pg_extension import PGExtension

# pg_cron_ex = PGExtension(schema="pg_catalog", signature="pg_cron")
pgvector_ex = PGExtension(schema="public", signature="vector")
