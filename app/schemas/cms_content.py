from app.schemas.pagination import PaginatedResponse


class CMSTypesResponse(PaginatedResponse):
    data: list[str]


class CMSContentResponse(PaginatedResponse):
    data: list[str]
