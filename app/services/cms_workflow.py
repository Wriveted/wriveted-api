"""
CMS Workflow Service - Domain service for content management workflows.

This service follows the existing architecture patterns in the codebase:
- Uses existing CMSRepository interface (established pattern)
- Integrates with existing EventOutboxService for reliable event delivery
- Raises service-layer exceptions (not HTTP exceptions)
- Handles complex CMS workflows with proper orchestration
- Follows the established service layer patterns like ConversationService
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.repositories.cms_repository import CMSRepository, CMSRepositoryImpl
from app.schemas.cms import FlowPublishRequest
from app.services.event_outbox_service import EventOutboxService
from app.services.exceptions import (
    ContentWorkflowError,
    FlowNotFoundError,
    FlowValidationError,
)

logger = get_logger()


class CMSWorkflowService:
    """
    Write service for CMS workflow operations following established patterns.

    This service implements the same architecture as ConversationService:
    - Uses domain-specific repository interfaces
    - Integrates with EventOutboxService for reliable events
    - Maintains transaction boundaries for write operations
    - Contains business logic for complex CMS workflows
    - Raises domain exceptions for proper error handling
    """

    def __init__(
        self,
        cms_repo: Optional[CMSRepository] = None,
        event_outbox: Optional[EventOutboxService] = None,
    ):
        # Dependency injection for testability
        self.cms_repo = cms_repo or CMSRepositoryImpl()
        self.event_outbox = event_outbox or EventOutboxService()
        self.logger = logger

    # WRITE OPERATIONS - Use transactions for consistency (following ConversationService pattern)

    async def publish_flow_with_validation(
        self,
        db: AsyncSession,
        flow_id: UUID,
        published_by_user_id: Optional[UUID],
        publish_request: Optional[FlowPublishRequest] = None,
    ) -> Dict[str, Any]:
        """
        Publish flow with comprehensive validation and workflow tracking.

        Business logic:
        - Validates flow structure before publishing
        - Sets published_by for audit trail
        - Handles publish/unpublish operations
        - Publishes domain events via outbox pattern

        This is a WRITE operation that requires transaction consistency.
        """
        self.logger.info("Publishing flow with validation", flow_id=flow_id)

        # Get flow with all components for validation
        flow = await self.cms_repo.get_flow_with_nodes(db, flow_id)
        if not flow:
            raise FlowNotFoundError(str(flow_id))

        # Default to publishing if no request body provided
        publish = True if publish_request is None else publish_request.publish

        if publish:
            # Validate flow before publishing
            validation_result = await self._validate_flow_structure(db, flow)
            if not validation_result["is_valid"]:
                raise FlowValidationError(validation_result["validation_errors"])

            # Handle version increment if requested
            new_version = None
            if publish_request and publish_request.increment_version:
                new_version = self._increment_version(
                    flow.version, publish_request.version_type or "patch"
                )

            # Publish flow - write operation
            published_flow = await self.cms_repo.publish_flow(
                db, flow_id, published_by_user_id, new_version=new_version
            )

            # Add domain event to outbox (same transaction)
            await self.event_outbox.publish_event(
                db,
                event_type="flow.published",
                destination="webhook_immediate",
                payload={
                    "flow_id": str(flow_id),
                    "flow_name": flow.name,
                    "version": flow.version,
                    "published_by": str(published_by_user_id)
                    if published_by_user_id
                    else None,
                    "published_at": datetime.utcnow().isoformat(),
                },
                flow_id=flow_id,
                user_id=published_by_user_id,
            )

            self.logger.info(
                "Flow published successfully",
                flow_id=flow_id,
                published_by=published_by_user_id,
            )
        else:
            # Unpublish flow - write operation
            published_flow = await self.cms_repo.unpublish_flow(db, flow_id)

            # Add unpublish event to outbox
            await self.event_outbox.publish_event(
                db,
                event_type="flow.unpublished",
                destination="webhook_immediate",
                payload={
                    "flow_id": str(flow_id),
                    "flow_name": flow.name,
                    "unpublished_at": datetime.utcnow().isoformat(),
                },
                flow_id=flow_id,
                user_id=published_by_user_id,
            )

            self.logger.info("Flow unpublished successfully", flow_id=flow_id)

        return await self._convert_flow_to_dict(db, published_flow)

    def _increment_version(self, current_version: str, version_type: str) -> str:
        """
        Increment version number based on semantic versioning.

        Args:
            current_version: Current version string (e.g., "1.0.0")
            version_type: Type of increment ("major", "minor", "patch")

        Returns:
            New version string
        """
        try:
            # Parse semantic version
            parts = current_version.split(".")
            if len(parts) != 3:
                # If not semantic version, just append increment
                return f"{current_version}.1"

            major, minor, patch = map(int, parts)

            if version_type == "major":
                major += 1
                minor = 0
                patch = 0
            elif version_type == "minor":
                minor += 1
                patch = 0
            else:  # patch
                patch += 1

            return f"{major}.{minor}.{patch}"

        except (ValueError, IndexError):
            # Fallback for non-semantic versions
            return f"{current_version}.1"

    async def validate_flow_comprehensive(
        self, db: AsyncSession, flow_id: UUID
    ) -> Dict[str, Any]:
        """
        Comprehensive flow validation with detailed error reporting.

        Business logic:
        - Validates flow structure and connectivity
        - Checks for orphaned nodes and circular dependencies
        - Provides detailed validation report

        This is a READ operation - no transaction needed.
        """
        self.logger.info("Validating flow comprehensively", flow_id=flow_id)

        flow = await self.cms_repo.get_flow_with_nodes(db, flow_id)
        if not flow:
            raise FlowNotFoundError(str(flow_id))

        return await self._validate_flow_structure(db, flow)

    # READ OPERATIONS - Direct repository access, no transactions needed (following ConversationService pattern)

    async def get_published_flows(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Get all published flows available for conversations.

        This is a READ operation - no transaction needed.
        """
        flows = await self.cms_repo.find_published_flows(db)
        return [await self._convert_flow_to_dict(db, flow) for flow in flows]

    async def get_random_content(
        self,
        db: AsyncSession,
        content_type: str,
        exclude_ids: Optional[List[UUID]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get random content of a specific type for variety in conversations.

        This is a READ operation - no transaction needed.
        """
        from app.models.cms import ContentType

        try:
            content_type_enum = ContentType(content_type)
        except ValueError:
            raise ContentWorkflowError(f"Invalid content type: {content_type}")

        content = await self.cms_repo.get_random_content_of_type(
            db, content_type_enum, exclude_ids
        )

        if not content:
            return None

        return self._convert_content_to_dict(content)

    # PRIVATE BUSINESS LOGIC METHODS

    async def _validate_flow_structure(self, db: AsyncSession, flow) -> Dict[str, Any]:
        """Validate flow structure and return detailed results."""
        import re

        validation_errors = []
        validation_warnings = []

        # Check if entry node exists
        entry_node_exists = any(
            node.node_id == flow.entry_node_id for node in flow.nodes
        )
        if not entry_node_exists:
            validation_errors.append(
                f"Entry node '{flow.entry_node_id}' does not exist"
            )

        # Check for orphaned nodes (nodes without connections)
        if flow.nodes and flow.connections:
            connected_nodes = set()
            for conn in flow.connections:
                connected_nodes.add(conn.source_node_id)
                connected_nodes.add(conn.target_node_id)

            for node in flow.nodes:
                if (
                    node.node_id not in connected_nodes
                    and node.node_id != flow.entry_node_id
                ):
                    validation_warnings.append(
                        f"Node '{node.node_id}' is not connected to any other nodes"
                    )

        # Validate template variable syntax in node content
        variable_pattern = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
        valid_scopes = {"user", "context", "temp", "input", "output", "local"}

        for node in flow.nodes:
            if not node.content:
                continue

            # Check text content for template variables
            text_content = node.content.get("text", "")
            if text_content:
                matches = variable_pattern.findall(text_content)
                for match in matches:
                    variable_ref = match.strip()
                    # Check if it's a secret reference (secret:key format)
                    if variable_ref.startswith("secret:"):
                        continue
                    # Check if variable has a valid scope prefix
                    if "." not in variable_ref:
                        validation_warnings.append(
                            f"Node '{node.node_id}': Variable '{{{{ {variable_ref} }}}}' "
                            f"missing scope prefix. Use '{{{{ temp.{variable_ref} }}}}' for "
                            f"question responses or '{{{{ user.{variable_ref} }}}}' for user data."
                        )
                    else:
                        scope = variable_ref.split(".")[0]
                        if scope not in valid_scopes:
                            validation_warnings.append(
                                f"Node '{node.node_id}': Variable '{{{{ {variable_ref} }}}}' "
                                f"has invalid scope '{scope}'. Valid scopes: {', '.join(sorted(valid_scopes))}"
                            )

        is_valid = len(validation_errors) == 0

        return {
            "is_valid": is_valid,
            "validation_errors": validation_errors,
            "validation_warnings": validation_warnings,
            "nodes_count": len(flow.nodes),
            "connections_count": len(flow.connections),
            "entry_node_id": flow.entry_node_id,
        }

    def _convert_content_to_dict(self, content) -> Dict[str, Any]:
        """Convert content object to dict with proper info field consistency."""
        info = {}
        if hasattr(content, "info") and content.info:
            # Handle SQLAlchemy MutableDict conversion
            info = (
                {str(k): v for k, v in content.info.items()}
                if hasattr(content.info, "items")
                else {}
            )

        return {
            "id": str(content.id),
            # Be defensive: content.type might be None in edge cases
            "type": content.type.value
            if hasattr(content, "type") and content.type
            else "unknown",
            "content": content.content,
            "info": info,
            "tags": content.tags if hasattr(content, "tags") else [],
            "is_active": content.is_active,
            "status": content.status.value
            if hasattr(content, "status") and content.status
            else "draft",
            "version": content.version if hasattr(content, "version") else 1,
            "created_at": content.created_at.isoformat()
            if hasattr(content, "created_at")
            else None,
            "updated_at": content.updated_at.isoformat()
            if hasattr(content, "updated_at")
            else None,
        }

    # Content Management Service Methods
    async def create_content_with_validation(
        self,
        db: AsyncSession,
        content_data: Dict[str, Any],
        created_by: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Create content with business logic validation and event publishing."""
        try:
            # Validate content data structure
            if not content_data.get("type"):
                raise ContentWorkflowError("Content type is required")

            if not content_data.get("content"):
                raise ContentWorkflowError("Content body is required")

            # Create content via repository
            content = await self.cms_repo.create_content(db, content_data, created_by)

            # Publish creation event
            await self.event_outbox.publish_event(
                db,
                "content_created",
                "webhook_immediate",
                {
                    "content_id": str(content.id),
                    "content_type": content.type.value,
                    "created_by": str(created_by) if created_by else None,
                },
            )

            # Commit the transaction
            await db.commit()

            logger.info(
                "Created content with workflow service",
                content_id=content.id,
                content_type=content.type,
            )

            return self._convert_content_to_dict(content)

        except Exception as e:
            logger.error("Failed to create content", error=str(e))
            await db.rollback()
            if isinstance(e, ContentWorkflowError):
                raise
            raise ContentWorkflowError(f"Failed to create content: {str(e)}")

    async def update_content_with_validation(
        self, db: AsyncSession, content_id: UUID, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update content with business logic validation and event publishing."""
        try:
            # Check if content exists
            existing_content = await self.cms_repo.get_content_by_id(db, content_id)
            if not existing_content:
                raise ContentWorkflowError(f"Content not found: {content_id}")

            # Filter out None values to avoid overwriting with nulls
            filtered_update_data = {
                k: v for k, v in update_data.items() if v is not None
            }

            # Update content via repository
            updated_content = await self.cms_repo.update_content(
                db, content_id, filtered_update_data
            )

            # Publish update event
            await self.event_outbox.publish_event(
                db,
                "content_updated",
                "webhook_immediate",
                {
                    "content_id": str(content_id),
                    "content_type": updated_content.type.value,
                    "changes": list(filtered_update_data.keys()),
                },
            )

            # Commit the transaction
            await db.commit()

            logger.info(
                "Updated content with workflow service",
                content_id=content_id,
                changes=list(filtered_update_data.keys()),
            )

            return self._convert_content_to_dict(updated_content)

        except Exception as e:
            logger.error(
                "Failed to update content", content_id=content_id, error=str(e)
            )
            await db.rollback()
            if isinstance(e, ContentWorkflowError):
                raise
            raise ContentWorkflowError(f"Failed to update content: {str(e)}")

    async def update_content_status_with_validation(
        self,
        db: AsyncSession,
        content_id: UUID,
        new_status: str,
        comment: Optional[str] = None,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Update content workflow status with versioning rules and events."""
        from app.models.cms import ContentStatus as ContentStatusEnum

        try:
            content = await self.cms_repo.get_content_by_id(db, content_id)
            if not content:
                raise ContentWorkflowError(f"Content not found: {content_id}")

            try:
                status_enum = ContentStatusEnum(new_status)
            except ValueError:
                raise ContentWorkflowError(f"Invalid status: {new_status}")

            update_data: Dict[str, Any] = {"status": status_enum}
            # Increment version for published/approved content
            if status_enum.value in ["published", "approved"]:
                update_data["version"] = content.version + 1

            updated_content = await self.cms_repo.update_content(
                db, content_id, update_data
            )

            await self.event_outbox.publish_event(
                db,
                "content_status_updated",
                "webhook_immediate",
                {
                    "content_id": str(content_id),
                    "new_status": status_enum.value,
                    "comment": comment,
                    "updated_by": str(user_id) if user_id else None,
                },
            )

            self.logger.info(
                "Updated content status via workflow",
                content_id=content_id,
                new_status=status_enum.value,
            )
            return self._convert_content_to_dict(updated_content)
        except Exception as e:
            logger.error(
                "Failed to update content status", content_id=content_id, error=str(e)
            )
            await db.rollback()
            if isinstance(e, ContentWorkflowError):
                raise
            raise ContentWorkflowError(f"Failed to update content status: {str(e)}")

    async def bulk_update_content_with_validation(
        self,
        db: AsyncSession,
        content_ids: list[UUID],
        updates: Dict[str, Any],
    ) -> tuple[int, list[Dict[str, Any]]]:
        """Bulk update content with validation; returns (updated_count, errors)."""
        updated_count = 0
        errors: list[Dict[str, Any]] = []
        for cid in content_ids:
            try:
                existing = await self.cms_repo.get_content_by_id(db, cid)
                if not existing:
                    errors.append(
                        {"content_id": str(cid), "error": "Content not found"}
                    )
                    continue
                # Filter None to avoid overwriting with nulls
                filtered = {k: v for k, v in updates.items() if v is not None}
                await self.cms_repo.update_content(db, cid, filtered)
                updated_count += 1
            except Exception as e:
                errors.append({"content_id": str(cid), "error": str(e)})

        # Commit all updates in a single transaction
        await db.commit()

        return updated_count, errors

    async def bulk_delete_content_with_validation(
        self,
        db: AsyncSession,
        content_ids: list[UUID],
    ) -> tuple[int, list[Dict[str, Any]]]:
        """Bulk delete content with validation; returns (deleted_count, errors)."""
        deleted_count = 0
        errors: list[Dict[str, Any]] = []
        for cid in content_ids:
            try:
                success = await self.cms_repo.delete_content(db, cid)
                if success:
                    deleted_count += 1
                else:
                    errors.append(
                        {"content_id": str(cid), "error": "Content not found"}
                    )
            except Exception as e:
                errors.append({"content_id": str(cid), "error": str(e)})

        # Commit all deletes in a single transaction
        await db.commit()

        return deleted_count, errors

    async def delete_content_with_validation(
        self, db: AsyncSession, content_id: UUID
    ) -> bool:
        """Delete content with business logic validation and event publishing."""
        try:
            # Check if content exists and get details for event
            existing_content = await self.cms_repo.get_content_by_id(db, content_id)
            if not existing_content:
                raise ContentWorkflowError(f"Content not found: {content_id}")

            # Delete content via repository
            success = await self.cms_repo.delete_content(db, content_id)

            if success:
                # Publish deletion event
                await self.event_outbox.publish_event(
                    db,
                    "content_deleted",
                    "webhook_immediate",
                    {
                        "content_id": str(content_id),
                        "content_type": existing_content.type.value,
                    },
                )

                logger.info(
                    "Deleted content with workflow service", content_id=content_id
                )

            return success

        except Exception as e:
            logger.error(
                "Failed to delete content", content_id=content_id, error=str(e)
            )
            await db.rollback()
            if isinstance(e, ContentWorkflowError):
                raise
            raise ContentWorkflowError(f"Failed to delete content: {str(e)}")

    async def list_content_with_business_logic(
        self,
        db: AsyncSession,
        content_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        active: Optional[bool] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Dict[str, Any]], int]:
        """List content with business logic and return both data and count."""
        try:
            from app.models.cms import ContentType as ContentTypeEnum

            # Convert string content_type to enum
            content_type_enum = None
            if content_type:
                try:
                    content_type_enum = ContentTypeEnum(content_type)
                except ValueError:
                    raise ContentWorkflowError(f"Invalid content type: {content_type}")

            # Get content list and count
            content_list = await self.cms_repo.list_content_with_filters(
                db, content_type_enum, tags, search, active, status, skip, limit
            )

            total_count = await self.cms_repo.count_content_with_filters(
                db, content_type_enum, tags, search, active, status
            )

            # Convert to dict format
            content_dicts = [
                self._convert_content_to_dict(content) for content in content_list
            ]

            logger.debug(
                "Listed content with business logic",
                count=len(content_dicts),
                total=total_count,
                content_type=content_type,
            )

            return content_dicts, total_count

        except Exception as e:
            logger.error("Failed to list content", error=str(e))
            if isinstance(e, ContentWorkflowError):
                raise
            raise ContentWorkflowError(f"Failed to list content: {str(e)}")

    async def get_content_with_validation(
        self, db: AsyncSession, content_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get content by ID with validation."""
        try:
            content = await self.cms_repo.get_content_by_id(db, content_id)

            if not content:
                return None

            return self._convert_content_to_dict(content)

        except Exception as e:
            logger.error("Failed to get content", content_id=content_id, error=str(e))
            raise ContentWorkflowError(f"Failed to get content: {str(e)}")

    # Content Variant Methods
    async def list_content_variants(
        self,
        db: AsyncSession,
        content_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[dict], int]:
        from app import crud

        variants = await crud.content_variant.aget_by_content_id(
            db, content_id=content_id, skip=skip, limit=limit
        )
        total = await crud.content_variant.aget_count_by_content_id(
            db, content_id=content_id
        )
        return [v for v in variants], total

    async def create_content_variant(
        self,
        db: AsyncSession,
        content_id: UUID,
        variant_data: dict,
    ):
        from app import crud
        from app.schemas.cms import ContentVariantCreate

        content = await self.cms_repo.get_content_by_id(db, content_id)
        if not content:
            raise ContentWorkflowError("Content not found")
        variant_in = ContentVariantCreate.model_validate(variant_data)
        variant = await crud.content_variant.acreate(
            db, obj_in=variant_in, content_id=content_id
        )
        await self.event_outbox.publish_event(
            db,
            "content_variant_created",
            "webhook_immediate",
            {"content_id": str(content_id), "variant_id": str(variant.id)},
        )
        return variant

    async def update_content_variant(
        self,
        db: AsyncSession,
        content_id: UUID,
        variant_id: UUID,
        variant_data: dict,
    ):
        from app import crud
        from app.schemas.cms import ContentVariantUpdate

        variant = await crud.content_variant.aget(db, variant_id)
        if not variant or variant.content_id != content_id:
            raise ContentWorkflowError("Variant not found")
        variant_update = ContentVariantUpdate.model_validate(variant_data)
        updated = await crud.content_variant.aupdate(
            db, db_obj=variant, obj_in=variant_update
        )
        await self.event_outbox.publish_event(
            db,
            "content_variant_updated",
            "webhook_immediate",
            {"content_id": str(content_id), "variant_id": str(variant_id)},
        )
        return updated

    async def patch_content_variant(
        self,
        db: AsyncSession,
        content_id: UUID,
        variant_id: UUID,
        variant_data: dict,
    ):
        from app import crud
        from app.schemas.cms import ContentVariantUpdate

        variant = await crud.content_variant.aget(db, variant_id)
        if not variant or variant.content_id != content_id:
            raise ContentWorkflowError("Variant not found")
        # Merge performance_data if present
        if "performance_data" in variant_data and variant_data["performance_data"]:
            existing = getattr(variant, "performance_data", {}) or {}
            variant_data = {
                **variant_data,
                "performance_data": {**existing, **variant_data["performance_data"]},
            }
        variant_update = ContentVariantUpdate.model_validate(variant_data)
        updated = await crud.content_variant.aupdate(
            db, db_obj=variant, obj_in=variant_update
        )
        await self.event_outbox.publish_event(
            db,
            "content_variant_updated",
            "webhook_immediate",
            {"content_id": str(content_id), "variant_id": str(variant_id)},
        )
        return updated

    async def delete_content_variant(
        self,
        db: AsyncSession,
        content_id: UUID,
        variant_id: UUID,
    ) -> bool:
        from app import crud

        variant = await crud.content_variant.aget(db, variant_id)
        if not variant or variant.content_id != content_id:
            return False
        await crud.content_variant.aremove(db, id=variant_id)
        await self.event_outbox.publish_event(
            db,
            "content_variant_deleted",
            "webhook_immediate",
            {"content_id": str(content_id), "variant_id": str(variant_id)},
        )
        return True

    async def update_variant_performance(
        self,
        db: AsyncSession,
        content_id: UUID,
        variant_id: UUID,
        performance_update: dict,
    ) -> None:
        from app import crud

        variant = await crud.content_variant.aget(db, variant_id)
        if not variant or variant.content_id != content_id:
            raise ContentWorkflowError("Variant not found")
        await crud.content_variant.aupdate_performance(
            db, variant_id=variant_id, performance_data=performance_update
        )
        await self.event_outbox.publish_event(
            db,
            "content_variant_performance_updated",
            "webhook_immediate",
            {"content_id": str(content_id), "variant_id": str(variant_id)},
        )

    async def _convert_flow_to_dict(self, db: AsyncSession, flow) -> Dict[str, Any]:
        """Convert flow object to dict with proper info field consistency."""
        # Ensure the flow object is fully loaded in this async context
        if hasattr(flow, "refresh") and callable(getattr(flow, "refresh")):
            await db.refresh(flow)

        info = {}
        if hasattr(flow, "info") and flow.info:
            # Handle SQLAlchemy MutableDict conversion safely in async context
            info = dict(flow.info) if hasattr(flow.info, "items") else {}

        return {
            "id": str(flow.id),
            "name": flow.name,
            "description": flow.description,
            "version": flow.version,
            "flow_data": flow.flow_data,
            "entry_node_id": flow.entry_node_id,
            "info": info,
            "is_published": flow.is_published,
            "is_active": flow.is_active,
            "created_at": flow.created_at.isoformat()
            if hasattr(flow, "created_at")
            else None,
            "updated_at": flow.updated_at.isoformat()
            if hasattr(flow, "updated_at")
            else None,
            "published_at": flow.published_at.isoformat()
            if hasattr(flow, "published_at") and flow.published_at
            else None,
            "published_by": str(flow.published_by)
            if hasattr(flow, "published_by") and flow.published_by
            else None,
        }
