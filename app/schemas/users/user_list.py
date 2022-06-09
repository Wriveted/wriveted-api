from app.schemas.pagination import PaginatedResponse
from app.schemas.users import UserBrief


class UserListsResponse(PaginatedResponse):
    data: list[UserBrief]
