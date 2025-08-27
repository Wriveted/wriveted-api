from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Security
from starlette import status as status_module
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.async_db_dep import DBSessionDep
from app.api.dependencies.security import (
    get_current_active_superuser_or_backend_service_account,
    get_current_active_user_or_service_account,
)
from app.crud.cms import CRUDContent, CRUDFlowConnection
from app.models import ContentType
from app.models.user import User
from app.schemas.cms import (
    BulkContentRequest,
    BulkContentResponse,
    BulkContentUpdateRequest,
    BulkContentUpdateResponse,
    BulkContentDeleteRequest,
    BulkContentDeleteResponse,
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
from app.schemas.pagination import Pagination
from app.services.cms_workflow import CMSWorkflowService
from app.services.exceptions import (
    FlowValidationError,
    FlowNotFoundError,
    CMSWorkflowError,
)

logger = get_logger()


def get_cms_workflow_service() -> CMSWorkflowService:
    """Dependency function to get CMS Workflow Service instance."""
    return CMSWorkflowService()


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
):
    """Bulk update content items."""
    updated_count = 0
    errors = []

    try:
        for content_id in bulk_request.content_ids:
            content = await crud.content.aget(session, content_id)
            if not content:
                errors.append(
                    {"content_id": str(content_id), "error": "Content not found"}
                )
                continue

            # Create ContentUpdate object from the updates dict
            from app.schemas.cms import ContentUpdate as ContentUpdateSchema

            try:
                # Increment version on content update
                update_dict = bulk_request.updates.copy()
                update_dict["version"] = content.version + 1

                corrected_data = ContentUpdateSchema.model_validate(update_dict)
                await crud.content.aupdate(
                    session, db_obj=content, obj_in=corrected_data
                )
                updated_count += 1
            except Exception as e:
                errors.append({"content_id": str(content_id), "error": str(e)})

    except Exception as e:
        logger.error("Bulk update content failed", error=str(e))
        errors.append({"error": f"Bulk operation failed: {str(e)}"})

    logger.info(
        "Bulk updated content", updated_count=updated_count, error_count=len(errors)
    )
    return BulkContentUpdateResponse(updated_count=updated_count, errors=errors)


@router.delete("/content/bulk", response_model=BulkContentDeleteResponse)
async def bulk_delete_content(
    session: DBSessionDep,
    bulk_request: BulkContentDeleteRequest,
    current_user=Security(get_current_active_user_or_service_account),
):
    """Bulk delete content items."""
    deleted_count = 0
    errors = []

    try:
        content_crud: CRUDContent = crud.content  # type: ignore
        for content_id in bulk_request.content_ids:
            content = await crud.content.aget(session, content_id)
            if not content:
                errors.append(
                    {"content_id": str(content_id), "error": "Content not found"}
                )
                continue

            try:
                await content_crud.aremove(session, id=content_id)
                deleted_count += 1
            except Exception as e:
                errors.append({"content_id": str(content_id), "error": str(e)})

    except Exception as e:
        logger.error("Bulk delete content failed", error=str(e))
        errors.append({"error": f"Bulk operation failed: {str(e)}"})

    logger.info(
        "Bulk deleted content", deleted_count=deleted_count, error_count=len(errors)
    )
    return BulkContentDeleteResponse(deleted_count=deleted_count, errors=errors)


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
):
    """Update content workflow status."""
    content = await crud.content.aget(session, content_id)
    if not content:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Content not found"
        )

    # Update status and potentially increment version
    update_data = {"status": status_update.status}
    if status_update.status.value in ["published", "approved"]:
        # Increment version for published/approved content
        update_data["version"] = content.version + 1

    updated_content = await crud.content.aupdate(
        session, db_obj=content, obj_in=update_data
    )

    logger.info(
        "Updated content status",
        content_id=content_id,
        old_status=content.status,
        new_status=status_update.status,
        comment=status_update.comment,
        user_id=getattr(current_user, "id", None),
    )

    return ContentDetail.model_validate(updated_content)


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
):
    """List variants for specific content."""
    # Get both data and total count
    variants = await crud.content_variant.aget_by_content_id(
        session, content_id=content_id, skip=pagination.skip, limit=pagination.limit
    )

    total_count = await crud.content_variant.aget_count_by_content_id(
        session, content_id=content_id
    )

    return ContentVariantResponse(
        pagination=Pagination(**pagination.to_dict(), total=total_count), data=variants
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
):
    """Create a new variant for content."""
    # Check if content exists
    content = await crud.content.aget(session, content_id)
    if not content:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Content not found"
        )

    variant = await crud.content_variant.acreate(
        session, obj_in=variant_data, content_id=content_id
    )
    logger.info("Created content variant", variant_id=variant.id, content_id=content_id)
    return variant


