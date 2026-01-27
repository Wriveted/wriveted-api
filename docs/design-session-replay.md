# Session Replay / Introspection Feature Design

> **Document Type**: Design Document → Implementation Guide
>
> **Last Updated**: December 2024

## Implementation Status

| Component | Status |
|-----------|--------|
| `FlowExecutionStep` model | ✅ Implemented |
| `TraceAccessAudit` model | ✅ Implemented |
| Database migrations | ✅ Implemented |
| Execution trace schemas | ✅ Implemented |
| API endpoints | ✅ Implemented |
| `ExecutionTraceService` | ✅ Implemented |
| PII masking service | ✅ Implemented |
| **Chat runtime integration** | ✅ Implemented |
| ACL access control | ❌ Not implemented |
| Frontend replay viewer | ✅ Implemented (admin-ui) |
| Async trace queueing | ⚠️ Partial (buffered, not yet queued) |

> **Note**: `chat_runtime.py` now records execution traces and sets `trace_enabled` during session start based on flow tracing configuration.

## Overview

Enable detailed introspection of any conversation session to understand the execution path,
variable state at each step, and why specific branches were taken. This is critical for:
- **Debugging**: "Why did user X get this response?"
- **QA/Testing**: Verify flows work as intended
- **Analytics**: Understand user journeys in detail
- **Support**: Investigate user-reported issues

## Architecture

### Data Model

#### New Table: `flow_execution_steps`

Captures detailed execution data for each node visit during a session.

```sql
CREATE TABLE flow_execution_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,

    -- Node identification
    node_id VARCHAR(255) NOT NULL,
    node_type VARCHAR(50) NOT NULL,  -- MESSAGE, QUESTION, CONDITION, ACTION, SCRIPT, etc.

    -- Execution sequence
    step_number INTEGER NOT NULL,

    -- State snapshots (PII-masked, see PIIMasker service)
    state_before JSONB NOT NULL DEFAULT '{}',
    state_after JSONB NOT NULL DEFAULT '{}',

    -- Node-specific execution details (typed per node, see Pydantic schemas)
    execution_details JSONB NOT NULL DEFAULT '{}',

    -- Connection taken to next node
    connection_type VARCHAR(50),  -- 'default', '$0', '$1', etc.
    next_node_id VARCHAR(255),

    -- Timing
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,

    -- Error tracking
    error_message TEXT,
    error_details JSONB,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_exec_steps_session ON flow_execution_steps(session_id);
CREATE INDEX idx_exec_steps_session_step ON flow_execution_steps(session_id, step_number);
CREATE INDEX idx_exec_steps_node ON flow_execution_steps(node_id);
CREATE INDEX idx_exec_steps_started ON flow_execution_steps(started_at DESC);

-- Additional indexes for common queries (from review feedback)
CREATE INDEX idx_exec_steps_flow_date ON flow_execution_steps(session_id, started_at DESC)
    WHERE completed_at IS NOT NULL;
CREATE INDEX idx_exec_steps_errors ON flow_execution_steps(session_id, node_id)
    WHERE error_message IS NOT NULL;
```

#### Updates to Existing Tables

**ConversationSession** - add tracing fields:
```sql
ALTER TABLE conversation_sessions ADD COLUMN
    trace_enabled BOOLEAN NOT NULL DEFAULT false,
    trace_level VARCHAR(20) DEFAULT 'standard';  -- 'minimal', 'standard', 'verbose'
```

#### New Table: `trace_access_audit`

Track who accesses sensitive trace data:
```sql
CREATE TABLE trace_access_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id),
    accessed_by UUID NOT NULL REFERENCES users(id),
    access_type VARCHAR(50) NOT NULL,  -- 'view_trace', 'export', 'list'
    accessed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,
    data_accessed JSONB  -- which steps/fields were accessed
);

CREATE INDEX idx_trace_audit_session ON trace_access_audit(session_id);
CREATE INDEX idx_trace_audit_user ON trace_access_audit(accessed_by);
CREATE INDEX idx_trace_audit_time ON trace_access_audit(accessed_at DESC);
```

