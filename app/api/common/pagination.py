from fastapi import Query


class PaginationOrderingError(Exception):
    """Raised when an invalid pagination ordering is specified"""


class PaginatedQueryParams:
    def __init__(
        self,
        skip: int = Query(0, description="Skip this many items"),
        limit: int = Query(100, description="Maximum number of items to return"),
        order_by: str = Query(None, description="Column name to order by"),
        order_by_table: str = Query(
            None,
            description="Optional table name containing the column to order by, for the case of joined loads",
        ),
        order_direction: str = Query(
            "asc",
            description="Order direction. Ignored if no order_by is specified",
            regex="(?i)^(asc|desc)$",
        ),
    ):
        self.skip = skip
        self.limit = limit
        self.order_by = order_by
        self.order_by_table = order_by_table
        self.order_direction = order_direction if order_by else None

    def __repr__(self):
        return f"<Pagination skip={self.skip}, limit={self.limit}, order_by={self.order_by}, order_by_table={self.order_by_table}, order_direction={self.order_direction}>"

    def to_dict(self):
        return {
            "skip": self.skip,
            "limit": self.limit,
            "order_by": self.order_by,
            "order_by_table": self.order_by_table,
            "order_direction": self.order_direction,
        }