@router.put(
    "/content/{content_id}/variants/{variant_id}", response_model=ContentVariantDetail
)
async def update_content_variant(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    variant_id: UUID = Path(description="Variant ID"),
    variant_data: ContentVariantUpdate = Body(...),
):
    """Update existing content variant."""
    variant = await crud.content_variant.aget(session, variant_id)
    if not variant or variant.content_id != content_id:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Variant not found"
        )

    updated_variant = await crud.content_variant.aupdate(
        session, db_obj=variant, obj_in=variant_data
    )
    logger.info("Updated content variant", variant_id=variant_id)
    return updated_variant


@router.patch(
    "/content/{content_id}/variants/{variant_id}", response_model=ContentVariantDetail
)
async def patch_content_variant(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    variant_id: UUID = Path(description="Variant ID"),
    variant_data: ContentVariantUpdate = Body(...),
):
    """Patch update existing content variant (including performance data)."""
    variant = await crud.content_variant.aget(session, variant_id)
    if not variant or variant.content_id != content_id:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Variant not found"
        )

    # Handle performance_data in the update
    if hasattr(variant_data, "performance_data") and variant_data.performance_data:
        # Merge with existing performance_data
        existing_performance = getattr(variant, "performance_data", {}) or {}
        updated_performance = {**existing_performance, **variant_data.performance_data}
        # Create a new update object with merged performance data
        update_dict = variant_data.model_dump(exclude_unset=True)
        update_dict["performance_data"] = updated_performance

        from app.schemas.cms import ContentVariantUpdate as ContentVariantUpdateSchema

        merged_data = ContentVariantUpdateSchema.model_validate(update_dict)
        updated_variant = await crud.content_variant.aupdate(
            session, db_obj=variant, obj_in=merged_data
        )
    else:
        updated_variant = await crud.content_variant.aupdate(
            session, db_obj=variant, obj_in=variant_data
        )

    logger.info("Patched content variant", variant_id=variant_id)
    return updated_variant


@router.delete(
    "/content/{content_id}/variants/{variant_id}",
    status_code=status_module.HTTP_204_NO_CONTENT,
)
async def delete_content_variant(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    variant_id: UUID = Path(description="Variant ID"),
):
    """Delete a content variant."""
    variant = await crud.content_variant.aget(session, variant_id)
    if not variant or variant.content_id != content_id:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Variant not found"
        )

    # Delete the variant
    await crud.content_variant.aremove(session, id=variant_id)
    logger.info("Deleted content variant", variant_id=variant_id, content_id=content_id)
    # No return value for 204 No Content


@router.post("/content/{content_id}/variants/{variant_id}/performance")
async def update_variant_performance(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    variant_id: UUID = Path(description="Variant ID"),
    performance_data: VariantPerformanceUpdate = Body(...),
):
    """Update variant performance metrics."""
    variant = await crud.content_variant.aget(session, variant_id)
    if not variant or variant.content_id != content_id:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Variant not found"
        )

    # Update performance data
    await crud.content_variant.aupdate_performance(
        session,
        variant_id=variant_id,
        performance_data=performance_data.dict(exclude_unset=True),
    )
    logger.info("Updated variant performance", variant_id=variant_id)
    return {"message": "Performance data updated"}


# Flow Management Endpoints


@router.get("/flows")
async def list_flows(
    session: DBSessionDep,
    published: Optional[bool] = Query(None, description="Filter by published status"),
    is_published: Optional[bool] = Query(
        None, description="Filter by published status (alias)"
    ),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    version: Optional[str] = Query(None, description="Filter by exact version"),
    pagination: PaginatedQueryParams = Depends(),
):
    """List flows with filtering options."""
    # Handle published/is_published aliases
    published_filter = published if published is not None else is_published

    # Get both data and total count
    flows = await crud.flow.aget_all_with_filters(
        session,
        published=published_filter,
        active=active,
        search=search,
        version=version,
        skip=pagination.skip,
        limit=pagination.limit,
    )

    total_count = await crud.flow.aget_count_with_filters(
        session,
        published=published_filter,
        active=active,
        search=search,
        version=version,
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
):
    """Get flow definition."""
    flow = await crud.flow.aget(session, flow_id)
    if not flow:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
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
):
    """Create new flow."""

    created_by = (
        current_user_or_service_account.id
        if isinstance(current_user_or_service_account, User)
        else None
    )

    flow = await crud.flow.acreate(session, obj_in=flow_data, created_by=created_by)
    logger.info("Created flow", flow_id=flow.id, name=flow.name)

    return FlowDetail.model_validate(flow)


