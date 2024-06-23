from datetime import datetime
from typing import Any, Optional

from pydantic import UUID4, BaseModel, ConfigDict

from app.models.cms_content import ContentType
from app.schemas.pagination import PaginatedResponse


class CMSBrief(BaseModel):
    id: UUID4
    type: ContentType

    model_config = ConfigDict(from_attributes=True)


class CMSDetail(CMSBrief):
    created_at: datetime
    updated_at: datetime
    content: Optional[dict[str, Any]] = None


class CMSTypesResponse(PaginatedResponse):
    data: list[str]


class CMSContentResponse(PaginatedResponse):
    data: list[CMSDetail]
