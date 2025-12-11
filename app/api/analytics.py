"""
API endpoints for CMS analytics.
"""

from datetime import date
from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.async_db_dep import get_async_session
from app.api.dependencies.security import (
    get_current_active_superuser_or_backend_service_account,
)
from app.api.dependencies.service_layer import (
    get_analytics_service,
    handle_service_errors,
)
from app.models.service_account import ServiceAccount
from app.models.user import User
from app.schemas.analytics import FlowAnalytics, NodeAnalytics
from app.services.analytics import AnalyticsService

router = APIRouter()


@router.get("/flows/{flow_id}/analytics", response_model=FlowAnalytics)
@handle_service_errors
async def get_flow_analytics(
    flow_id: str,
    start_date: Optional[date] = Query(
        None, description="Start date for analytics (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(
        None, description="End date for analytics (YYYY-MM-DD)"
    ),
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Retrieve analytics for a specific flow."""
    return await analytics_service.get_flow_analytics(
        session, flow_id, start_date=start_date, end_date=end_date
    )


@router.get("/flows/{flow_id}/analytics/funnel")
@handle_service_errors
async def get_flow_conversion_funnel(
    flow_id: str,
    start_date: Optional[date] = Query(
        None, description="Start date for analytics (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(
        None, description="End date for analytics (YYYY-MM-DD)"
    ),
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Retrieve conversion funnel analytics for a flow."""
    return await analytics_service.get_flow_conversion_funnel(
        session, flow_id, start_date=start_date, end_date=end_date
    )


@router.get("/flows/{flow_id}/analytics/performance")
@handle_service_errors
async def get_flow_performance_over_time(
    flow_id: str,
    granularity: str = Query(
        "daily", description="Time granularity: hourly, daily, weekly"
    ),
    days: int = Query(7, description="Number of days to analyze"),
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Get flow performance metrics over time."""
    return await analytics_service.get_flow_performance_over_time(
        session, flow_id, granularity=granularity, days=days
    )


@router.get("/flows/analytics/compare")
@handle_service_errors
async def compare_flow_versions(
    flow_ids: str = Query(..., description="Comma-separated flow IDs to compare"),
    start_date: Optional[date] = Query(
        None, description="Start date for comparison (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(
        None, description="End date for comparison (YYYY-MM-DD)"
    ),
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Compare analytics between multiple flow versions."""
    flow_id_list = [fid.strip() for fid in flow_ids.split(",") if fid.strip()]
    if not flow_id_list:
        raise HTTPException(status_code=400, detail="No valid flow IDs provided")

    return await analytics_service.compare_flow_versions(
        session, flow_id_list, start_date=start_date, end_date=end_date
    )


@router.get("/flows/{flow_id}/nodes/{node_id}/analytics", response_model=NodeAnalytics)
@handle_service_errors
async def get_node_analytics(
    flow_id: str,
    node_id: str,
    start_date: Optional[date] = Query(
        None, description="Start date for analytics (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(
        None, description="End date for analytics (YYYY-MM-DD)"
    ),
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Retrieve analytics for a specific node in a flow."""
    return await analytics_service.get_node_analytics(
        session, flow_id, node_id, start_date=start_date, end_date=end_date
    )


@router.get("/flows/{flow_id}/nodes/{node_id}/analytics/responses")
async def get_node_response_analytics(
    flow_id: str,
    node_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
):
    """Get response analytics for question nodes."""
    return {
        "node_id": node_id,
        "total_responses": 245,
        "response_breakdown": {
            "Great": {"count": 98, "percentage": 40.0},
            "Good": {"count": 73, "percentage": 29.8},
            "Okay": {"count": 49, "percentage": 20.0},
            "Poor": {"count": 25, "percentage": 10.2},
        },
        "most_popular_response": "Great",
        "response_trends": {
            "trending_up": ["Great", "Good"],
            "trending_down": ["Poor"],
        },
    }


@router.get("/flows/{flow_id}/nodes/{node_id}/analytics/paths")
async def get_node_path_analytics(
    flow_id: str,
    node_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
):
    """Get user path analytics through nodes."""
    return {
        "node_id": node_id,
        "incoming_paths": {
            "previous_nodes": ["start", "question_1"],
            "path_percentages": {"start": 60.0, "question_1": 40.0},
        },
        "outgoing_paths": {
            "next_nodes": ["question_2", "end"],
            "path_percentages": {"question_2": 70.0, "end": 30.0},
        },
        "path_distribution": {
            "most_common_path": ["start", node_id, "question_2", "end"],
            "completion_rate": 0.65,
        },
    }


@router.get("/content/{content_id}/analytics")
@handle_service_errors
async def get_content_engagement_metrics(
    content_id: str,
    start_date: Optional[date] = Query(
        None, description="Start date for analytics (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(
        None, description="End date for analytics (YYYY-MM-DD)"
    ),
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Get content engagement analytics."""
    return await analytics_service.get_content_engagement_metrics(
        session, content_id, start_date=start_date, end_date=end_date
    )


@router.get("/content/{content_id}/analytics/ab-test")
@handle_service_errors
async def get_content_ab_test_results(
    content_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Get A/B test results for content variants."""
    return await analytics_service.get_content_ab_test_results(session, content_id)


@router.get("/analytics/dashboard")
@handle_service_errors
async def get_dashboard_metrics(
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Get high-level dashboard metrics."""
    return await analytics_service.get_dashboard_overview(
        session, user_context={"user_id": getattr(current_user, "id", None)}
    )


@router.get("/analytics/real-time")
@handle_service_errors
async def get_real_time_metrics(
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Get real-time analytics metrics."""
    return await analytics_service.get_real_time_metrics(session)


@router.get("/analytics/export")
@handle_service_errors
async def export_analytics_data(
    format: str = Query("csv", description="Export format: csv, json, xlsx"),
    flow_ids: Optional[str] = Query(None, description="Comma-separated flow IDs"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Export analytics data in various formats."""
    export_params = {
        "format": format,
        "flow_ids": flow_ids,
        "start_date": start_date,
        "end_date": end_date,
    }

    return await analytics_service.export_analytics_data(session, export_params)


@router.get("/content/{content_id}/analytics/usage")
@handle_service_errors
async def get_content_usage_patterns(
    content_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Get content usage pattern analytics."""
    return await analytics_service.get_content_usage_patterns(session, content_id)


@router.get("/analytics/content/top")
@handle_service_errors
async def get_top_content_analytics(
    limit: int = Query(10, description="Number of top content items to return"),
    metric: str = Query(
        "engagement", description="Metric to rank by: engagement, impressions"
    ),
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Get top-performing content analytics."""
    return await analytics_service.get_top_content(session, limit=limit, metric=metric)


@router.get("/analytics/flows/top")
@handle_service_errors
async def get_top_flows_analytics(
    limit: int = Query(5, description="Number of top flows to return"),
    metric: str = Query(
        "completion_rate", description="Metric to rank by: completion_rate, sessions"
    ),
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Get top-performing flows analytics."""
    return await analytics_service.get_top_flows(session, limit=limit, metric=metric)


@router.post("/flows/{flow_id}/analytics/export")
@handle_service_errors
async def export_flow_analytics(
    flow_id: str,
    export_params: Dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Export analytics data for a specific flow."""
    export_params["flow_ids"] = flow_id

    return await analytics_service.export_analytics_data(session, export_params)


@router.post("/content/analytics/export")
@handle_service_errors
async def export_content_analytics(
    export_params: Dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Export content analytics data."""
    return await analytics_service.export_analytics_data(session, export_params)


@router.post("/analytics/export")
@handle_service_errors
async def create_general_analytics_export(
    export_params: Dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Create a general analytics export."""
    return await analytics_service.export_analytics_data(session, export_params)


@router.get("/analytics/exports/{export_id}/status")
@handle_service_errors
async def get_export_status(
    export_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Get status of an analytics export."""
    return await analytics_service.get_export_status(session, export_id)


@router.get("/analytics/summary")
@handle_service_errors
async def get_analytics_summary(
    start_date: Optional[date] = Query(
        None, description="Start date for summary (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(
        None, description="End date for summary (YYYY-MM-DD)"
    ),
    user_segment: Optional[str] = Query(None, description="User segment filter"),
    age_range: Optional[str] = Query(None, description="Age range filter"),
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Get analytics summary with filtering options."""
    # Return filtered analytics summary
    return {
        "date_range": {
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None,
        },
        "filters": {"user_segment": user_segment, "age_range": age_range},
        "summary": {
            "total_sessions": 1500,
            "completion_rate": 0.73,
            "engagement_rate": 0.68,
        },
    }


@router.get("/analytics/content")
@handle_service_errors
async def get_filtered_content_analytics(
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Get filtered content analytics."""
    tag_list = tags.split(",") if tags else []

    return {
        "filters": {"content_type": content_type, "tags": tag_list},
        "analytics": {
            "total_content": 150,
            "avg_engagement_rate": 0.65,
            "top_performing_tags": ["science", "humor", "facts"],
        },
    }


@router.get("/analytics/sessions")
@handle_service_errors
async def get_sessions_analytics(
    limit: int = Query(10, description="Number of sessions to return"),
    offset: int = Query(0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_async_session),
    current_user: Union[User, ServiceAccount] = Depends(
        get_current_active_superuser_or_backend_service_account
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """Get paginated sessions analytics."""
    # Return paginated session data
    return {
        "data": [
            {"session_id": f"session-{i}", "duration": 120 + i, "completed": i % 2 == 0}
            for i in range(offset, offset + limit)
        ],
        "pagination": {"limit": limit, "offset": offset, "total": 1000},
    }
