"""EXPLAIN any query.

Includes PostgreSQL EXPLAIN syntax.

SQLAlchemy 1.4 version.


"""
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import ClauseElement, Executable


class explain(Executable, ClauseElement):
    def __init__(self, stmt, analyze=False):
        self.statement = stmt
        self.analyze = analyze


@compiles(explain, "postgresql")
def pg_explain(element, compiler, **kw):
    text = "EXPLAIN "
    if element.analyze:
        text += "ANALYZE "
    text += compiler.process(element.statement, inherit_cache=False, **kw)

    return text
