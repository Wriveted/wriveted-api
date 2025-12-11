"""
Comprehensive CMS Analytics and Metrics Tests.

This module consolidates all analytics-related tests from multiple CMS test files:
- Flow performance analytics and metrics
- Content engagement and conversion tracking
- A/B testing analytics and variant performance
- User journey and interaction analytics
- Content recommendation analytics
- System performance and usage metrics
- Analytics data export functionality
- Real-time analytics and dashboard data

Consolidated from:
- test_cms.py (variant performance metrics)
- test_cms_api_enhanced.py (pagination and filtering analytics)
- Various other test files (analytics-related functionality)

Note: This area had the least existing test coverage, so many tests are newly created
to fill gaps in analytics testing.
"""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text
from starlette import status


@pytest.fixture(autouse=True)
async def cleanup_cms_data(async_session):
    """Clean up CMS data before and after each test to ensure test isolation."""
    cms_tables = [
        "cms_content",
        "cms_content_variants",
        "flow_definitions",
        "flow_nodes",
        "flow_connections",
        "conversation_sessions",
        "conversation_history",
        "conversation_analytics",
    ]

    await async_session.rollback()

    # Clean up before test runs
    for table in cms_tables:
        try:
            await async_session.execute(
                text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            )
        except Exception:
            # Table might not exist, skip it
            pass
    await async_session.commit()

    yield

    await async_session.rollback()

    # Clean up after test runs
    for table in cms_tables:
        try:
            await async_session.execute(
                text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            )
        except Exception:
            # Table might not exist, skip it
            pass
    await async_session.commit()