@router.put("/flows/{flow_id}", response_model=FlowDetail)
async def update_flow(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    flow_data: FlowUpdate = Body(...),
):
    """Update existing flow."""
    flow = await crud.flow.aget(session, flow_id)
    if not flow:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )

    updated_flow = await crud.flow.aupdate(session, db_obj=flow, obj_in=flow_data)
    logger.info("Updated flow", flow_id=flow_id)

    return FlowDetail.model_validate(updated_flow)


@router.post("/flows/{flow_id}/publish")
async def publish_flow(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    publish_request: Optional[FlowPublishRequest] = Body(None),
    current_user=Security(get_current_active_user_or_service_account),
    cms_service: CMSWorkflowService = Depends(get_cms_workflow_service),
):
    """Publish or unpublish a flow using CMS Workflow Service."""
    try:
        # Get published_by user ID (only for User accounts, None for ServiceAccount)
        published_by = current_user.id if isinstance(current_user, User) else None

        # Use CMS Workflow Service for proper business logic and validation
        flow_dict = await cms_service.publish_flow_with_validation(
            session, flow_id, published_by, publish_request
        )

        # Determine action for logging
        publish = True if publish_request is None else publish_request.publish
        action = "published" if publish else "unpublished"
        logger.info(f"Flow {action} via service", flow_id=flow_id)

        # Return the service dict directly (already properly formatted)
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


@router.post("/flows/{flow_id}/unpublish", response_model=FlowDetail)
async def unpublish_flow(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    current_user=Security(get_current_active_user_or_service_account),
):
    """Unpublish a flow."""
    flow = await crud.flow.aget(session, flow_id)
    if not flow:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )

    await crud.flow.aupdate_publish_status(
        session,
        flow_id=flow_id,
        published=False,
        published_by=None,
    )

    # Return the updated flow data
    updated_flow = await crud.flow.aget(session, flow_id)
    logger.info("Flow unpublished", flow_id=flow_id)
    return FlowDetail.model_validate(updated_flow)


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
):
    """Clone an existing flow."""
    source_flow = await crud.flow.aget(session, flow_id)
    if not source_flow:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )

    # Handle created_by field - only set for User accounts, None for ServiceAccount
    created_by = current_user.id if isinstance(current_user, User) else None

    cloned_flow = await crud.flow.aclone(
        session,
        source_flow=source_flow,
        new_name=clone_request.name,
        new_version=clone_request.version,
        created_by=created_by,
    )

    # If description or info was provided in the clone request, update it after cloning
    if clone_request.description or clone_request.info:
        from app.schemas.cms import FlowUpdate as FlowUpdateSchema

        update_data_dict = {}
        if clone_request.description:
            update_data_dict["description"] = clone_request.description
        if clone_request.info:
            update_data_dict["info"] = clone_request.info

        update_data = FlowUpdateSchema(**update_data_dict)
        cloned_flow = await crud.flow.aupdate(
            session, db_obj=cloned_flow, obj_in=update_data
        )
    logger.info("Cloned flow", original_id=flow_id, cloned_id=cloned_flow.id)

    return FlowDetail.model_validate(cloned_flow)


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
):
    """Delete flow (soft delete by setting is_active=False)."""
    flow = await crud.flow.aget(session, flow_id)
    if not flow:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )

    # Soft delete by setting is_active to False
    from app.schemas.cms import FlowUpdate as FlowUpdateSchema

    update_data = FlowUpdateSchema(is_active=False)
    await crud.flow.aupdate(session, db_obj=flow, obj_in=update_data)
    logger.info("Soft deleted flow", flow_id=flow_id)


# Flow Node Management Endpoints


