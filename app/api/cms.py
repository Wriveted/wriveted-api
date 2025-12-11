from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Security,
)
from sqlalchemy import func, or_, select
from starlette import status as status_module
from structlog import get_logger

from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.async_db_dep import DBSessionDep
from app.api.dependencies.security import (
    get_current_active_superuser_or_backend_service_account,
    get_current_active_user_or_service_account,
)
from app.models import ContentType, ServiceAccount
from app.models.cms import ChatTheme, FlowDefinition
from app.models.user import User, UserAccountType
from app.schemas.cms import (
    BulkContentDeleteRequest,
    BulkContentDeleteResponse,
    BulkContentRequest,
    BulkContentResponse,
    BulkContentUpdateRequest,
    BulkContentUpdateResponse,
    ChatThemeCreate,
    ChatThemeDetail,
    ChatThemeResponse,
    ChatThemeUpdate,
    ConnectionCreate,
    ConnectionDetail,
    ConnectionResponse,
    ContentCreate,
    ContentDetail,
    ContentResponse,
    ContentStatusUpdate,
    ContentUpdate,
    ContentVariantCreate,
    ContentVariantDetail,
    ContentVariantResponse,
    ContentVariantUpdate,
    FlowCloneRequest,
    FlowCreate,
    FlowDetail,
    FlowPublishRequest,
    FlowResponse,
    FlowUpdate,
    NodeCreate,
    NodeDetail,
    NodePositionUpdate,
    NodeResponse,
    NodeUpdate,
    VariantPerformanceUpdate,
)
from app.schemas.execution_trace import (
    SessionListResponse,
    SessionSummary,
    SessionTraceResponse,
    TraceStorageStats,
    TracingConfigRequest,
    TracingConfigResponse,
)
from app.schemas.pagination import Pagination
from app.services.cms_workflow import CMSWorkflowService
from app.services.exceptions import (
    CMSWorkflowError,
    FlowNotFoundError,
    FlowValidationError,
)
from app.services.execution_trace import execution_trace_service, trace_audit_service
from app.services.flow_service import FlowService
from app.services.trace_cleanup import trace_cleanup_service

logger = get_logger()


def get_cms_workflow_service() -> CMSWorkflowService:
    """Dependency function to get CMS Workflow Service instance."""
    return CMSWorkflowService()


def get_flow_service() -> FlowService:
    """Dependency function to get Flow Service instance."""
    return FlowService()


router = APIRouter(
    tags=["Digital Content Management System"],
    dependencies=[Security(get_current_active_superuser_or_backend_service_account)],
)

# Content Management Endpoints