---

## Trace Levels Definition

| Level | Node Visits | Connections | State Snapshots | Execution Details | Use Case |
|-------|-------------|-------------|-----------------|-------------------|----------|
| **minimal** | Yes | Yes | No | No | Production monitoring, path analytics |
| **standard** | Yes | Yes | Yes (masked) | Summary only | Debugging, support |
| **verbose** | Yes | Yes | Yes (masked) | Full details | Development, deep debugging |

**Default**: `standard` for new sessions
**Admin override**: Can enable `verbose` for specific sessions/flows

---

## Security Implementation

### 1. PII Masking Service

```python
# app/services/pii_masker.py

from typing import Any, Dict, Set
import re
import hashlib

class PIIMasker:
    """Mask personally identifiable information in trace data."""

    # Keys that should always be masked
    SENSITIVE_KEYS: Set[str] = {
        'email', 'phone', 'telephone', 'mobile',
        'address', 'street', 'postcode', 'zipcode',
        'ssn', 'social_security',
        'password', 'secret', 'token', 'api_key',
        'parent_name', 'parent_email', 'guardian',
        'student_name', 'child_name', 'full_name',
        'date_of_birth', 'dob', 'birthday',
        'credit_card', 'card_number', 'cvv',
    }

    # Patterns to detect and mask
    EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    PHONE_PATTERN = re.compile(r'\+?[\d\s\-\(\)]{10,}')

    def __init__(self, mask_char: str = '*', preserve_length: bool = True):
        self.mask_char = mask_char
        self.preserve_length = preserve_length

    def mask_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively mask PII in state dictionary."""
        if not state:
            return {}
        return self._mask_recursive(state)

    def _mask_recursive(self, obj: Any, parent_key: str = '') -> Any:
        if isinstance(obj, dict):
            return {
                key: self._mask_recursive(value, key)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [self._mask_recursive(item, parent_key) for item in obj]
        elif isinstance(obj, str):
            return self._mask_string(obj, parent_key)
        return obj

    def _mask_string(self, value: str, key: str) -> str:
        # Check if key indicates sensitive data
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in self.SENSITIVE_KEYS):
            return self._mask_value(value)

        # Check for email/phone patterns in value
        if self.EMAIL_PATTERN.search(value):
            return self.EMAIL_PATTERN.sub('[EMAIL]', value)
        if self.PHONE_PATTERN.search(value):
            return self.PHONE_PATTERN.sub('[PHONE]', value)

        return value

    def _mask_value(self, value: str) -> str:
        if self.preserve_length:
            return self.mask_char * len(value)
        return f"[MASKED:{hashlib.sha256(value.encode()).hexdigest()[:8]}]"


# Usage in trace service
pii_masker = PIIMasker()
masked_state = pii_masker.mask_state(session.state)
```

### 2. Access Control with ACL Integration

```python
# app/models/cms.py (addition to FlowExecutionStep)

class FlowExecutionStep(Base):
    # ... existing fields ...

    def __acl__(self) -> List[tuple]:
        """Access control for execution traces.

        Traces inherit permissions from their flow, with additional restrictions:
        - Only admins and flow owners can view traces
        - School admins can only see traces from their school's flows
        - Audit logging is required for all access
        """
        acls = [
            (Allow, "role:admin", All),
            (Allow, "role:wriveted", All),  # Internal staff
        ]

        # Inherit from session's flow
        if self.session and self.session.flow:
            flow = self.session.flow
            if flow.created_by:
                acls.append((Allow, f"user:{flow.created_by}", "read"))

        # School-scoped access
        if self.session and self.session.user:
            user = self.session.user
            if hasattr(user, 'school_id') and user.school_id:
                acls.append((Allow, f"school-admin:{user.school_id}", "read"))

        return acls
```

### 3. Audit Logging Middleware

