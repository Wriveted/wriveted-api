from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Security
from starlette import status
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.async_db_dep import DBSessionDep
from app.api.dependencies.security import (
    get_current_active_superuser_or_backend_service_account,
    get_current_active_user,
    get_current_active_user_or_service_account,
)
from app.crud.cms import CRUDContent, CRUDFlow, CRUDFlowConnection
from app.models import ContentType
from app.models.user import User
from app.schemas.cms import (
    BulkContentRequest,
    BulkContentResponse,
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

logger = get_logger()

router = APIRouter(
    tags=["Digital Content Management System"],
    dependencies=[Security(get_current_active_superuser_or_backend_service_account)],
)

# Content Management Endpoints


@router.get("/content", response_model=ContentResponse)
async def list_content(
    session: DBSessionDep,
    content_type: Optional[ContentType] = Query(
        None, description="Filter by content type"
    ),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    search: Optional[str] = Query(None, description="Full-text search"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    pagination: PaginatedQueryParams = Depends(),
):
    """List content with filtering options."""
    try:
        # Get both data and total count
        data = await crud.content.aget_all_with_optional_filters(
            session,
            content_type=content_type,
            tags=tags,
            search=search,
            active=active,
            skip=pagination.skip,
            limit=pagination.limit,
        )

        total_count = await crud.content.aget_count_with_optional_filters(
            session,
            content_type=content_type,
            tags=tags,
            search=search,
            active=active,
        )

        logger.info(
            "Retrieved content list",
            filters={
                "type": content_type,
                "tags": tags,
                "search": search,
                "active": active,
            },
            total=total_count,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    return ContentResponse(
        pagination=Pagination(**pagination.to_dict(), total=total_count), data=data
    )


@router.get("/content/{content_type}", response_model=ContentResponse, deprecated=True)
async def get_cms_content_by_type(
    session: DBSessionDep,
    content_type: ContentType = Path(description="What type of content to return"),
    query: str | None = Query(
        None, description="A query string to match against content"
    ),
    jsonpath_match: str = Query(
        None,
        description="Filter using a JSONPath over the content. The resulting value must be a boolean expression.",
    ),
    pagination: PaginatedQueryParams = Depends(),
):
    """
    DEPRECATED: Get a filtered and paginated list of content by content type.

    Use GET /content with content_type query parameter instead.
    This endpoint will be removed in a future version.
    """
    logger.warning(
        "DEPRECATED endpoint accessed",
        endpoint="GET /content/{content_type}",
        replacement="GET /content?content_type=...",
        content_type=content_type,
    )

    try:
        data = await crud.content.aget_all_with_optional_filters(
            session,
            content_type=content_type,
            search=query,
            jsonpath_match=jsonpath_match,
            skip=pagination.skip,
            limit=pagination.limit,
        )
        logger.info(
            "Retrieved digital content",
            content_type=content_type,
            query=query,
            data=data,
            jsonpath_match=jsonpath_match,
            skip=pagination.skip,
            limit=pagination.limit,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    return ContentResponse(
        pagination=Pagination(**pagination.to_dict(), total=None), data=data
    )


@router.get("/content/{content_id}", response_model=ContentDetail)
async def get_content(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
):
    """Get specific content by ID."""
    content = await crud.content.aget(session, content_id)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Content not found"
        )
    return content


@router.post(
    "/content", response_model=ContentDetail, status_code=status.HTTP_201_CREATED
)
async def create_content(
    session: DBSessionDep,
    content_data: ContentCreate,
    current_user_or_service_account=Security(
        get_current_active_user_or_service_account
    ),
):
    """Create new content."""
    # For service accounts, set the creator to null.
    created_by = (
        current_user_or_service_account.id
        if isinstance(current_user_or_service_account, User)
        else None
    )

    content = await crud.content.acreate(
        session, obj_in=content_data, created_by=created_by
    )
    logger.info("Created content", content_id=content.id, type=content.type)
    return content


@router.put("/content/{content_id}", response_model=ContentDetail)
async def update_content(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
    content_data: ContentUpdate = Body(...),
):
    """Update existing content."""
    content = await crud.content.aget(session, content_id)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Content not found"
        )

    updated_content = await crud.content.aupdate(
        session, db_obj=content, obj_in=content_data
    )
    logger.info("Updated content", content_id=content_id)
    return updated_content


@router.delete("/content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(
    session: DBSessionDep,
    content_id: UUID = Path(description="Content ID"),
):
    """Delete content."""
    content = await crud.content.aget(session, content_id)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Content not found"
        )

    content_crud: CRUDContent = crud.content  # type: ignore
    await content_crud.aremove(session, id=content_id)
    logger.info("Deleted content", content_id=content_id)


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
            status_code=status.HTTP_404_NOT_FOUND, detail="Content not found"
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
        user_id=current_user.id,
    )
    return updated_content


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
    status_code=status.HTTP_201_CREATED,
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Content not found"
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found"
        )

    updated_variant = await crud.content_variant.aupdate(
        session, db_obj=variant, obj_in=variant_data
    )
    logger.info("Updated content variant", variant_id=variant_id)
    return updated_variant


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
            status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found"
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


