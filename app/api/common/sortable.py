from fastapi import Query


class SortableQueryParams:
    """Sort the query result

    ?sort=key1:asc,key2:desc,key3:asc

    """

    def __init__(
        self,
        sort: str = Query(
            None, description="Sort string", example="key1:asc,key2:desc,key3:asc"
        ),
    ):
        self.original = sort
        elements = sort.split(",")
        self.by = [element.split(":") for element in elements]

    def __repr__(self):
        return f"<Sort by={self.by} >"

    def to_dict(self):
        return {"by": self.by}