```python
# app/services/trace_audit.py

from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

class TraceAuditService:
    """Audit logging for trace access."""

    async def log_access(
        self,
        db: AsyncSession,
        session_id: UUID,
        accessed_by: UUID,
        access_type: str,
        request: Request,
        data_accessed: dict = None,
    ):
        """Log access to trace data."""
        audit = TraceAccessAudit(
            session_id=session_id,
            accessed_by=accessed_by,
            access_type=access_type,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent'),
            data_accessed=data_accessed,
        )
        db.add(audit)
        await db.flush()

        # Also emit structured log for monitoring
        logger.info(
            "Trace accessed",
            session_id=str(session_id),
            accessed_by=str(accessed_by),
            access_type=access_type,
        )
```

### 4. Webhook Data Redaction

```python
# In execution details building for WEBHOOK nodes

def _build_webhook_details(self, result: dict) -> WebhookExecutionDetails:
    """Build webhook execution details with sensitive data redacted."""

    # Redact auth headers
    safe_headers = {}
    for key, value in result.get('request_headers', {}).items():
        if key.lower() in ('authorization', 'x-api-key', 'cookie'):
            safe_headers[key] = '[REDACTED]'
        else:
            safe_headers[key] = value

    # Truncate large response bodies
    response_body = result.get('response_body', {})
    if len(str(response_body)) > 1024:
        response_body = {
            '_truncated': True,
            '_size_bytes': len(str(response_body)),
            '_preview': str(response_body)[:500],
        }

    return WebhookExecutionDetails(
        url=self._mask_url_credentials(result.get('url', '')),
        method=result.get('method', 'POST'),
        request_headers=safe_headers,
        response_status=result.get('response_status'),
        response_body=response_body,
        duration_ms=result.get('duration_ms'),
    )
```

---

## Performance Implementation

### 1. Async/Background Trace Recording

**Critical**: Trace recording MUST NOT block the chat flow.

```python
# app/services/execution_trace.py

from app.services.cloud_tasks import CloudTasksService

class ExecutionTraceService:
    """Service for capturing execution traces asynchronously."""

    def __init__(self):
        self.cloud_tasks = CloudTasksService()
        self.pii_masker = PIIMasker()
        self._buffer: List[dict] = []
        self._buffer_size = 10

    async def record_step_async(
        self,
        session_id: UUID,
        node_id: str,
        node_type: NodeType,
        step_number: int,
        state_before: dict,
        state_after: dict,
        execution_details: dict,
        **kwargs,
    ):
        """Queue trace recording as background task - non-blocking."""

        # Mask PII before queuing
        masked_before = self.pii_masker.mask_state(state_before)
        masked_after = self.pii_masker.mask_state(state_after)

        trace_data = {
            'session_id': str(session_id),
            'node_id': node_id,
            'node_type': node_type.value,
            'step_number': step_number,
            'state_before': masked_before,
            'state_after': masked_after,
            'execution_details': execution_details,
            **kwargs,
        }

        # Add to buffer
        self._buffer.append(trace_data)

        # Flush if buffer full or session ending
        if len(self._buffer) >= self._buffer_size or kwargs.get('session_ending'):
            await self._flush_buffer()

    async def _flush_buffer(self):
        """Flush buffered traces to background task queue."""
        if not self._buffer:
            return

        traces_to_flush = self._buffer.copy()
        self._buffer.clear()

        try:
            # Queue as Cloud Task for async processing
            await self.cloud_tasks.create_task(
                queue_name='trace-recording',
                task_name=f'traces-{uuid.uuid4()}',
                payload={'traces': traces_to_flush},
                handler_path='/internal/tasks/record-traces',
            )
        except Exception as e:
            # Never fail chat flow due to trace recording
            logger.error("Failed to queue trace recording", error=str(e))
            # Store in Redis for retry (fallback)
            await self._store_failed_traces(traces_to_flush)
```

### 2. Integration with Chat Runtime (Non-Blocking)

