# Analytics Endpoint Strategy

Design note assessing which analytics endpoints use real data versus simulated/placeholder data, and recommending which to keep, remove, or defer.

## Endpoint Classification

### Real SQL Implementations (keep and test)

These endpoints query `conversation_sessions`, `conversation_history`, `flow_definitions`, and `flow_nodes` tables with proper SQL aggregation. They return meaningful data when sessions exist.

| Endpoint | Service Method | What It Queries |
|----------|---------------|-----------------|
| `GET /flows/{flow_id}/analytics` | `get_flow_analytics` | Session counts, completion rate, avg duration, unique users |
| `GET /flows/{flow_id}/analytics/funnel` | `get_flow_conversion_funnel` | Per-node visitor counts across flow, drop-off between nodes |
| `GET /flows/{flow_id}/analytics/performance` | `get_flow_performance_over_time` | Time-series session/completion data with date_trunc granularity |
| `GET /flows/analytics/compare` | `compare_flow_versions` | Session metrics per flow, cross-flow comparison scoring |
| `GET /flows/{flow_id}/nodes/{node_id}/analytics` | `get_node_analytics` | Node views, interactions, response time via window functions |
| `GET /analytics/flows/top` | `get_top_flows` | Flows ranked by completion rate or session count |
| `GET /analytics/dashboard` | `get_dashboard_overview` | Active flow/content/session counts, top performing flows |
| `GET /analytics/real-time` | `get_real_time_metrics` | Active session count, sessions in last hour, top active flows |

**Notes on partially-simulated fields within real endpoints:**
- `get_dashboard_overview` has a hardcoded `recent_activity` block (`content_created_this_week: 5`, `flows_published_this_week: 2`) — the rest is real SQL.
- `get_real_time_metrics` has a simulated `real_time_events` list, `response_time: 145`, and `error_rate: 0.002` — active session and flow queries are real.

### Fully Simulated (hardcoded data, no SQL)

These endpoints return fabricated numbers. They exist in the API layer (`analytics.py`) and bypass the service entirely or the service generates fake data using MD5 hashes of IDs.

| Endpoint | What It Returns |
|----------|----------------|
| `GET /flows/{flow_id}/nodes/{node_id}/analytics/responses` | Hardcoded response breakdown ("Great": 98, "Good": 73, etc.) — no service call |
| `GET /flows/{flow_id}/nodes/{node_id}/analytics/paths` | Hardcoded path distribution with fake node names — no service call |
| `GET /analytics/summary` | Hardcoded `total_sessions: 1500`, `completion_rate: 0.73` — no service call |
| `GET /analytics/sessions` | Generates sequential fake `session-{i}` entries — no service call |
| `GET /analytics/content` | Hardcoded `total_content: 150`, fake tag rankings — no service call |

### Simulated Service Methods (MD5-hash-derived fake data)

These call `AnalyticsService` methods, but those methods generate numbers from MD5 hashes of the input ID rather than querying usage data. The system has no content impression/interaction tracking tables.

| Endpoint | Service Method | Problem |
|----------|---------------|---------|
| `GET /content/{content_id}/analytics` | `get_content_engagement_metrics` | Hash-based impressions, fake sentiment analysis |
| `GET /content/{content_id}/analytics/ab-test` | `get_content_ab_test_results` | Queries real variants but generates fake conversion/engagement rates |
| `GET /content/{content_id}/analytics/usage` | `get_content_usage_patterns` | Hash-based frequency, hardcoded time/context/segment distributions |
| `GET /analytics/content/top` | `get_top_content` | Queries real content list but ranks by hash-based fake scores |

### Export Endpoints (no backend implementation)

These generate fake export IDs and status without actually creating files or background jobs.

| Endpoint | Problem |
|----------|---------|
| `GET /analytics/export` | Returns fake export_id, estimated file size, non-functional download URL |
| `POST /flows/{flow_id}/analytics/export` | Same — delegates to same fake method |
| `POST /content/analytics/export` | Same |
| `POST /analytics/export` | Same |
| `GET /analytics/exports/{export_id}/status` | MD5-hash-derived progress percentage |

## Product Analysis

**What is actually useful for Huey Books?**

The product is a chatflow-based book recommendation engine for schools. The valuable analytics are:

1. **Flow completion rate** — Are students finishing the recommendation flow? (implemented, real SQL)
2. **Drop-off analysis** — Where do students abandon the flow? (implemented via funnel endpoint)
3. **Session volume** — How many students are using the system? (implemented)
4. **Per-school metrics** — Flow usage by school. (not implemented — sessions have `school_id` but no endpoint filters by school)

**What is not useful right now:**
- Content A/B testing — No A/B test infrastructure exists. Variants are used for content localization, not experimentation.
- Content engagement/impressions — No tracking tables for content views exist. This would require new instrumentation.
- Data exports — No background job infrastructure for export file generation exists.
- Real-time event streams — PostgreSQL NOTIFY/LISTEN exists for dashboard updates, but the REST endpoint simulates events rather than surfacing them.

## Recommendations

### Keep (real implementations, worth testing)

- `GET /flows/{flow_id}/analytics` — core flow metrics
- `GET /flows/{flow_id}/analytics/funnel` — conversion funnel
- `GET /flows/{flow_id}/analytics/performance` — time-series performance
- `GET /flows/analytics/compare` — flow version comparison
- `GET /flows/{flow_id}/nodes/{node_id}/analytics` — node-level metrics
- `GET /analytics/flows/top` — top flows ranking
- `GET /analytics/dashboard` — dashboard overview (clean up hardcoded `recent_activity`)
- `GET /analytics/real-time` — real-time session counts (clean up simulated fields)

### Remove (no real implementation, misleading)

- `GET /flows/{flow_id}/nodes/{node_id}/analytics/responses` — hardcoded fake data
- `GET /flows/{flow_id}/nodes/{node_id}/analytics/paths` — hardcoded fake data
- `GET /analytics/summary` — hardcoded fake data, overlaps with `/analytics/dashboard`
- `GET /analytics/sessions` — sequential fake data
- `GET /analytics/content` — hardcoded fake data
- All 5 export endpoints — no backend implementation
- `GET /analytics/exports/{export_id}/status` — fake progress tracking

### Defer (needs new infrastructure to implement properly)

- `GET /content/{content_id}/analytics` — needs content impression tracking tables
- `GET /content/{content_id}/analytics/ab-test` — needs A/B test framework
- `GET /content/{content_id}/analytics/usage` — needs content usage tracking
- `GET /analytics/content/top` — needs real engagement scoring

## Summary

Of 21 analytics endpoints, **8 have real SQL implementations** worth keeping and testing. **5 return inline hardcoded data** and should be removed. **4 use hash-derived fake data** in the service layer and should be deferred until tracking infrastructure exists. **5 export endpoints** have no backend and should be removed (or one kept as a stub if export is on the roadmap).

Removing the 10 fake endpoints would reduce the analytics API surface by ~48% while eliminating every endpoint that returns misleading data.
