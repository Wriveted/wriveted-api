# Session Replay / Execution Tracing

## Overview

The execution tracing system captures detailed node-by-node execution data for conversation sessions. This enables debugging ("why did user X get this response?"), QA testing, analytics, and support investigations.

## Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| `FlowExecutionStep` model | Implemented | `app/models/cms.py` |
| `TraceAccessAudit` model | Implemented | `app/models/cms.py` |
| `ExecutionTraceService` | Implemented | `app/services/execution_trace.py` (535 lines) |
| `TraceAuditService` | Implemented | `app/services/execution_trace.py` |
| `PIIMasker` | Implemented | `app/services/pii_masker.py` (204 lines) |
| `TraceCleanupService` | Implemented | `app/services/trace_cleanup.py` (176 lines) |
| Execution trace schemas | Implemented | `app/schemas/execution_trace.py` |
| API endpoints | Implemented | `app/api/cms.py` (5 endpoints) |
| Chat runtime integration | Implemented | `chat_runtime.py` records traces when enabled |
| ACL access control on traces | Not implemented | `FlowExecutionStep` has no `__acl__` method |
| Async trace queueing | Partial | Buffered in-process, not yet via Cloud Tasks |

## Data Model

### `flow_execution_steps` table

Each row captures one node visit during a session:

- `session_id` (FK to `conversation_sessions`)
- `node_id`, `node_type` -- which node was visited
- `step_number` -- execution sequence within the session
- `state_before`, `state_after` (JSONB) -- PII-masked state snapshots
- `execution_details` (JSONB) -- node-type-specific details (see typed schemas below)
- `connection_type`, `next_node_id` -- which connection was taken to the next node
- `started_at`, `completed_at`, `duration_ms` -- timing
- `error_message`, `error_details` -- error tracking

Indexes: session+step_number composite, session+started_at partial (completed only), session+node_id partial (errors only).

### `trace_access_audit` table

Tracks who accesses trace data: `session_id`, `accessed_by` (user FK), `access_type`, `ip_address`, `user_agent`, `data_accessed` (JSONB).

### Session fields

`conversation_sessions` has `trace_enabled` (boolean) and `trace_level` (varchar: `minimal`, `standard`, `verbose`). These are set at session start based on the flow's tracing configuration.

## Trace Levels

| Level | State Snapshots | Execution Details | Use Case |
|-------|-----------------|-------------------|----------|
| `minimal` | No | No | Production monitoring, path analytics |
| `standard` | Yes (PII-masked) | Summary only | Debugging, support |
| `verbose` | Yes (PII-masked) | Full details | Development, deep debugging |

Default is `standard` for new sessions. `verbose` can be enabled per-flow.

## Typed Execution Details

Each node type has a Pydantic schema for its `execution_details` field (defined in `app/schemas/execution_trace.py`):

- **ConditionExecutionDetails**: `conditions_evaluated` (list of expression/result pairs), `matched_condition_index`, `connection_taken`
- **ScriptExecutionDetails**: `language`, `code_preview`, `inputs`, `outputs`, `console_logs`, `execution_time_ms`
- **QuestionExecutionDetails**: `question_text`, `rendered_question`, `options`, `user_response`, `response_time_ms`
- **MessageExecutionDetails**: `message_template`, `rendered_message`, `media_urls`
- **ActionExecutionDetails**: `action_type`, `actions_executed`, `variables_changed` (with old/new values)
- **WebhookExecutionDetails**: `url` (credentials masked), `method`, `request_headers` (auth redacted), `response_status`, `response_body` (truncated if >1KB)

## PII Masking

`PIIMasker` (`app/services/pii_masker.py`) recursively masks sensitive data before storing state snapshots:

- **Key-based masking**: Fields matching sensitive key names (email, phone, password, token, etc.) are masked
- **Pattern-based masking**: Email and phone patterns detected and replaced with `[EMAIL]` / `[PHONE]`
- **Webhook redaction**: Auth headers replaced with `[REDACTED]`, URL credentials masked, large response bodies truncated

## API Endpoints

All mounted under `/v1/cms/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/flows/{flow_id}/sessions` | GET | List sessions for a flow (filterable by status, user, date range, errors) |
| `/sessions/{session_id}/trace` | GET | Full session trace with audit logging |
| `/flows/{flow_id}/tracing` | POST | Enable/disable tracing and set level for a flow |
| `/flows/{flow_id}/tracing` | GET | Get current tracing configuration |
| `/flows/{flow_id}/trace-stats` | GET | Trace statistics for a flow |
| `/trace-storage` | GET | Storage statistics (total traces, table size, date range) |

## Trace Recording

`ExecutionTraceService.record_step_async()` buffers trace data in-process and flushes in batches. The service is designed to never block the chat flow -- trace recording failures are logged but do not propagate to the user.

The chat runtime calls `record_step` after each node execution when `session.trace_enabled` is true. State snapshots are PII-masked before storage.

## Data Retention

`TraceCleanupService` deletes old traces in batches (default retention: 30 days, configurable per-flow via `retention_days`). Designed to be run as a scheduled job (e.g., Cloud Scheduler hitting `/internal/tasks/cleanup-traces` daily).

## Remaining Work

- **ACL access control**: `FlowExecutionStep` does not implement `__acl__` -- trace access is currently controlled at the API endpoint level, not per-record
- **Async queueing**: Trace recording is buffered in-process but not yet offloaded to Cloud Tasks for true async processing
- **Frontend replay viewer**: Implemented in the admin UI (separate repo)