```python
# app/services/chat_runtime.py

async def process(self, db, node, session, context):
    """Process node with non-blocking trace recording."""

    trace_service = ExecutionTraceService()

    # Shallow copy for performance (only deep copy nested mutables)
    state_before = self._efficient_state_copy(session.state)
    started_at = datetime.utcnow()

    try:
        # Execute node logic (main path)
        result = await self._execute_node_logic(db, node, session, context)

        state_after = self._efficient_state_copy(session.state)
        duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)

        # NON-BLOCKING: Queue trace for async recording
        # This returns immediately, doesn't wait for DB write
        asyncio.create_task(
            self._record_trace_safe(
                trace_service, session, node, state_before, state_after,
                result, duration_ms
            )
        )

        return result

    except Exception as e:
        # Record error trace (also non-blocking)
        asyncio.create_task(
            self._record_error_trace_safe(
                trace_service, session, node, state_before, e
            )
        )
        raise

async def _record_trace_safe(self, trace_service, session, node,
                              state_before, state_after, result, duration_ms):
    """Safe wrapper for trace recording - never raises."""
    try:
        if session.trace_enabled:
            await trace_service.record_step_async(
                session_id=session.id,
                node_id=node.node_id,
                node_type=node.node_type,
                step_number=await self._get_step_number(session.id),
                state_before=state_before,
                state_after=state_after,
                execution_details=self._build_execution_details(node, result),
                connection_type=result.get('connection_type'),
                next_node_id=result.get('next_node_id'),
                duration_ms=duration_ms,
            )
    except Exception as e:
        logger.error("Trace recording failed silently",
                     error=str(e), session_id=str(session.id))

def _efficient_state_copy(self, state: dict) -> dict:
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
```

---

## Typed Execution Details Schemas

```python
# app/schemas/execution_trace.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime

class ConditionEval(BaseModel):
    index: int
    expression: str
    result: bool
    error: Optional[str] = None

class ConditionExecutionDetails(BaseModel):
    type: Literal["condition"] = "condition"
    conditions_evaluated: List[ConditionEval]
    matched_condition_index: Optional[int] = None
    connection_taken: str

class ScriptExecutionDetails(BaseModel):
    type: Literal["script"] = "script"
    language: Literal["javascript", "typescript"]
    code_preview: str = Field(max_length=500)  # First 500 chars
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    console_logs: List[str] = Field(default_factory=list, max_length=100)
    error: Optional[str] = None
    execution_time_ms: int

class QuestionExecutionDetails(BaseModel):
    type: Literal["question"] = "question"
    question_text: str
    rendered_question: str  # After variable substitution
    options: Optional[List[str]] = None
    user_response: Optional[str] = None
    response_time_ms: Optional[int] = None
    input_type: str = "text"  # text, choice, etc.

class MessageExecutionDetails(BaseModel):
    type: Literal["message"] = "message"
    message_template: str
    rendered_message: str  # After variable substitution
    media_urls: List[str] = Field(default_factory=list)

class ActionExecutionDetails(BaseModel):
    type: Literal["action"] = "action"
    action_type: str
    actions_executed: List[Dict[str, Any]]
    variables_changed: Dict[str, Dict[str, Any]]  # {path: {old, new}}

class WebhookExecutionDetails(BaseModel):
    type: Literal["webhook"] = "webhook"
    url: str  # Credentials masked
    method: str
    request_headers: Dict[str, str]  # Auth headers redacted
    response_status: Optional[int] = None
    response_body: Optional[Dict[str, Any]] = None  # Truncated if large
    duration_ms: Optional[int] = None
    error: Optional[str] = None

# Union type for execution details
ExecutionDetails = (
    ConditionExecutionDetails |
    ScriptExecutionDetails |
    QuestionExecutionDetails |
    MessageExecutionDetails |
    ActionExecutionDetails |
    WebhookExecutionDetails
)

# Response schemas
class ExecutionStepResponse(BaseModel):
    step_number: int
    node_id: str
    node_type: str
    state_before: Dict[str, Any]
    state_after: Dict[str, Any]
    execution_details: Dict[str, Any]
    connection_type: Optional[str]
    next_node_id: Optional[str]
    duration_ms: Optional[int]
    started_at: datetime
    error_message: Optional[str] = None

class SessionTraceResponse(BaseModel):
    session: Dict[str, Any]
    steps: List[ExecutionStepResponse]
    total_steps: int
    total_duration_ms: int
```

