"""Trace cleanup service for managing trace data retention.

Provides batched deletion of old execution traces based on flow retention settings.
"""

import asyncio
import logging
from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TraceCleanupService:
    """Manages trace data retention and cleanup."""

    DEFAULT_RETENTION_DAYS = 30
    BATCH_SIZE = 1000
    BATCH_DELAY_SECONDS = 0.1

    async def cleanup_old_traces(self, db: AsyncSession) -> int:
        """Delete old traces in batches based on flow retention settings.

        Returns total deleted count.
        """
        deleted_total = 0

        while True:
            # Delete in batches to avoid long-running transactions
            result = await db.execute(
                text("""
                    DELETE FROM flow_execution_steps
                    WHERE id IN (
                        SELECT fes.id FROM flow_execution_steps fes
                        JOIN conversation_sessions cs ON cs.id = fes.session_id
                        JOIN flow_definitions fd ON fd.id = cs.flow_id
                        WHERE fes.started_at < NOW() - INTERVAL '1 day' * COALESCE(fd.retention_days, :default_days)
                        LIMIT :batch_size
                    )
                """),
                {
                    "default_days": self.DEFAULT_RETENTION_DAYS,
                    "batch_size": self.BATCH_SIZE,
                },
            )

            deleted = result.rowcount
            deleted_total += deleted
            await db.commit()

            logger.info(
                "Trace cleanup batch completed",
                extra={"deleted_batch": deleted, "total_deleted": deleted_total},
            )

            if deleted < self.BATCH_SIZE:
                break

            # Small delay between batches to reduce DB load
            await asyncio.sleep(self.BATCH_DELAY_SECONDS)

        logger.info("Trace cleanup completed", extra={"total_deleted": deleted_total})
        return deleted_total

    async def cleanup_audit_logs(
        self, db: AsyncSession, retention_days: int = 90
    ) -> int:
        """Clean up old trace access audit logs.

        Audit logs are kept longer than traces for compliance.
        """
        deleted_total = 0

        while True:
            result = await db.execute(
                text("""
                    DELETE FROM trace_access_audit
                    WHERE id IN (
                        SELECT id FROM trace_access_audit
                        WHERE accessed_at < NOW() - INTERVAL '1 day' * :retention_days
                        LIMIT :batch_size
                    )
                """),
                {"retention_days": retention_days, "batch_size": self.BATCH_SIZE},
            )

            deleted = result.rowcount
            deleted_total += deleted
            await db.commit()

            if deleted < self.BATCH_SIZE:
                break

            await asyncio.sleep(self.BATCH_DELAY_SECONDS)

        logger.info(
            "Audit log cleanup completed", extra={"total_deleted": deleted_total}
        )
        return deleted_total

    async def get_storage_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Get trace storage statistics for monitoring."""
        result = await db.execute(
            text("""
            SELECT
                COUNT(*) as total_traces,
                pg_size_pretty(pg_total_relation_size('flow_execution_steps')) as table_size,
                MIN(started_at) as oldest_trace,
                MAX(started_at) as newest_trace
            FROM flow_execution_steps
        """)
        )
        row = result.fetchone()

        if not row:
            return {
                "total_traces": 0,
                "table_size": "0 bytes",
                "oldest_trace": None,
                "newest_trace": None,
            }

        return {
            "total_traces": row.total_traces,
            "table_size": row.table_size,
            "oldest_trace": row.oldest_trace.isoformat() if row.oldest_trace else None,
            "newest_trace": row.newest_trace.isoformat() if row.newest_trace else None,
        }

    async def get_flow_trace_stats(
        self, db: AsyncSession, flow_id: str
    ) -> Dict[str, Any]:
        """Get trace statistics for a specific flow."""
        result = await db.execute(
            text("""
            SELECT
                COUNT(DISTINCT fes.session_id) as traced_sessions,
                COUNT(*) as total_steps,
                AVG(fes.duration_ms) as avg_step_duration_ms,
                COUNT(CASE WHEN fes.error_message IS NOT NULL THEN 1 END) as error_steps,
                MIN(fes.started_at) as oldest_trace,
                MAX(fes.started_at) as newest_trace
            FROM flow_execution_steps fes
            JOIN conversation_sessions cs ON cs.id = fes.session_id
            WHERE cs.flow_id = :flow_id
        """),
            {"flow_id": flow_id},
        )
        row = result.fetchone()

        if not row:
            return {
                "traced_sessions": 0,
                "total_steps": 0,
                "avg_step_duration_ms": None,
                "error_steps": 0,
                "oldest_trace": None,
                "newest_trace": None,
            }

        return {
            "traced_sessions": row.traced_sessions,
            "total_steps": row.total_steps,
            "avg_step_duration_ms": float(row.avg_step_duration_ms)
            if row.avg_step_duration_ms
            else None,
            "error_steps": row.error_steps,
            "oldest_trace": row.oldest_trace.isoformat() if row.oldest_trace else None,
            "newest_trace": row.newest_trace.isoformat() if row.newest_trace else None,
        }


# Module-level instance
trace_cleanup_service = TraceCleanupService()