@router.get("/content")
async def list_content(
    session: DBSessionDep,
    content_type: Optional[ContentType] = Query(
        None, description="Filter by content type"
    ),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    search: Optional[str] = Query(None, description="Full-text search"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    status: Optional[str] = Query(None, description="Filter by content status"),
    pagination: PaginatedQueryParams = Depends(),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """List content with filtering options using CMS Workflow Service."""
    try:
        # Convert ContentType enum to string for service layer
        content_type_str = content_type.value if content_type else None

        # Use CMS Workflow Service for business logic
        data, total_count = await cms_service.list_content_with_business_logic(
            session,
            content_type=content_type_str,
            tags=tags,
            search=search,
            active=active,
            status=status,
            skip=pagination.skip,
            limit=pagination.limit,
        )

        logger.info(
            "Retrieved content list via service",
            filters={
                "type": content_type_str,
                "tags": tags,
                "search": search,
                "active": active,
                "status": status,
            },
            total=total_count,
        )
    except Exception as e:
        logger.error("Failed to list content", error=str(e))
        raise HTTPException(
            status_code=status_module.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    # Create pagination object for response
    pagination_obj = Pagination(**pagination.to_dict(), total=total_count)

    # Convert service response to Pydantic models
    content_details = [ContentDetail.model_validate(item) for item in data]

    # Return proper Pydantic response model
    return ContentResponse(
        pagination=pagination_obj,
        data=content_details,
    )


@router.patch("/content/bulk", response_model=BulkContentUpdateResponse)
async def bulk_update_content(
    session: DBSessionDep,
    bulk_request: BulkContentUpdateRequest,
    current_user=Security(get_current_active_user_or_service_account),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """Bulk update content items via service layer."""
    try:
        updated_count, errors = await cms_service.bulk_update_content_with_validation(
            session, bulk_request.content_ids, bulk_request.updates
        )
        logger.info(
            "Bulk updated content via service",
            updated_count=updated_count,
            error_count=len(errors),
        )
        return BulkContentUpdateResponse(updated_count=updated_count, errors=errors)
    except Exception as e:
        logger.error("Bulk update content failed", error=str(e))
        return BulkContentUpdateResponse(updated_count=0, errors=[{"error": str(e)}])


@router.delete("/content/bulk", response_model=BulkContentDeleteResponse)
async def bulk_delete_content(
    session: DBSessionDep,
    bulk_request: BulkContentDeleteRequest,
    current_user=Security(get_current_active_user_or_service_account),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """Bulk delete content items via service layer."""
    try:
        deleted_count, errors = await cms_service.bulk_delete_content_with_validation(
            session, bulk_request.content_ids
        )
        logger.info(
            "Bulk deleted content via service",
            deleted_count=deleted_count,
            error_count=len(errors),
        )
        return BulkContentDeleteResponse(deleted_count=deleted_count, errors=errors)
    except Exception as e:
        logger.error("Bulk delete content failed", error=str(e))
        return BulkContentDeleteResponse(deleted_count=0, errors=[{"error": str(e)}])


@router.get("/content/{content_id}", response_model=ContentDetail)
async def get_content(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """Get specific content by ID using CMS Workflow Service."""
    try:
        content_result = await cms_service.get_content_with_validation(
            session, content_id
        )

        if not content_result:
            raise HTTPException(
                status_code=status_module.HTTP_404_NOT_FOUND, detail="Content not found"
            )

        return ContentDetail.model_validate(content_result)

    except Exception as e:
        logger.error("Failed to get content", content_id=content_id, error=str(e))
        # Handle not found errors specifically
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status_module.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        raise HTTPException(
            status_code=status_module.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post(
    "/content", response_model=ContentDetail, status_code=status_module.HTTP_201_CREATED
)
async def create_content(
    session: DBSessionDep,
    content_data: ContentCreate,
    current_user_or_service_account=Security(
        get_current_active_user_or_service_account
    ),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """Create new content using CMS Workflow Service."""
    try:
        # For service accounts, set the creator to null.
        created_by = (
            current_user_or_service_account.id
            if isinstance(current_user_or_service_account, User)
            else None
        )

        # Convert Pydantic model to dict for service layer
        content_dict = content_data.model_dump(exclude_unset=True)

        # Use CMS Workflow Service for business logic and event handling
        content_result = await cms_service.create_content_with_validation(
            session, content_dict, created_by
        )

        logger.info(
            "Created content via service",
            content_id=content_result["id"],
            type=content_result["type"],
        )

        return ContentDetail.model_validate(content_result)

    except Exception as e:
        logger.error("Failed to create content", error=str(e))
        raise HTTPException(
            status_code=status_module.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.put("/content/{content_id}", response_model=ContentDetail)
async def update_content(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    content_data: ContentUpdate = Body(...),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """Update existing content using CMS Workflow Service."""
    try:
        # Convert Pydantic model to dict for service layer
        update_dict = content_data.model_dump(exclude_unset=True)

        # Use CMS Workflow Service for business logic and event handling
        updated_content_result = await cms_service.update_content_with_validation(
            session, content_id, update_dict
        )

        logger.info("Updated content via service", content_id=content_id)

        return ContentDetail.model_validate(updated_content_result)

    except Exception as e:
        logger.error("Failed to update content", content_id=content_id, error=str(e))
        # Handle not found errors specifically
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status_module.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        raise HTTPException(
            status_code=status_module.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.delete("/content/{content_id}", status_code=status_module.HTTP_204_NO_CONTENT)
async def delete_content(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """Delete content using CMS Workflow Service."""
    try:
        # Use CMS Workflow Service for business logic and event handling
        success = await cms_service.delete_content_with_validation(session, content_id)

        if not success:
            raise HTTPException(
                status_code=status_module.HTTP_404_NOT_FOUND, detail="Content not found"
            )

        logger.info("Deleted content via service", content_id=content_id)

    except Exception as e:
        logger.error("Failed to delete content", content_id=content_id, error=str(e))
        # Handle not found errors specifically
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status_module.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        raise HTTPException(
            status_code=status_module.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/content/{content_id}/status", response_model=ContentDetail)
async def update_content_status(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    status_update: ContentStatusUpdate = Body(...),
    current_user=Security(get_current_active_user_or_service_account),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """Update content workflow status via service layer."""
    try:
        user_id = getattr(current_user, "id", None)
        updated = await cms_service.update_content_status_with_validation(
            session,
            content_id,
            status_update.status.value,
            status_update.comment,
            user_id,
        )
        logger.info(
            "Updated content status via service",
            content_id=content_id,
            new_status=status_update.status,
            user_id=user_id,
        )
        return ContentDetail.model_validate(updated)
    except Exception as e:
        logger.error(
            "Failed to update content status", content_id=content_id, error=str(e)
        )
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/content/bulk", response_model=BulkContentResponse)
async def bulk_content_operations(
    session: DBSessionDep,
    bulk_request: BulkContentRequest,
    current_user=Security(get_current_active_user_or_service_account),
):
    """Perform bulk operations on content."""
    # Implementation would handle bulk create/update/delete
    # This is a placeholder for the actual implementation
    return BulkContentResponse(success_count=0, error_count=0, errors=[])


# Content Variants Endpoints


@router.get("/content/{content_id}/variants", response_model=ContentVariantResponse)
async def list_content_variants(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    pagination: PaginatedQueryParams = Depends(),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """List variants for specific content via service layer."""
    data, total = await cms_service.list_content_variants(
        session, content_id, pagination.skip, pagination.limit
    )
    return ContentVariantResponse(
        pagination=Pagination(**pagination.to_dict(), total=total), data=data
    )


@router.post(
    "/content/{content_id}/variants",
    response_model=ContentVariantDetail,
    status_code=status_module.HTTP_201_CREATED,
)
async def create_content_variant(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    variant_data: ContentVariantCreate = Body(...),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """Create a new variant for content."""
    try:
        variant = await cms_service.create_content_variant(
            session, content_id, variant_data.model_dump(exclude_unset=True)
        )
        logger.info(
            "Created content variant via service",
            variant_id=variant.id,
            content_id=content_id,
        )
        return variant
    except CMSWorkflowError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/content/{content_id}/variants/{variant_id}", response_model=ContentVariantDetail
)
async def update_content_variant(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    variant_id: UUID = Path(description="Variant ID"),
    variant_data: ContentVariantUpdate = Body(...),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """Update existing content variant."""
    try:
        updated = await cms_service.update_content_variant(
            session, content_id, variant_id, variant_data.model_dump(exclude_unset=True)
        )
        logger.info("Updated content variant via service", variant_id=variant_id)
        return updated
    except CMSWorkflowError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/content/{content_id}/variants/{variant_id}", response_model=ContentVariantDetail
)
async def patch_content_variant(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    variant_id: UUID = Path(description="Variant ID"),
    variant_data: ContentVariantUpdate = Body(...),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """Patch update existing content variant (including performance data)."""
    try:
        updated = await cms_service.patch_content_variant(
            session, content_id, variant_id, variant_data.model_dump(exclude_unset=True)
        )
        logger.info("Patched content variant via service", variant_id=variant_id)
        return updated
    except CMSWorkflowError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/content/{content_id}/variants/{variant_id}",
    status_code=status_module.HTTP_204_NO_CONTENT,
)
async def delete_content_variant(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    variant_id: UUID = Path(description="Variant ID"),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """Delete a content variant."""
    success = await cms_service.delete_content_variant(session, content_id, variant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Variant not found")
    logger.info(
        "Deleted content variant via service",
        variant_id=variant_id,
        content_id=content_id,
    )
    # No return value for 204 No Content


@router.post("/content/{content_id}/variants/{variant_id}/performance")
async def update_variant_performance(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    variant_id: UUID = Path(description="Variant ID"),
    performance_data: VariantPerformanceUpdate = Body(...),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """Update variant performance metrics."""
    try:
        await cms_service.update_variant_performance(
            session,
            content_id,
            variant_id,
            performance_data.model_dump(exclude_unset=True),
        )
        logger.info("Updated variant performance via service", variant_id=variant_id)
        return {"message": "Performance data updated"}
    except CMSWorkflowError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


# Flow Management Endpoints


@router.get("/flows")
async def list_flows(
    session: DBSessionDep,
    published: Optional[bool] = Query(None, description="Filter by published status"),
    is_published: Optional[bool] = Query(
        None, description="Filter by published status (alias)"
    ),
    active: Optional[bool] = Query(
        True, description="Filter by active status (default: True)"
    ),
    search: Optional[str] = Query(None, description="Search in name and description"),
    version: Optional[str] = Query(None, description="Filter by exact version"),
    pagination: PaginatedQueryParams = Depends(),
    flow_service: FlowService = Depends(get_flow_service),
):
    """List flows with filtering options."""
    # Handle published/is_published aliases
    published_filter = published if published is not None else is_published

    try:
        # Get both data and total count using FlowService
        flows, total_count = await flow_service.list_flows_with_filters(
            session,
            published=published_filter,
            active=active,
            search=search,
            version=version,
            skip=pagination.skip,
            limit=pagination.limit,
        )
    except (FlowValidationError, CMSWorkflowError) as e:
        raise HTTPException(
            status_code=status_module.HTTP_400_BAD_REQUEST, detail=str(e)
        )

    # Create pagination object for response
    pagination_obj = Pagination(**pagination.to_dict(), total=total_count)

    # Return proper Pydantic response model (FastAPI will handle serialization)
    return FlowResponse(
        pagination=pagination_obj,
        data=flows,  # Let Pydantic handle the FlowDetail serialization
    )


@router.get("/flows/{flow_id}", response_model=FlowDetail)
async def get_flow(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    include_inactive: Optional[bool] = Query(
        False, description="Include inactive flows"
    ),
    flow_service: FlowService = Depends(get_flow_service),
):
    """Get flow definition."""
    try:
        # Use get_flow_by_id for simple retrieval, get_flow_with_components for operations needing nodes/connections
        flow = await flow_service.get_flow_by_id(session, flow_id)
    except FlowNotFoundError:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )
    except CMSWorkflowError as e:
        raise HTTPException(
            status_code=status_module.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )

    # If flow is inactive and include_inactive is False, return 404
    if not flow.is_active and not include_inactive:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )

    return FlowDetail.model_validate(flow)


@router.post(
    "/flows", response_model=FlowDetail, status_code=status_module.HTTP_201_CREATED
)
async def create_flow(
    session: DBSessionDep,
    flow_data: FlowCreate,
    current_user_or_service_account=Security(
        get_current_active_user_or_service_account
    ),
    flow_service: FlowService = Depends(get_flow_service),
):
    """Create new flow."""

    created_by = (
        current_user_or_service_account.id
        if isinstance(current_user_or_service_account, User)
        else None
    )

    try:
        flow = await flow_service.create_flow(session, flow_data, created_by)
        logger.info("Created flow", flow_id=flow.id, name=flow.name)
        return FlowDetail.model_validate(flow)
    except (FlowValidationError, CMSWorkflowError) as e:
        raise HTTPException(
            status_code=status_module.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.put("/flows/{flow_id}", response_model=FlowDetail)
async def update_flow(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    flow_data: FlowUpdate = Body(...),
    flow_service: FlowService = Depends(get_flow_service),
):
    """Update existing flow."""
    try:
        updated_flow = await flow_service.update_flow(session, flow_id, flow_data)
        logger.info("Updated flow", flow_id=flow_id)
        return FlowDetail.model_validate(updated_flow)
    except FlowNotFoundError:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )
    except (FlowValidationError, CMSWorkflowError) as e:
        raise HTTPException(
            status_code=status_module.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.post("/flows/{flow_id}/publish")
async def publish_flow(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    publish_request: Optional[FlowPublishRequest] = Body(None),
    current_user=Security(get_current_active_user_or_service_account),
    flow_service: FlowService = Depends(get_flow_service),
):
    """Publish or unpublish a flow using Flow Service."""
    try:
        # Get published_by user ID (only for User accounts, None for ServiceAccount)
        published_by = current_user.id if isinstance(current_user, User) else None

        # Determine if we're publishing or unpublishing
        publish = True if publish_request is None else publish_request.publish

        if publish:
            # Publish the flow
            # FlowPublishRequest doesn't have version, it has increment_version logic
            # For now, pass None to use existing flow version
            flow = await flow_service.publish_flow(session, flow_id, published_by, None)
        else:
            # Unpublish the flow
            flow = await flow_service.unpublish_flow(session, flow_id)

        action = "published" if publish else "unpublished"
        logger.info(f"Flow {action}", flow_id=flow_id)

        # Convert SQLAlchemy model to dict for response
        flow_dict = {
            "id": str(flow.id),
            "name": flow.name,
            "description": flow.description,
            "version": flow.version,
            "flow_data": flow.flow_data or {},
            "entry_node_id": flow.entry_node_id,
            "info": flow.info or {},
            "is_published": flow.is_published,
            "is_active": flow.is_active,
            "published_at": flow.published_at.isoformat()
            if flow.published_at
            else None,
            "published_by": str(flow.published_by) if flow.published_by else None,
            "created_at": flow.created_at.isoformat() if flow.created_at else None,
            "updated_at": flow.updated_at.isoformat() if flow.updated_at else None,
            "created_by": str(flow.created_by) if flow.created_by else None,
        }
        return flow_dict

    except FlowNotFoundError:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )
    except FlowValidationError as e:
        raise HTTPException(
            status_code=status_module.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_failed", "errors": e.errors},
        )
    except CMSWorkflowError as e:
        raise HTTPException(
            status_code=status_module.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e)},
        )


# Removed redundant unpublish endpoint; use /publish with publish=false
@router.post("/flows/{flow_id}/unpublish", response_model=FlowDetail)
async def unpublish_flow(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    current_user=Security(get_current_active_user_or_service_account),
    flow_service: FlowService = Depends(get_flow_service),
):
    """Unpublish a flow (legacy endpoint)."""
    try:
        # Unpublish the flow using FlowService
        flow = await flow_service.unpublish_flow(session, flow_id)
        logger.info("Flow unpublished via legacy endpoint", flow_id=flow_id)

        # Convert to FlowDetail response
        flow_dict = {
            "id": str(flow.id),
            "name": flow.name,
            "description": flow.description,
            "version": flow.version,
            "flow_data": flow.flow_data or {},
            "entry_node_id": flow.entry_node_id,
            "info": flow.info or {},
            "is_published": flow.is_published,
            "is_active": flow.is_active,
            "published_at": flow.published_at.isoformat()
            if flow.published_at
            else None,
            "published_by": str(flow.published_by) if flow.published_by else None,
            "created_at": flow.created_at.isoformat() if flow.created_at else None,
            "updated_at": flow.updated_at.isoformat() if flow.updated_at else None,
            "created_by": str(flow.created_by) if flow.created_by else None,
        }
        return FlowDetail.model_validate(flow_dict)
    except FlowNotFoundError:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )
    except Exception as e:
        logger.error("Failed to unpublish flow", flow_id=flow_id, error=str(e))
        raise HTTPException(
            status_code=status_module.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unpublish failed: {str(e)}",
        )


@router.post(
    "/flows/{flow_id}/clone",
    response_model=FlowDetail,
    status_code=status_module.HTTP_201_CREATED,
)
async def clone_flow(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    clone_request: FlowCloneRequest = Body(...),
    current_user=Security(get_current_active_user_or_service_account),
    flow_service: FlowService = Depends(get_flow_service),
):
    """Clone an existing flow."""
    # Handle created_by field - only set for User accounts, None for ServiceAccount
    created_by = current_user.id if isinstance(current_user, User) else None

    try:
        cloned_flow = await flow_service.clone_flow(
            session, flow_id, clone_request, created_by
        )
        logger.info("Cloned flow", original_id=flow_id, cloned_id=cloned_flow.id)
        return FlowDetail.model_validate(cloned_flow)
    except FlowNotFoundError:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )
    except (FlowValidationError, CMSWorkflowError) as e:
        raise HTTPException(
            status_code=status_module.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.get("/flows/{flow_id}/validate")
async def validate_flow(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """Validate flow structure and integrity using CMS Workflow Service."""
    try:
        # Use CMS Workflow Service for comprehensive validation
        validation_result = await cms_service.validate_flow_comprehensive(
            session, flow_id
        )

        logger.info(
            "Validated flow via service",
            flow_id=flow_id,
            is_valid=validation_result["is_valid"],
            errors=len(validation_result["validation_errors"]),
        )

        return validation_result

    except FlowNotFoundError:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )
    except Exception as e:
        logger.error("Flow validation failed", flow_id=flow_id, error=str(e))
        raise HTTPException(
            status_code=status_module.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}",
        )


@router.delete("/flows/{flow_id}", status_code=status_module.HTTP_204_NO_CONTENT)
async def delete_flow(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    flow_service: FlowService = Depends(get_flow_service),
):
    """Delete flow (soft delete by setting is_active=False)."""
    try:
        await flow_service.soft_delete_flow(session, flow_id)
        logger.info("Soft deleted flow", flow_id=flow_id)
    except FlowNotFoundError:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )
    except CMSWorkflowError as e:
        raise HTTPException(
            status_code=status_module.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Flow Node Management Endpoints


@router.get("/flows/{flow_id}/nodes", response_model=NodeResponse)
async def list_flow_nodes(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    pagination: PaginatedQueryParams = Depends(),
    flow_service: FlowService = Depends(get_flow_service),
):
    """List nodes in flow."""
    nodes, total_count = await flow_service.list_nodes(
        session, flow_id, pagination.skip, pagination.limit
    )
    return NodeResponse(
        pagination=Pagination(**pagination.to_dict(), total=total_count), data=nodes
    )


@router.put("/flows/{flow_id}/nodes/positions")
async def update_node_positions(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    position_update: NodePositionUpdate = Body(...),
    flow_service: FlowService = Depends(get_flow_service),
):
    """Batch update node positions."""
    try:
        await flow_service.update_node_positions(
            session, flow_id, position_update.positions
        )
    except CMSWorkflowError as e:
        if "flow not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    logger.info(
        "Updated node positions", flow_id=flow_id, count=len(position_update.positions)
    )
    return {"message": "Node positions updated"}


@router.get("/flows/{flow_id}/nodes/{node_db_id}", response_model=NodeDetail)
async def get_flow_node(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    node_db_id: UUID = Path(description="Node Database ID"),
    flow_service: FlowService = Depends(get_flow_service),
):
    """Get node details."""
    node = await flow_service.get_node(session, flow_id, node_db_id)
    if not node:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Node not found"
        )
    return node


@router.post(
    "/flows/{flow_id}/nodes",
    response_model=NodeDetail,
    status_code=status_module.HTTP_201_CREATED,
)
async def create_flow_node(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    node_data: NodeCreate = Body(...),
    flow_service: FlowService = Depends(get_flow_service),
):
    """Create node in flow."""
    try:
        node = await flow_service.create_node(session, flow_id, node_data)
    except FlowNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CMSWorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))
    logger.info("Created flow node", node_id=node.node_id, flow_id=flow_id)
    return node


@router.put("/flows/{flow_id}/nodes/{node_db_id}", response_model=NodeDetail)
async def update_flow_node(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    node_db_id: UUID = Path(description="Node Database ID"),
    node_data: NodeUpdate = Body(...),
    flow_service: FlowService = Depends(get_flow_service),
):
    """Update node."""
    try:
        # Ensure flow exists first for correct 404
        await flow_service.get_flow_by_id(session, flow_id)
        updated_node = await flow_service.update_node(session, node_db_id, node_data)
        logger.info("Updated flow node", node_db_id=node_db_id, flow_id=flow_id)
        return updated_node
    except CMSWorkflowError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/flows/{flow_id}/nodes/{node_db_id}", status_code=status_module.HTTP_204_NO_CONTENT
)
async def delete_flow_node(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    node_db_id: UUID = Path(description="Node Database ID"),
    flow_service: FlowService = Depends(get_flow_service),
):
    """Delete node and its connections."""
    success = await flow_service.delete_node(session, node_db_id)
    if not success:
        raise HTTPException(status_code=404, detail="Node not found")
    logger.info("Deleted flow node", node_db_id=node_db_id, flow_id=flow_id)


# Flow Connections Endpoints


@router.get("/flows/{flow_id}/connections", response_model=ConnectionResponse)
async def list_flow_connections(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    pagination: PaginatedQueryParams = Depends(),
    flow_service: FlowService = Depends(get_flow_service),
):
    """List connections in flow."""
    connections, total_count = await flow_service.list_connections(
        session, flow_id, pagination.skip, pagination.limit
    )

    return ConnectionResponse(
        pagination=Pagination(**pagination.to_dict(), total=total_count),
        data=connections,
    )


@router.post(
    "/flows/{flow_id}/connections",
    response_model=ConnectionDetail,
    status_code=status_module.HTTP_201_CREATED,
)
async def create_flow_connection(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    connection_data: ConnectionCreate = Body(...),
    flow_service: FlowService = Depends(get_flow_service),
):
    """Create connection between nodes."""
    try:
        connection = await flow_service.create_connection(
            session, flow_id, connection_data
        )
        logger.info(
            "Created flow connection",
            flow_id=flow_id,
            source=connection_data.source_node_id,
            target=connection_data.target_node_id,
        )
        return connection
    except CMSWorkflowError as e:
        if "flow not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/flows/{flow_id}/connections/{connection_id}",
    status_code=status_module.HTTP_204_NO_CONTENT,
)
async def delete_flow_connection(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    connection_id: UUID = Path(description="Connection ID"),
    flow_service: FlowService = Depends(get_flow_service),
):
    """Delete connection."""
    # Ensure connection belongs to the provided flow
    conn = await flow_service.get_connection_by_id(session, connection_id)
    if not conn or conn.flow_id != flow_id:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Connection not found"
        )
    success = await flow_service.delete_connection(session, connection_id)
    if not success:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Connection not found"
        )
    logger.info("Deleted flow connection", connection_id=connection_id, flow_id=flow_id)


# Chat Theme Management Endpoints


@router.get("/themes", response_model=ChatThemeResponse)
async def list_themes(
    session: DBSessionDep,
    school_id: Optional[UUID] = Query(None, description="Filter by school ID"),
    include_global: bool = Query(
        True, description="Include global themes (school_id=null)"
    ),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    pagination: PaginatedQueryParams = Depends(),
    current_user_or_service_account: Union[User, ServiceAccount] = Security(
        get_current_active_user_or_service_account
    ),
):
    """
    List chat themes with filtering options.

    - Admin users can see all themes
    - School admins can see global themes + their school's themes
    - Other users can see global themes + their school's themes (if applicable)
    """
    from sqlalchemy import select

    query = select(ChatTheme).where(ChatTheme.is_active == True)

    if active is not None:
        query = query.where(ChatTheme.is_active == active)

    is_admin = (
        isinstance(current_user_or_service_account, User)
        and current_user_or_service_account.type == UserAccountType.WRIVETED
    )

    if not is_admin:
        user_school_id = None
        if isinstance(current_user_or_service_account, User):
            user_school_id = getattr(current_user_or_service_account, "school_id", None)

        conditions = []
        if include_global:
            conditions.append(ChatTheme.school_id.is_(None))

        if school_id:
            if user_school_id and str(user_school_id) != str(school_id):
                raise HTTPException(
                    status_code=status_module.HTTP_403_FORBIDDEN,
                    detail="Cannot access themes for other schools",
                )
            conditions.append(ChatTheme.school_id == school_id)
        elif user_school_id:
            conditions.append(ChatTheme.school_id == user_school_id)

        if conditions:
            query = query.where(or_(*conditions))
    else:
        if school_id:
            query = query.where(ChatTheme.school_id == school_id)
        elif not include_global:
            query = query.where(ChatTheme.school_id.isnot(None))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total_count = total_result.scalar_one()

    query = (
        query.offset(pagination.skip)
        .limit(pagination.limit)
        .order_by(ChatTheme.created_at.desc())
    )
    result = await session.execute(query)
    themes = result.scalars().all()

    logger.info(
        "Retrieved themes list",
        school_id=school_id,
        include_global=include_global,
        total=total_count,
    )

    pagination_obj = Pagination(**pagination.to_dict(), total=total_count)
    theme_details = [ChatThemeDetail.model_validate(theme) for theme in themes]

    return ChatThemeResponse(pagination=pagination_obj, data=theme_details)


@router.get("/themes/{theme_id}", response_model=ChatThemeDetail)
async def get_theme(
    session: DBSessionDep,
    theme_id: UUID = Path(description="Theme ID"),
    current_user_or_service_account: Union[User, ServiceAccount] = Security(
        get_current_active_user_or_service_account
    ),
):
    """Get a specific chat theme."""
    from sqlalchemy import select

    query = select(ChatTheme).where(ChatTheme.id == theme_id)
    result = await session.execute(query)
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Theme not found"
        )

    is_admin = (
        isinstance(current_user_or_service_account, User)
        and current_user_or_service_account.type == UserAccountType.WRIVETED
    )

    if not is_admin and theme.school_id is not None:
        user_school_id = None
        if isinstance(current_user_or_service_account, User):
            user_school_id = getattr(current_user_or_service_account, "school_id", None)

        if user_school_id is None or str(user_school_id) != str(theme.school_id):
            raise HTTPException(
                status_code=status_module.HTTP_403_FORBIDDEN,
                detail="Cannot access this theme",
            )

    logger.info("Retrieved theme", theme_id=theme_id)
    return ChatThemeDetail.model_validate(theme)


@router.post(
    "/themes",
    response_model=ChatThemeDetail,
    status_code=status_module.HTTP_201_CREATED,
)
async def create_theme(
    session: DBSessionDep,
    theme_data: ChatThemeCreate,
    current_user_or_service_account: Union[User, ServiceAccount] = Security(
        get_current_active_user_or_service_account
    ),
):
    """
    Create a new chat theme.

    - Admin users can create global themes (school_id=null) or school-specific themes
    - School admins can only create themes for their school
    """
    is_admin = (
        isinstance(current_user_or_service_account, User)
        and current_user_or_service_account.type == UserAccountType.WRIVETED
    )

    if theme_data.school_id is None and not is_admin:
        raise HTTPException(
            status_code=status_module.HTTP_403_FORBIDDEN,
            detail="Only admins can create global themes",
        )

    if not is_admin and theme_data.school_id:
        user_school_id = None
        if isinstance(current_user_or_service_account, User):
            user_school_id = getattr(current_user_or_service_account, "school_id", None)

        if user_school_id is None or str(user_school_id) != str(theme_data.school_id):
            raise HTTPException(
                status_code=status_module.HTTP_403_FORBIDDEN,
                detail="Can only create themes for your own school",
            )

    created_by = (
        current_user_or_service_account.id
        if isinstance(current_user_or_service_account, User)
        else None
    )

    theme = ChatTheme(
        name=theme_data.name,
        description=theme_data.description,
        school_id=theme_data.school_id,
        config=theme_data.config.model_dump(),
        logo_url=theme_data.logo_url,
        avatar_url=theme_data.avatar_url,
        is_active=theme_data.is_active,
        is_default=theme_data.is_default,
        version=theme_data.version,
        created_by=created_by,
    )

    session.add(theme)
    await session.commit()
    await session.refresh(theme)

    logger.info("Created theme", theme_id=theme.id, name=theme.name)
    return ChatThemeDetail.model_validate(theme)


@router.put("/themes/{theme_id}", response_model=ChatThemeDetail)
async def update_theme(
    session: DBSessionDep,
    theme_data: ChatThemeUpdate,
    theme_id: UUID = Path(description="Theme ID"),
    current_user_or_service_account: Union[User, ServiceAccount] = Security(
        get_current_active_user_or_service_account
    ),
):
    """
    Update an existing chat theme.

    - Admin users can update any theme
    - School admins can only update their school's themes
    """
    from sqlalchemy import select

    query = select(ChatTheme).where(ChatTheme.id == theme_id)
    result = await session.execute(query)
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Theme not found"
        )

    is_admin = (
        isinstance(current_user_or_service_account, User)
        and current_user_or_service_account.type == UserAccountType.WRIVETED
    )

    if not is_admin:
        if theme.school_id is None:
            raise HTTPException(
                status_code=status_module.HTTP_403_FORBIDDEN,
                detail="Cannot modify global themes",
            )

        user_school_id = None
        if isinstance(current_user_or_service_account, User):
            user_school_id = getattr(current_user_or_service_account, "school_id", None)

        if user_school_id is None or str(user_school_id) != str(theme.school_id):
            raise HTTPException(
                status_code=status_module.HTTP_403_FORBIDDEN,
                detail="Cannot modify themes from other schools",
            )

    update_data = theme_data.model_dump(exclude_unset=True)

    if "config" in update_data and update_data["config"]:
        update_data["config"] = update_data["config"].model_dump()

    for field, value in update_data.items():
        setattr(theme, field, value)

    await session.commit()
    await session.refresh(theme)

    logger.info("Updated theme", theme_id=theme_id)
    return ChatThemeDetail.model_validate(theme)


@router.delete("/themes/{theme_id}", status_code=status_module.HTTP_204_NO_CONTENT)
async def delete_theme(
    session: DBSessionDep,
    theme_id: UUID = Path(description="Theme ID"),
    current_user_or_service_account: Union[User, ServiceAccount] = Security(
        get_current_active_user_or_service_account
    ),
):
    """
    Delete a chat theme (soft delete by setting is_active=False).

    - Admin users can delete any theme
    - School admins can only delete their school's themes
    """
    from sqlalchemy import select

    query = select(ChatTheme).where(ChatTheme.id == theme_id)
    result = await session.execute(query)
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Theme not found"
        )

    is_admin = (
        isinstance(current_user_or_service_account, User)
        and current_user_or_service_account.type == UserAccountType.WRIVETED
    )

    if not is_admin:
        if theme.school_id is None:
            raise HTTPException(
                status_code=status_module.HTTP_403_FORBIDDEN,
                detail="Cannot delete global themes",
            )

        user_school_id = None
        if isinstance(current_user_or_service_account, User):
            user_school_id = getattr(current_user_or_service_account, "school_id", None)

        if user_school_id is None or str(user_school_id) != str(theme.school_id):
            raise HTTPException(
                status_code=status_module.HTTP_403_FORBIDDEN,
                detail="Cannot delete themes from other schools",
            )

    theme.is_active = False
    await session.commit()

    logger.info("Deleted theme (soft delete)", theme_id=theme_id)


# =============================================================================
# Execution Trace / Session Replay Endpoints
# =============================================================================


@router.get("/flows/{flow_id}/sessions", response_model=SessionListResponse)
async def list_flow_sessions(
    session: DBSessionDep,
    request: Request,
    flow_id: UUID = Path(description="Flow ID"),
    status: Optional[str] = Query(None, description="Filter by session status"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    from_date: Optional[datetime] = Query(None, description="Sessions started after"),
    to_date: Optional[datetime] = Query(None, description="Sessions started before"),
    has_errors: Optional[bool] = Query(None, description="Filter by error status"),
    pagination: PaginatedQueryParams = Depends(),
    current_user: Union[User, ServiceAccount] = Security(
        get_current_active_user_or_service_account
    ),
):
    """List sessions for a flow with filtering and pagination.

    Returns session summaries including path, step count, and error status.
    Access is audit logged.
    """
    # Verify flow exists
    flow_result = await session.execute(
        select(FlowDefinition).where(FlowDefinition.id == flow_id)
    )
    flow = flow_result.scalar_one_or_none()
    if not flow:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND,
            detail="Flow not found",
        )

    # Get sessions
    result = await execution_trace_service.list_flow_sessions(
        db=session,
        flow_id=flow_id,
        status=status,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
        has_errors=has_errors,
        limit=pagination.limit,
        offset=pagination.skip,
    )

    logger.info(
        "Listed flow sessions",
        flow_id=str(flow_id),
        total=result["total"],
    )

    return SessionListResponse(
        items=[SessionSummary(**item) for item in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get("/sessions/{session_id}/trace", response_model=SessionTraceResponse)
async def get_session_trace(
    session: DBSessionDep,
    request: Request,
    session_id: UUID = Path(description="Session ID"),
    current_user: Union[User, ServiceAccount] = Security(
        get_current_active_user_or_service_account
    ),
):
    """Get full execution trace for a session.

    Returns complete execution history including state at each step.
    Access is audit logged for compliance.
    """
    try:
        trace = await execution_trace_service.get_session_trace(
            db=session,
            session_id=session_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Log audit record
    if isinstance(current_user, User):
        await trace_audit_service.log_access(
            db=session,
            session_id=session_id,
            accessed_by=current_user.id,
            access_type="view_trace",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            data_accessed={"steps_viewed": len(trace["steps"])},
        )
        await session.commit()

    logger.info(
        "Retrieved session trace",
        session_id=str(session_id),
        step_count=trace["total_steps"],
    )

    return trace


@router.post("/flows/{flow_id}/tracing", response_model=TracingConfigResponse)
async def configure_flow_tracing(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    config: TracingConfigRequest = Body(...),
    current_user: Union[User, ServiceAccount] = Security(
        get_current_active_superuser_or_backend_service_account
    ),
):
    """Configure tracing settings for a flow.

    Allows enabling/disabling tracing and setting detail level and sample rate.
    Admin only.
    """
    # Get flow
    flow_result = await session.execute(
        select(FlowDefinition).where(FlowDefinition.id == flow_id)
    )
    flow = flow_result.scalar_one_or_none()

    if not flow:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND,
            detail="Flow not found",
        )

    # Update tracing config
    flow.trace_enabled = config.enabled
    flow.trace_sample_rate = int(config.sample_rate * 100)  # Store as percentage

    await session.commit()
    await session.refresh(flow)

    logger.info(
        "Updated flow tracing config",
        flow_id=str(flow_id),
        enabled=config.enabled,
        sample_rate=config.sample_rate,
    )

    return TracingConfigResponse(
        flow_id=flow.id,
        enabled=flow.trace_enabled,
        level=config.level,
        sample_rate=flow.trace_sample_rate / 100.0,
    )


@router.get("/flows/{flow_id}/tracing", response_model=TracingConfigResponse)
async def get_flow_tracing_config(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
):
    """Get current tracing configuration for a flow."""
    flow_result = await session.execute(
        select(FlowDefinition).where(FlowDefinition.id == flow_id)
    )
    flow = flow_result.scalar_one_or_none()

    if not flow:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND,
            detail="Flow not found",
        )

    return TracingConfigResponse(
        flow_id=flow.id,
        enabled=flow.trace_enabled,
        level="standard",  # Default level
        sample_rate=flow.trace_sample_rate / 100.0,
    )


@router.get("/flows/{flow_id}/trace-stats")
async def get_flow_trace_stats(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
):
    """Get trace statistics for a flow.

    Returns aggregate stats including traced sessions, total steps, and error rate.
    """
    stats = await trace_cleanup_service.get_flow_trace_stats(
        db=session,
        flow_id=str(flow_id),
    )

    return stats


@router.get("/trace-storage", response_model=TraceStorageStats)
async def get_trace_storage_stats(
    session: DBSessionDep,
    current_user: User = Security(
        get_current_active_superuser_or_backend_service_account
    ),
):
    """Get overall trace storage statistics.

    Admin only. Returns total traces, storage size, and date range.
    """
    stats = await trace_cleanup_service.get_storage_stats(db=session)

    return TraceStorageStats(
        total_traces=stats["total_traces"],
        table_size=stats["table_size"],
        oldest_trace=datetime.fromisoformat(stats["oldest_trace"])
        if stats["oldest_trace"]
        else None,
        newest_trace=datetime.fromisoformat(stats["newest_trace"])
        if stats["newest_trace"]
        else None,
    )