---

## API Endpoints

### 1. List Session Executions for a Flow
```
GET /v1/cms/flows/{flow_id}/sessions
```

Query params:
- `status`: Filter by session status (active, completed, abandoned)
- `user_id`: Filter by user
- `from_date`, `to_date`: Date range
- `has_errors`: Filter sessions with/without errors
- `limit`, `offset`: Pagination

Response:
```json
{
    "items": [
        {
            "id": "uuid",
            "session_token": "...",
            "user_id": "uuid",
            "status": "completed",
            "started_at": "2025-01-15T10:30:00Z",
            "ended_at": "2025-01-15T10:35:00Z",
            "total_steps": 12,
            "has_errors": false,
            "path_summary": ["welcome", "ask_genre", "check_genre", "fantasy_path", "end"]
        }
    ],
    "total": 150,
    "limit": 20,
    "offset": 0
}
```

### 2. Get Full Session Trace
```
GET /v1/cms/sessions/{session_id}/trace
```

**Requires audit logging** - access is recorded.

### 3. Enable/Disable Tracing for a Flow
```
POST /v1/cms/flows/{flow_id}/tracing
```

Body:
```json
{
    "enabled": true,
    "level": "standard",
    "sample_rate": 0.1  // Enable for 10% of sessions (for gradual rollout)
}
```

### 4. Get Aggregate Path Analytics
```
GET /v1/cms/flows/{flow_id}/paths
```

---

## Data Retention & Cleanup

### Cleanup Service

```python
# app/services/trace_cleanup.py

class TraceCleanupService:
    """Manages trace data retention and cleanup."""

    DEFAULT_RETENTION_DAYS = 30
    BATCH_SIZE = 1000

    async def cleanup_old_traces(self, db: AsyncSession) -> int:
        """Delete old traces in batches. Returns total deleted count."""
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
                {'default_days': self.DEFAULT_RETENTION_DAYS, 'batch_size': self.BATCH_SIZE}
            )

            deleted = result.rowcount
            deleted_total += deleted
            await db.commit()

            # Emit metric
            metrics.counter("trace_cleanup.deleted_batch", deleted)

            if deleted < self.BATCH_SIZE:
                break

            # Small delay between batches to reduce DB load
            await asyncio.sleep(0.1)

        logger.info("Trace cleanup completed", total_deleted=deleted_total)
        metrics.gauge("trace_cleanup.total_deleted", deleted_total)

        return deleted_total

    async def get_storage_stats(self, db: AsyncSession) -> dict:
        """Get trace storage statistics for monitoring."""
        result = await db.execute(text("""
            SELECT
                COUNT(*) as total_traces,
                pg_size_pretty(pg_total_relation_size('flow_execution_steps')) as table_size,
                MIN(started_at) as oldest_trace,
                MAX(started_at) as newest_trace
            FROM flow_execution_steps
        """))
        row = result.fetchone()
        return {
            'total_traces': row.total_traces,
            'table_size': row.table_size,
            'oldest_trace': row.oldest_trace,
            'newest_trace': row.newest_trace,
        }
```

### Cloud Scheduler Job

```yaml
# terraform/cloud_scheduler.tf or deployment config

resource "google_cloud_scheduler_job" "trace_cleanup" {
  name        = "trace-cleanup-daily"
  description = "Clean up old execution traces"
  schedule    = "0 3 * * *"  # 3 AM daily
  time_zone   = "UTC"

  http_target {
    uri         = "${var.internal_api_url}/internal/tasks/cleanup-traces"
    http_method = "POST"
    headers = {
      "Authorization" = "Bearer ${var.internal_service_token}"
    }
  }

  retry_config {
    retry_count          = 3
    min_backoff_duration = "30s"
    max_backoff_duration = "300s"
  }
}
```

---

## Feature Flags & Gradual Rollout