@router.get("/flows", response_model=FlowResponse)
async def list_flows(
    session: DBSessionDep,
    published: Optional[bool] = Query(None, description="Filter by published status"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    pagination: PaginatedQueryParams = Depends(),
):
    """List flows with filtering options."""
    # Get both data and total count
    flows = await crud.flow.aget_all_with_filters(
        session,
        published=published,
        active=active,
        skip=pagination.skip,
        limit=pagination.limit,
    )

    total_count = await crud.flow.aget_count_with_filters(
        session,
        published=published,
        active=active,
    )

    return FlowResponse(
        pagination=Pagination(**pagination.to_dict(), total=total_count), data=flows
    )


@router.get("/flows/{flow_id}", response_model=FlowDetail)
async def get_flow(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
):
    """Get flow definition."""
    flow = await crud.flow.aget(session, flow_id)
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found"
        )
    return flow


@router.post("/flows", response_model=FlowDetail, status_code=status.HTTP_201_CREATED)
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
    return flow


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
            status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found"
        )

    updated_flow = await crud.flow.aupdate(session, db_obj=flow, obj_in=flow_data)
    logger.info("Updated flow", flow_id=flow_id)
    return updated_flow


@router.post("/flows/{flow_id}/publish")
async def publish_flow(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    publish_request: FlowPublishRequest = Body(...),
    current_user=Security(get_current_active_user_or_service_account),
):
    """Publish or unpublish a flow."""
    flow = await crud.flow.aget(session, flow_id)
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found"
        )

    await crud.flow.aupdate_publish_status(
        session,
        flow_id=flow_id,
        published=publish_request.publish,
        published_by=current_user.id if publish_request.publish else None,
    )

    action = "published" if publish_request.publish else "unpublished"
    logger.info(f"Flow {action}", flow_id=flow_id)
    return {"message": f"Flow {action} successfully"}


@router.post(
    "/flows/{flow_id}/clone",
    response_model=FlowDetail,
    status_code=status.HTTP_201_CREATED,
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found"
        )

    cloned_flow = await crud.flow.aclone(
        session,
        source_flow=source_flow,
        new_name=clone_request.name,
        new_version=clone_request.version,
        created_by=current_user.id,
    )
    logger.info("Cloned flow", original_id=flow_id, cloned_id=cloned_flow.id)
    return cloned_flow


@router.delete("/flows/{flow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flow(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
):
    """Delete flow."""
    flow = await crud.flow.aget(session, flow_id)
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found"
        )

    flow_crud: CRUDFlow = crud.flow  # type: ignore
    await flow_crud.aremove(session, id=flow_id)
    logger.info("Deleted flow", flow_id=flow_id)


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


@router.get("/flows/{flow_id}/nodes/{node_id}", response_model=NodeDetail)
async def get_flow_node(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    node_id: str = Path(description="Node ID"),
):
    """Get node details."""
    node = await crud.flow_node.aget_by_flow_and_node_id(
        session, flow_id=flow_id, node_id=node_id
    )
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Node not found"
        )
    return node


@router.post(
    "/flows/{flow_id}/nodes",
    response_model=NodeDetail,
    status_code=status.HTTP_201_CREATED,
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found"
        )

    node = await crud.flow_node.acreate(session, obj_in=node_data, flow_id=flow_id)
    logger.info("Created flow node", node_id=node.node_id, flow_id=flow_id)
    return node


@router.put("/flows/{flow_id}/nodes/{node_id}", response_model=NodeDetail)
async def update_flow_node(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    node_id: str = Path(description="Node ID"),
    node_data: NodeUpdate = Body(...),
):
    """Update node."""
    node = await crud.flow_node.aget_by_flow_and_node_id(
        session, flow_id=flow_id, node_id=node_id
    )
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Node not found"
        )

    updated_node = await crud.flow_node.aupdate(session, db_obj=node, obj_in=node_data)
    logger.info("Updated flow node", node_id=node_id, flow_id=flow_id)
    return updated_node


@router.delete(
    "/flows/{flow_id}/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_flow_node(
    session: DBSessionDep,
    flow_id: UUID = Path(description="Flow ID"),
    node_id: str = Path(description="Node ID"),
):
    """Delete node and its connections."""
    node = await crud.flow_node.aget_by_flow_and_node_id(
        session, flow_id=flow_id, node_id=node_id
    )
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Node not found"
        )

    await crud.flow_node.aremove_with_connections(session, node=node)
    logger.info("Deleted flow node", node_id=node_id, flow_id=flow_id)


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
            status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found"
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
    status_code=status.HTTP_201_CREATED,
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found"
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
    status_code=status.HTTP_204_NO_CONTENT,
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found"
        )

    connection_crud: CRUDFlowConnection = crud.flow_connection  # type: ignore
    await connection_crud.aremove(session, id=connection_id)
    logger.info("Deleted flow connection", connection_id=connection_id, flow_id=flow_id)
