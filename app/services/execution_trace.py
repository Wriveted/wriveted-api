"""Execution trace service for session replay functionality.

Provides async trace recording, retrieval, and management with PII masking.
"""

import copy
import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cms import (
    ConversationSession,
    FlowDefinition,
    FlowExecutionStep,
    TraceAccessAudit,
    TraceLevel,
)
from app.services.pii_masker import PIIMasker

logger = logging.getLogger(__name__)


class ExecutionTraceService:
    """Service for capturing and managing execution traces asynchronously."""

    def __init__(self):
        self.pii_masker = PIIMasker()
        self._buffer: List[dict] = []
        self._buffer_size = 10

    async def should_trace_session(
        self,
        db: AsyncSession,
        flow_id: UUID,
        session_token: str,
    ) -> bool:
        """Determine if tracing should be enabled for this session.

        Uses flow-level config and sample rate for deterministic sampling.
        """
        result = await db.execute(
            select(
                FlowDefinition.trace_enabled, FlowDefinition.trace_sample_rate
            ).where(FlowDefinition.id == flow_id)
        )
        row = result.first()

        if not row or not row.trace_enabled:
            return False

        sample_rate = row.trace_sample_rate
        if sample_rate >= 100:
            return True
        if sample_rate <= 0:
            return False

        # Deterministic sampling based on session token
        hash_value = int(hashlib.md5(session_token.encode()).hexdigest(), 16)
        return (hash_value % 100) < sample_rate

    def get_trace_level(self, flow: FlowDefinition) -> TraceLevel:
        """Get trace level for a flow based on environment and config."""
        # Default to standard, could be made configurable per-flow
        return TraceLevel.STANDARD

    async def record_step(
        self,
        db: AsyncSession,
        session_id: UUID,
        node_id: str,
        node_type: str,
        step_number: int,
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        execution_details: Dict[str, Any],
        connection_type: Optional[str] = None,
        next_node_id: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> FlowExecutionStep:
        """Record a single execution step directly to database.

        State is PII-masked before storage.
        """
        # Mask PII in state snapshots
        masked_before = self.pii_masker.mask_state(state_before)
        masked_after = self.pii_masker.mask_state(state_after)

        step = FlowExecutionStep(
            session_id=session_id,
            node_id=node_id,
            node_type=node_type,
            step_number=step_number,
            state_before=masked_before,
            state_after=masked_after,
            execution_details=execution_details,
            connection_type=connection_type,
            next_node_id=next_node_id,
            started_at=started_at or datetime.utcnow(),
            completed_at=completed_at,
            duration_ms=duration_ms,
            error_message=error_message,
            error_details=error_details,
        )

        db.add(step)
        await db.flush()

        return step

    async def record_step_async(
        self,
        session_id: UUID,
        node_id: str,
        node_type: str,
        step_number: int,
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        execution_details: Dict[str, Any],
        **kwargs,
    ):
        """Queue trace recording for async processing - non-blocking.

        Buffers traces and flushes when buffer is full or session ends.
        """
        # Mask PII before buffering
        masked_before = self.pii_masker.mask_state(state_before)
        masked_after = self.pii_masker.mask_state(state_after)

        trace_data = {
            "session_id": str(session_id),
            "node_id": node_id,
            "node_type": node_type,
            "step_number": step_number,
            "state_before": masked_before,
            "state_after": masked_after,
            "execution_details": execution_details,
            **kwargs,
        }

        self._buffer.append(trace_data)

        # Flush if buffer full or session ending
        if len(self._buffer) >= self._buffer_size or kwargs.get("session_ending"):
            await self._flush_buffer()

    async def _flush_buffer(self):
        """Flush buffered traces to background task queue."""
        if not self._buffer:
            return

        traces_to_flush = self._buffer.copy()
        self._buffer.clear()

        # In production, this would queue to Cloud Tasks
        # For now, log that we would queue these
        logger.info(
            "Would queue %d traces for background recording",
            len(traces_to_flush),
        )

    async def get_session_trace(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> Dict[str, Any]:
        """Get full execution trace for a session.

        Returns session metadata and all execution steps in order.
        """
        # Get session
        session_result = await db.execute(
            select(ConversationSession).where(ConversationSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Get execution steps
        steps_result = await db.execute(
            select(FlowExecutionStep)
            .where(FlowExecutionStep.session_id == session_id)
            .order_by(FlowExecutionStep.step_number)
        )
        steps = steps_result.scalars().all()

        # Calculate total duration
        total_duration_ms = sum(s.duration_ms or 0 for s in steps)

        return {
            "session": {
                "id": str(session.id),
                "session_token": session.session_token,
                "user_id": str(session.user_id) if session.user_id else None,
                "flow_id": str(session.flow_id),
                "status": session.status.value,
                "started_at": session.started_at.isoformat()
                if session.started_at
                else None,
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            },
            "steps": [
                {
                    "id": str(step.id),
                    "step_number": step.step_number,
                    "node_id": step.node_id,
                    "node_type": step.node_type,
                    "state_before": step.state_before,
                    "state_after": step.state_after,
                    "execution_details": step.execution_details,
                    "connection_type": step.connection_type,
                    "next_node_id": step.next_node_id,
                    "duration_ms": step.duration_ms,
                    "started_at": step.started_at.isoformat()
                    if step.started_at
                    else None,
                    "completed_at": step.completed_at.isoformat()
                    if step.completed_at
                    else None,
                    "error_message": step.error_message,
                    "error_details": step.error_details,
                }
                for step in steps
            ],
            "total_steps": len(steps),
            "total_duration_ms": total_duration_ms,
        }

    async def list_flow_sessions(
        self,
        db: AsyncSession,
        flow_id: UUID,
        status: Optional[str] = None,
        user_id: Optional[UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        has_errors: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List sessions for a flow with filtering and pagination."""
        # Build base query
        query = select(ConversationSession).where(
            ConversationSession.flow_id == flow_id
        )

        # Apply filters
        if status:
            query = query.where(ConversationSession.status == status)
        if user_id:
            query = query.where(ConversationSession.user_id == user_id)
        if from_date:
            query = query.where(ConversationSession.started_at >= from_date)
        if to_date:
            query = query.where(ConversationSession.started_at <= to_date)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(desc(ConversationSession.started_at))
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        sessions = result.scalars().all()

        # Build response with summaries
        items = []
        for session in sessions:
            # Get step count and error status
            step_info = await db.execute(
                select(
                    func.count(FlowExecutionStep.id).label("total_steps"),
                    func.count(FlowExecutionStep.error_message)
                    .filter(FlowExecutionStep.error_message.isnot(None))
                    .label("error_count"),
                ).where(FlowExecutionStep.session_id == session.id)
            )
            step_row = step_info.first()

            total_steps = step_row.total_steps if step_row else 0
            has_errors_flag = (step_row.error_count or 0) > 0 if step_row else False

            # Filter by has_errors if specified
            if has_errors is not None and has_errors != has_errors_flag:
                continue

            # Get path summary (first N node IDs)
            path_result = await db.execute(
                select(FlowExecutionStep.node_id)
                .where(FlowExecutionStep.session_id == session.id)
                .order_by(FlowExecutionStep.step_number)
                .limit(10)
            )
            path_summary = [row.node_id for row in path_result.all()]

            items.append(
                {
                    "id": str(session.id),
                    "session_token": session.session_token,
                    "user_id": str(session.user_id) if session.user_id else None,
                    "flow_id": str(session.flow_id),
                    "status": session.status.value,
                    "started_at": session.started_at.isoformat()
                    if session.started_at
                    else None,
                    "ended_at": session.ended_at.isoformat()
                    if session.ended_at
                    else None,
                    "total_steps": total_steps,
                    "has_errors": has_errors_flag,
                    "error_count": step_row.error_count or 0 if step_row else 0,
                    "path_summary": path_summary,
                }
            )

        # When has_errors filter is applied, recalculate total based on filtered items
        # (since filtering happens post-query)
        actual_total = len(items) if has_errors is not None else total

        return {
            "items": items,
            "total": actual_total,
            "limit": limit,
            "offset": offset,
        }

    async def get_next_step_number(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> int:
        """Get the next step number for a session."""
        result = await db.execute(
            select(func.max(FlowExecutionStep.step_number)).where(
                FlowExecutionStep.session_id == session_id
            )
        )
        max_step = result.scalar()
        return (max_step or 0) + 1

    def build_execution_details(
        self,
        node_type: str,
        result: Dict[str, Any],
        node_content: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build typed execution details based on node type."""
        node_type_lower = node_type.lower()

        if node_type_lower == "condition":
            return self._build_condition_details(result, node_content)
        elif node_type_lower == "script":
            return self._build_script_details(result, node_content)
        elif node_type_lower == "question":
            return self._build_question_details(result, node_content)
        elif node_type_lower == "message":
            return self._build_message_details(result, node_content)
        elif node_type_lower == "action":
            return self._build_action_details(result, node_content)
        elif node_type_lower == "webhook":
            return self._build_webhook_details(result, node_content)
        else:
            return {"type": node_type_lower, "raw": result}

    def _build_condition_details(
        self, result: Dict[str, Any], content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build condition execution details."""
        conditions_evaluated = []
        for i, cond in enumerate(content.get("conditions", [])):
            expr = cond.get("if", {})
            conditions_evaluated.append(
                {
                    "index": i,
                    "expression": str(expr),
                    "result": result.get("condition_results", {}).get(str(i), False),
                    "error": result.get("condition_errors", {}).get(str(i)),
                }
            )

        return {
            "type": "condition",
            "conditions_evaluated": conditions_evaluated,
            "matched_condition_index": result.get("matched_index"),
            "connection_taken": result.get("connection_type", "default"),
        }

    def _build_script_details(
        self, result: Dict[str, Any], content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build script execution details."""
        code = content.get("code", "")
        return {
            "type": "script",
            "language": content.get("language", "javascript"),
            "code_preview": code[:500] if code else "",
            "inputs": result.get("inputs", {}),
            "outputs": result.get("outputs", {}),
            "console_logs": result.get("console_logs", [])[:100],
            "error": result.get("error"),
            "execution_time_ms": result.get("execution_time_ms"),
        }

    def _build_question_details(
        self, result: Dict[str, Any], content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build question execution details."""
        return {
            "type": "question",
            "question_text": content.get("question", content.get("text", "")),
            "rendered_question": result.get("rendered_question", ""),
            "options": content.get("options"),
            "user_response": result.get("user_response"),
            "response_time_ms": result.get("response_time_ms"),
            "input_type": content.get("input_type", "text"),
        }

    def _build_message_details(
        self, result: Dict[str, Any], content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build message execution details."""
        return {
            "type": "message",
            "message_template": content.get("text", content.get("rich_text", "")),
            "rendered_message": result.get("rendered_message", ""),
            "media_urls": content.get("media_urls", []),
        }

    def _build_action_details(
        self, result: Dict[str, Any], content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build action execution details."""
        return {
            "type": "action",
            "action_type": content.get("action_type", ""),
            "actions_executed": result.get("actions_executed", []),
            "variables_changed": result.get("variables_changed", {}),
        }

    def _build_webhook_details(
        self, result: Dict[str, Any], content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build webhook execution details with sensitive data redacted."""
        # Redact auth headers
        safe_headers = {}
        for key, value in result.get("request_headers", {}).items():
            if key.lower() in ("authorization", "x-api-key", "cookie", "x-auth-token"):
                safe_headers[key] = "[REDACTED]"
            else:
                safe_headers[key] = value

        # Truncate large response bodies
        response_body = result.get("response_body", {})
        if len(str(response_body)) > 1024:
            response_body = {
                "_truncated": True,
                "_size_bytes": len(str(response_body)),
                "_preview": str(response_body)[:500],
            }

        return {
            "type": "webhook",
            "url": self.pii_masker.mask_url_credentials(content.get("url", "")),
            "method": content.get("method", "POST"),
            "request_headers": safe_headers,
            "response_status": result.get("response_status"),
            "response_body": response_body,
            "duration_ms": result.get("duration_ms"),
            "error": result.get("error"),
        }

    def efficient_state_copy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Efficient state copy - shallow for primitives, deep for mutables."""
        if not state:
            return {}

        result = {}
        for key, value in state.items():
            if isinstance(value, (dict, list)):
                result[key] = copy.deepcopy(value)
            else:
                result[key] = value
        return result


class TraceAuditService:
    """Audit logging for trace access."""

    async def log_access(
        self,
        db: AsyncSession,
        session_id: UUID,
        accessed_by: UUID,
        access_type: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        data_accessed: Optional[Dict[str, Any]] = None,
    ):
        """Log access to trace data."""
        audit = TraceAccessAudit(
            session_id=session_id,
            accessed_by=accessed_by,
            access_type=access_type,
            ip_address=ip_address,
            user_agent=user_agent,
            data_accessed=data_accessed,
        )
        db.add(audit)
        await db.flush()

        logger.info(
            "Trace accessed",
            extra={
                "session_id": str(session_id),
                "accessed_by": str(accessed_by),
                "access_type": access_type,
            },
        )


# Module-level instances for convenience
execution_trace_service = ExecutionTraceService()
trace_audit_service = TraceAuditService()