```python
# app/services/feature_flags.py

class TraceFeatureFlags:
    """Feature flags for trace functionality."""

    @classmethod
    async def is_tracing_enabled(cls, flow_id: UUID, session_token: str) -> bool:
        """Check if tracing is enabled for this flow/session."""
        # Check flow-level setting first
        flow_config = await cls._get_flow_trace_config(flow_id)

        if not flow_config.get('enabled', False):
            return False

        # Apply sample rate
        sample_rate = flow_config.get('sample_rate', 1.0)
        if sample_rate < 1.0:
            # Deterministic sampling based on session token
            hash_value = int(hashlib.md5(session_token.encode()).hexdigest(), 16)
            if (hash_value % 100) >= (sample_rate * 100):
                return False

        return True

    @classmethod
    def get_trace_level(cls, flow_id: UUID) -> TraceLevel:
        """Get trace level for a flow."""
        # Could be environment-based or per-flow config
        if settings.ENVIRONMENT == 'production':
            return TraceLevel.STANDARD
        return TraceLevel.VERBOSE
```

---

## Monitoring & Alerting

```python
# Metrics to emit

# Recording performance
metrics.histogram("trace.record_step.duration_ms", duration)
metrics.counter("trace.record_step.success")
metrics.counter("trace.record_step.failure")

# Storage
metrics.gauge("trace.storage.total_records")
metrics.gauge("trace.storage.size_bytes")

# Access
metrics.counter("trace.access.view_trace")
metrics.counter("trace.access.export")

# Cleanup
metrics.counter("trace_cleanup.runs")
metrics.gauge("trace_cleanup.deleted_per_run")
```

### Alerts (for monitoring system)

1. **Trace recording failure rate > 5%**: Investigate immediately
2. **Storage growth > 10GB/week**: Review retention or sampling
3. **Cleanup job didn't run for > 36 hours**: Check scheduler
4. **Trace query p95 > 5s**: Add indexes or optimize

---

## Migration Plan

### Phase 1: Database Setup
1. Create `flow_execution_steps` table
2. Create `trace_access_audit` table
3. Add `trace_enabled`, `trace_level` to `conversation_sessions`
4. Add `retention_days` to `flow_definitions`

### Phase 2: Backend Implementation
1. Implement PIIMasker service
2. Implement ExecutionTraceService with async recording
3. Add audit logging
4. Create cleanup service and Cloud Scheduler job

### Phase 3: Integration
1. Add tracing to chat_runtime (behind feature flag)
2. Deploy with `sample_rate: 0.05` (5% of sessions)
3. Monitor for 1 week

### Phase 4: Frontend
1. Build session list page
2. Build replay viewer component
3. Add to flow builder

### Phase 5: Full Rollout
1. Increase sample rate to 100%
2. Enable for all flows
3. Remove feature flag

### Rollback Plan
- Feature flag allows instant disable
- If DB issues, can disable tracing without code deploy
- Trace data is disposable - can truncate table if needed

---

## Testing Strategy

### Unit Tests
- PIIMasker: verify all sensitive fields masked
- ExecutionDetails schemas: validate each node type
- Cleanup service: batch deletion logic

### Integration Tests
```python
# tests/integration/test_execution_trace.py

async def test_trace_recording_non_blocking():
    """Verify trace recording doesn't slow down chat flow."""
    # Execute flow with tracing enabled
    # Measure response time
    # Assert < 50ms overhead

async def test_pii_masking():
    """Verify PII is properly masked in traces."""
    state = {'user': {'email': 'test@example.com', 'name': 'John'}}
    # Execute with tracing
    # Verify stored trace has masked values

async def test_access_audit():
    """Verify all trace access is logged."""
    # Access trace
    # Query audit table
    # Verify record exists
```

### E2E Tests
- Start session → execute flow → view replay in UI
- Verify path highlighting works
- Verify state inspector shows correct data at each step

### Load Tests
- 1000 concurrent sessions with tracing enabled
- Measure p50/p95/p99 latency impact
- Verify no memory leaks in buffer
