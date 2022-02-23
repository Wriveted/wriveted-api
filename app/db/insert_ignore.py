from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import Insert

"""
When imported, automatically make all inserts not fail on duplicate keys.
Thanks to atellier: https://github.com/sqlalchemy/sqlalchemy/issues/5374
"""


@compiles(Insert, "mysql")
def mysql_insert_ignore(insert, compiler, **kw):
    return compiler.visit_insert(insert.prefix_with("IGNORE"), **kw)


# ----- didn't end up using this. but may come in handy if further optimisations are required. -----

# takes advantage of the @compiles directive to override the default sqlalchemy statement generation. 
# this helps to optimise bulk inserts when conflicts are expected.
#
# the main goal was to avoid integrity errors when trying to add an existing isbn, which is expected to be common.
# alternatives included:
# 1) querying a list of all existing editions to store in memory for local comparison 
# (which could get dire as the total collection grows to tens, hundreds of thousands)
# 2) comparing the db with the isbn at each iteration (which has horrific performance)
# 3) avoiding bulk inserts and try/excepting each db.commit (again, dreadfully slow)
# 4) using raw sql strings to perform the inserts with ignores (might be optimal speed-wise,
# but functionality divorced from the ORM could possibly be harder to maintain)
@compiles(Insert, "postgresql")
def postgresql_on_conflict_do_nothing(insert, compiler, **kw):
    statement = compiler.visit_insert(insert, **kw)
    # IF we have a "RETURNING" clause, we must insert before it
    returning_position = statement.find("RETURNING")
    if returning_position >= 0:
        return (
            statement[:returning_position]
            + "ON CONFLICT DO NOTHING "
            + statement[returning_position:]
        )
    else:
        return statement + " ON CONFLICT DO NOTHING"