@router.get("/flows/{flow_id}/nodes", response_model=NodeResponse)
async def list_flow_nodes(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    pagination: PaginatedQueryParams = Depends(),
):
    """List nodes in flow."""
    # Get both data and total count
    nodes = await crud.flow_node.aget_by_flow_id(
        session, flow_id=flow_id, skip=pagination.skip, limit=pagination.limit
    )

    total_count = await crud.flow_node.aget_count_by_flow_id(session, flow_id=flow_id)

    return NodeResponse(
        pagination=Pagination(**pagination.to_dict(), total=total_count), data=nodes
    )


@router.get("/flows/{flow_id}/nodes/{node_db_id}", response_model=NodeDetail)
async def get_flow_node(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    node_db_id: UUID = Path(description="Node Database ID"),
):
    """Get node details."""
    node = await crud.flow_node.aget(session, node_db_id)
    if not node or node.flow_id != flow_id:
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
):
    """Create node in flow."""
    # Check if flow exists
    flow = await crud.flow.aget(session, flow_id)
    if not flow:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )

    node = await crud.flow_node.acreate(session, obj_in=node_data, flow_id=flow_id)
    logger.info("Created flow node", node_id=node.node_id, flow_id=flow_id)
    return node


@router.put("/flows/{flow_id}/nodes/{node_db_id}", response_model=NodeDetail)
async def update_flow_node(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    node_db_id: UUID = Path(description="Node Database ID"),
    node_data: NodeUpdate = Body(...),
):
    """Update node."""
    node = await crud.flow_node.aget(session, node_db_id)
    if not node or node.flow_id != flow_id:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Node not found"
        )

    updated_node = await crud.flow_node.aupdate(session, db_obj=node, obj_in=node_data)
    logger.info("Updated flow node", node_db_id=node_db_id, flow_id=flow_id)
    return updated_node


@router.delete(
    "/flows/{flow_id}/nodes/{node_db_id}", status_code=status_module.HTTP_204_NO_CONTENT
)
async def delete_flow_node(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    node_db_id: UUID = Path(description="Node Database ID"),
):
    """Delete node and its connections."""
    node = await crud.flow_node.aget(session, node_db_id)
    if not node or node.flow_id != flow_id:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Node not found"
        )

    await crud.flow_node.aremove_with_connections(session, node=node)
    logger.info("Deleted flow node", node_db_id=node_db_id, flow_id=flow_id)


@router.put("/flows/{flow_id}/nodes/positions")
async def update_node_positions(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    position_update: NodePositionUpdate = Body(...),
):
    """Batch update node positions."""
    # Check if flow exists
    flow = await crud.flow.aget(session, flow_id)
    if not flow:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )

    await crud.flow_node.aupdate_positions(
        session, flow_id=flow_id, positions=position_update.positions
    )
    logger.info(
        "Updated node positions", flow_id=flow_id, count=len(position_update.positions)
    )
    return {"message": "Node positions updated"}


# Flow Connections Endpoints


@router.get("/flows/{flow_id}/connections", response_model=ConnectionResponse)
async def list_flow_connections(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    pagination: PaginatedQueryParams = Depends(),
):
    """List connections in flow."""
    # Get both data and total count
    connections = await crud.flow_connection.aget_by_flow_id(
        session, flow_id=flow_id, skip=pagination.skip, limit=pagination.limit
    )

    total_count = await crud.flow_connection.aget_count_by_flow_id(
        session, flow_id=flow_id
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
):
    """Create connection between nodes."""
    # Check if flow exists
    flow = await crud.flow.aget(session, flow_id)
    if not flow:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Flow not found"
        )

    connection = await crud.flow_connection.acreate(
        session, obj_in=connection_data, flow_id=flow_id
    )
    logger.info(
        "Created flow connection",
        flow_id=flow_id,
        source=connection_data.source_node_id,
        target=connection_data.target_node_id,
    )
    return connection


@router.delete(
    "/flows/{flow_id}/connections/{connection_id}",
    status_code=status_module.HTTP_204_NO_CONTENT,
)
async def delete_flow_connection(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    connection_id: UUID = Path(description="Connection ID"),
):
    """Delete connection."""
    connection = await crud.flow_connection.aget(session, connection_id)
    if not connection or connection.flow_id != flow_id:
        raise HTTPException(
            status_code=status_module.HTTP_404_NOT_FOUND, detail="Connection not found"
        )

    connection_crud: CRUDFlowConnection = crud.flow_connection  # type: ignore
    await connection_crud.aremove(session, id=connection_id)
    logger.info("Deleted flow connection", connection_id=connection_id, flow_id=flow_id)