class TestFlowAnalytics:
    """Test flow performance analytics and metrics."""

    def test_get_flow_analytics_basic(self, client, backend_service_account_headers):
        """Test basic flow analytics retrieval."""
        # First create a flow to analyze
        flow_data = {
            "name": "Analytics Test Flow",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
            "is_published": True,
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Get analytics for the flow
        response = client.get(
            f"v1/cms/flows/{flow_id}/analytics",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "flow_id" in data
        assert "total_sessions" in data
        assert "completion_rate" in data
        assert "average_duration" in data
        assert "bounce_rate" in data
        assert "engagement_metrics" in data
        assert "time_period" in data

    def test_get_flow_analytics_with_date_range(
        self, client, backend_service_account_headers
    ):
        """Test flow analytics with specific date range."""
        # Create flow first
        flow_data = {
            "name": "Date Range Analytics Flow",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Get analytics for last 30 days
        start_date = (datetime.now() - timedelta(days=30)).date().isoformat()
        end_date = datetime.now().date().isoformat()

        response = client.get(
            f"v1/cms/flows/{flow_id}/analytics?start_date={start_date}&end_date={end_date}",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert (
            data["time_period"]["start_date"] == start_date
        )  # Now both are date strings
        assert data["time_period"]["end_date"] == end_date

    def test_get_flow_conversion_funnel(self, client, backend_service_account_headers):
        """Test flow conversion funnel analytics."""
        # Create flow with multiple nodes
        flow_data = {
            "name": "Funnel Test Flow",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Add nodes to create a funnel
        nodes = [
            {"node_id": "welcome", "node_type": "message", "content": {"messages": []}},
            {
                "node_id": "question1",
                "node_type": "question",
                "content": {"question": {}},
            },
            {
                "node_id": "question2",
                "node_type": "question",
                "content": {"question": {}},
            },
            {"node_id": "result", "node_type": "message", "content": {"messages": []}},
        ]

        for node in nodes:
            client.post(
                f"v1/cms/flows/{flow_id}/nodes",
                json=node,
                headers=backend_service_account_headers,
            )

        # Get conversion funnel
        response = client.get(
            f"v1/cms/flows/{flow_id}/analytics/funnel",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "flow_id" in data
        assert "funnel_steps" in data
        assert "conversion_rates" in data
        assert "drop_off_points" in data
        assert len(data["funnel_steps"]) == len(nodes)

    def test_get_flow_performance_over_time(
        self, client, backend_service_account_headers
    ):
        """Test flow performance metrics over time."""
        # Create flow
        flow_data = {
            "name": "Performance Tracking Flow",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Get performance over time (daily granularity)
        response = client.get(
            f"v1/cms/flows/{flow_id}/analytics/performance?granularity=daily&days=7",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "flow_id" in data
        assert "time_series" in data
        assert "granularity" in data
        assert data["granularity"] == "daily"
        assert isinstance(data["time_series"], list)

    def test_compare_flow_versions_analytics(
        self, client, backend_service_account_headers
    ):
        """Test comparing analytics between flow versions."""
        # Create multiple versions of a flow
        flow_v1_data = {
            "name": "Version Comparison Flow",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        flow_v2_data = {
            "name": "Version Comparison Flow",
            "version": "2.0.0",
            "flow_data": {"entry_point": "start_v2"},
            "entry_node_id": "start_v2",
        }

        flow_v1_response = client.post(
            "v1/cms/flows", json=flow_v1_data, headers=backend_service_account_headers
        )
        flow_v1_id = flow_v1_response.json()["id"]

        flow_v2_response = client.post(
            "v1/cms/flows", json=flow_v2_data, headers=backend_service_account_headers
        )
        flow_v2_id = flow_v2_response.json()["id"]

        # Compare analytics between versions
        response = client.get(
            f"v1/cms/flows/analytics/compare?flow_ids={flow_v1_id},{flow_v2_id}",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "comparison" in data
        assert len(data["comparison"]) == 2
        assert "performance_delta" in data
        assert "winner" in data


class TestNodeAnalytics:
    """Test individual node performance analytics."""

    def test_get_node_engagement_metrics(self, client, backend_service_account_headers):
        """Test node-level engagement metrics."""
        # Create flow and node
        flow_data = {
            "name": "Node Analytics Flow",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        node_data = {
            "node_id": "analytics_node",
            "node_type": "question",
            "content": {
                "question": {"text": "How do you like our service?"},
                "options": ["Great", "Good", "Okay", "Poor"],
            },
        }

        node_response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )
        node_db_id = node_response.json()["id"]

        # Get node analytics
        response = client.get(
            f"v1/cms/flows/{flow_id}/nodes/{node_db_id}/analytics",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "node_id" in data
        assert "visits" in data
        assert "interactions" in data
        assert "bounce_rate" in data
        assert "average_time_spent" in data
        assert "response_distribution" in data

    def test_get_node_response_analytics(self, client, backend_service_account_headers):
        """Test analytics for user responses to question nodes."""
        # Create flow and question node
        flow_data = {
            "name": "Response Analytics Flow",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        node_data = {
            "node_id": "response_node",
            "node_type": "question",
            "content": {
                "question": {"text": "What's your favorite genre?"},
                "input_type": "buttons",
                "options": [
                    {"text": "Fantasy", "value": "fantasy"},
                    {"text": "Mystery", "value": "mystery"},
                    {"text": "Romance", "value": "romance"},
                    {"text": "Sci-Fi", "value": "scifi"},
                ],
            },
        }

        node_response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )
        node_db_id = node_response.json()["id"]

        # Get response analytics
        response = client.get(
            f"v1/cms/flows/{flow_id}/nodes/{node_db_id}/analytics/responses",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "node_id" in data
        assert "total_responses" in data
        assert "response_breakdown" in data
        assert "most_popular_response" in data
        assert "response_trends" in data

    def test_get_node_path_analytics(self, client, backend_service_account_headers):
        """Test user path analytics through nodes."""
        # Create flow with connected nodes
        flow_data = {
            "name": "Path Analytics Flow",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Create multiple connected nodes
        nodes = [
            {"node_id": "start", "node_type": "message", "content": {"messages": []}},
            {"node_id": "branch", "node_type": "question", "content": {"question": {}}},
            {"node_id": "path_a", "node_type": "message", "content": {"messages": []}},
            {"node_id": "path_b", "node_type": "message", "content": {"messages": []}},
        ]

        node_ids = []
        for node in nodes:
            response = client.post(
                f"v1/cms/flows/{flow_id}/nodes",
                json=node,
                headers=backend_service_account_headers,
            )
            node_ids.append(response.json()["id"])

        # Get path analytics for the branch node
        response = client.get(
            f"v1/cms/flows/{flow_id}/nodes/{node_ids[1]}/analytics/paths",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "node_id" in data
        assert "incoming_paths" in data
        assert "outgoing_paths" in data
        assert "path_distribution" in data


class TestContentAnalytics:
    """Test analytics for content performance and engagement."""

    def test_get_content_engagement_metrics(
        self, client, backend_service_account_headers
    ):
        """Test content engagement analytics."""
        # Create content first
        content_data = {
            "type": "joke",
            "content": {
                "text": "Why don't scientists trust atoms? Because they make up everything!",
                "category": "science",
            },
            "tags": ["science", "humor"],
            "status": "published",
        }

        create_response = client.post(
            "v1/cms/content", json=content_data, headers=backend_service_account_headers
        )
        content_id = create_response.json()["id"]

        # Get content analytics
        response = client.get(
            f"v1/cms/content/{content_id}/analytics",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "content_id" in data
        assert "impressions" in data
        assert "interactions" in data
        assert "engagement_rate" in data
        assert "sentiment_analysis" in data
        assert "usage_contexts" in data

    def test_get_content_ab_test_results(self, client, backend_service_account_headers):
        """Test A/B testing analytics for content variants."""
        # Create content with variants
        content_data = {
            "type": "message",
            "content": {"text": "Welcome to our platform!"},
            "tags": ["welcome"],
        }

        create_response = client.post(
            "v1/cms/content", json=content_data, headers=backend_service_account_headers
        )
        content_id = create_response.json()["id"]

        # Create variants
        variants = [
            {
                "variant_key": "formal",
                "variant_data": {"text": "Welcome to our professional platform."},
                "weight": 50,
            },
            {
                "variant_key": "casual",
                "variant_data": {"text": "Hey there! Welcome to our awesome platform!"},
                "weight": 50,
            },
        ]

        for variant in variants:
            client.post(
                f"v1/cms/content/{content_id}/variants",
                json=variant,
                headers=backend_service_account_headers,
            )

        # Get A/B test results
        response = client.get(
            f"v1/cms/content/{content_id}/analytics/ab-test",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "content_id" in data
        assert "test_results" in data
        assert "statistical_significance" in data
        assert "winning_variant" in data
        assert "confidence_level" in data

    def test_get_content_usage_patterns(self, client, backend_service_account_headers):
        """Test content usage pattern analytics."""
        # Create content
        content_data = {
            "type": "fact",
            "content": {
                "text": "The human brain contains approximately 86 billion neurons.",
                "category": "science",
            },
            "tags": ["brain", "science", "facts"],
        }

        create_response = client.post(
            "v1/cms/content", json=content_data, headers=backend_service_account_headers
        )
        content_id = create_response.json()["id"]

        # Get usage patterns
        response = client.get(
            f"v1/cms/content/{content_id}/analytics/usage",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "content_id" in data
        assert "usage_frequency" in data
        assert "time_patterns" in data
        assert "context_distribution" in data
        assert "user_segments" in data


class TestAnalyticsDashboard:
    """Test analytics dashboard data and aggregations."""

    def test_get_dashboard_overview(self, client, backend_service_account_headers):
        """Test dashboard overview analytics."""
        response = client.get(
            "v1/cms/analytics/dashboard",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "overview" in data
        assert "total_flows" in data["overview"]
        assert "total_content" in data["overview"]
        assert "active_sessions" in data["overview"]
        assert "engagement_rate" in data["overview"]
        assert "top_performing" in data
        assert "recent_activity" in data

    def test_get_real_time_metrics(self, client, backend_service_account_headers):
        """Test real-time analytics metrics."""
        response = client.get(
            "v1/cms/analytics/real-time",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "timestamp" in data
        assert "active_sessions" in data
        assert "current_interactions" in data
        assert "response_time" in data
        assert "error_rate" in data

    def test_get_top_content_analytics(self, client, backend_service_account_headers):
        """Test top-performing content analytics."""
        response = client.get(
            "v1/cms/analytics/content/top?limit=10&metric=engagement",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "top_content" in data
        assert "metric" in data
        assert data["metric"] == "engagement"
        assert "time_period" in data
        assert len(data["top_content"]) <= 10

    def test_get_top_flows_analytics(self, client, backend_service_account_headers):
        """Test top-performing flows analytics."""
        response = client.get(
            "v1/cms/analytics/flows/top?limit=5&metric=completion_rate",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "top_flows" in data
        assert "metric" in data
        assert data["metric"] == "completion_rate"
        assert len(data["top_flows"]) <= 5


class TestAnalyticsExport:
    """Test analytics data export functionality."""

    def test_export_flow_analytics(self, client, backend_service_account_headers):
        """Test exporting flow analytics data."""
        # Create flow for export
        flow_data = {
            "name": "Export Test Flow",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Export analytics
        export_params = {
            "format": "csv",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "metrics": ["sessions", "completion_rate", "bounce_rate"],
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/analytics/export",
            json=export_params,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "export_id" in data
        assert "download_url" in data
        assert "expires_at" in data
        assert "format" in data
        assert data["format"] == "csv"

    def test_export_content_analytics(self, client, backend_service_account_headers):
        """Test exporting content analytics data."""
        export_params = {
            "format": "json",
            "content_type": "joke",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
        }

        response = client.post(
            "v1/cms/content/analytics/export",
            json=export_params,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "export_id" in data
        assert "download_url" in data
        assert "format" in data
        assert data["format"] == "json"

    def test_get_export_status(self, client, backend_service_account_headers):
        """Test checking export status."""
        # Create an export first
        export_params = {
            "format": "csv",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
        }

        export_response = client.post(
            "v1/cms/analytics/export",
            json=export_params,
            headers=backend_service_account_headers,
        )
        export_id = export_response.json()["export_id"]

        # Check export status
        response = client.get(
            f"v1/cms/analytics/exports/{export_id}/status",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "export_id" in data
        assert "status" in data
        assert "progress" in data
        assert data["status"] in ["pending", "processing", "completed", "failed"]


class TestAnalyticsFiltering:
    """Test analytics filtering and segmentation."""

    def test_filter_analytics_by_date_range(
        self, client, backend_service_account_headers
    ):
        """Test filtering analytics by custom date range."""
        start_date = "2024-01-01"
        end_date = "2024-01-31"

        response = client.get(
            f"v1/cms/analytics/summary?start_date={start_date}&end_date={end_date}",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "date_range" in data
        assert data["date_range"]["start"] == start_date
        assert data["date_range"]["end"] == end_date

    def test_filter_analytics_by_user_segment(
        self, client, backend_service_account_headers
    ):
        """Test filtering analytics by user segment."""
        response = client.get(
            "v1/cms/analytics/summary?user_segment=children&age_range=7-12",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "filters" in data
        assert data["filters"]["user_segment"] == "children"
        assert data["filters"]["age_range"] == "7-12"

    def test_filter_analytics_by_content_type(
        self, client, backend_service_account_headers
    ):
        """Test filtering analytics by content type."""
        response = client.get(
            "v1/cms/analytics/content?content_type=joke&tags=science",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "filters" in data
        assert data["filters"]["content_type"] == "joke"
        assert "science" in data["filters"]["tags"]

    def test_analytics_pagination(self, client, backend_service_account_headers):
        """Test analytics data pagination."""
        response = client.get(
            "v1/cms/analytics/sessions?limit=10&offset=20",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["offset"] == 20


class TestAnalyticsAuthentication:
    """Test analytics endpoints require proper authentication."""

    def test_dashboard_requires_authentication(self, client):
        """Test dashboard analytics require authentication."""
        response = client.get("v1/cms/analytics/dashboard")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_flow_analytics_require_authentication(self, client):
        """Test flow analytics require authentication."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"v1/cms/flows/{fake_id}/analytics")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_content_analytics_require_authentication(self, client):
        """Test content analytics require authentication."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"v1/cms/content/{fake_id}/analytics")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_export_requires_authentication(self, client):
        """Test analytics export requires authentication."""
        export_params = {"format": "csv"}
        response = client.post("v1/cms/analytics/export", json=export_params)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_real_time_analytics_require_authentication(self, client):
        """Test real-time analytics require authentication."""
        response = client.get("v1/cms/analytics/real-time")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
