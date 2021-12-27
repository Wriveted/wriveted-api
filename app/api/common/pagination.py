from fastapi import Query


class PaginatedQueryParams:
    def __init__(self,
                 skip: int = Query(0, description='Skip this many items'),
                 limit: int = Query(100, description='Maximum number of items to return')
                 ):
        self.skip = skip
        self.limit = limit

