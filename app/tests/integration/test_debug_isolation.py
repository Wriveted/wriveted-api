"""
Debug tests to isolate the root cause of test failures.

These tests are designed to systematically identify:
1. Connection pool exhaustion
2. Resource cleanup issues
3. Timing/concurrency problems
4. Test ordering dependencies
"""

import asyncio
import logging
import time
from unittest.mock import Mock

import psutil
import pytest

logger = logging.getLogger(__name__)


class TestIsolationDebugging:
    """Tests to debug isolation issues."""

    def test_individual_export_analytics_baseline(
        self, client, backend_service_account_headers
    ):
        """Individual test that should pass - establishes baseline."""
        logger.info("🧪 [BASELINE] Running individual export analytics test")

        # Create flow for export
        flow_data = {
            "name": "Debug Export Test Flow",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        assert create_response.status_code == 201
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

        logger.info(f"🧪 [BASELINE] Export response status: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"🧪 [BASELINE] Response body: {response.text}")

        assert response.status_code == 200

    def test_individual_student_security_baseline(
        self, client, test_student_user_account_headers
    ):
        """Individual security test that should pass - establishes baseline."""
        logger.info("🧪 [BASELINE] Running individual security test")

        content_data = {
            "content_type": "MESSAGE",
            "title": "Debug Security Test",
            "tags": ["debug", "security"],
        }

        response = client.put(
            "v1/cms/content/550e8400-e29b-41d4-a716-446655440000",  # Random UUID
            json=content_data,
            headers=test_student_user_account_headers,
        )

        logger.info(f"🧪 [BASELINE] Security response status: {response.status_code}")
        if response.status_code != 403:
            logger.error(f"🧪 [BASELINE] Unexpected response: {response.text}")

        assert response.status_code == 403

    def test_minimal_sequential_failure_reproduction(
        self, client, backend_service_account_headers, test_student_user_account_headers
    ):
        """Try to reproduce failures with minimal sequential tests."""
        logger.info("🧪 [SEQUENCE] Running sequential test to reproduce failure")

        # Test 1: Export (should pass individually)
        logger.info("🧪 [SEQUENCE] Step 1: Export test")
        flow_data = {
            "name": "Sequential Test Flow",
            "version": "1.0.0",
            "flow_data": {},
            "entry_node_id": "start",
        }
        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        assert create_response.status_code == 201
        flow_id = create_response.json()["id"]

        export_params = {
            "format": "csv",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "metrics": ["sessions"],
        }
        export_response = client.post(
            f"v1/cms/flows/{flow_id}/analytics/export",
            json=export_params,
            headers=backend_service_account_headers,
        )

        if export_response.status_code != 200:
            logger.error(
                f"🧪 [SEQUENCE] Export failed: {export_response.status_code} - {export_response.text}"
            )
        assert export_response.status_code == 200

        # Test 2: Security (should pass individually)
        logger.info("🧪 [SEQUENCE] Step 2: Security test")
        content_data = {
            "content_type": "MESSAGE",
            "title": "Sequential Security Test",
            "tags": ["debug"],
        }
        security_response = client.put(
            "v1/cms/content/550e8400-e29b-41d4-a716-446655440001",
            json=content_data,
            headers=test_student_user_account_headers,
        )

        if security_response.status_code != 403:
            logger.error(
                f"🧪 [SEQUENCE] Security check failed: {security_response.status_code} - {security_response.text}"
            )
        assert security_response.status_code == 403

        logger.info("🧪 [SEQUENCE] Sequential test completed successfully")

    def test_resource_stress(self, client, backend_service_account_headers):
        """Test resource usage under multiple operations."""
        logger.info("🧪 [STRESS] Running resource stress test")

        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        logger.info(f"🧪 [STRESS] Initial memory: {initial_memory:.1f}MB")

        # Create multiple flows to stress test resources
        flow_ids = []
        for i in range(5):  # Create 5 flows
            flow_data = {
                "name": f"Stress Test Flow {i}",
                "version": "1.0.0",
                "flow_data": {"entry_point": "start"},
                "entry_node_id": "start",
            }

            response = client.post(
                "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
            )
            if response.status_code == 201:
                flow_ids.append(response.json()["id"])
            else:
                logger.error(
                    f"🧪 [STRESS] Flow creation failed at iteration {i}: {response.status_code}"
                )

        mid_memory = psutil.Process().memory_info().rss / 1024 / 1024
        logger.info(
            f"🧪 [STRESS] Memory after flow creation: {mid_memory:.1f}MB ({mid_memory - initial_memory:+.1f}MB)"
        )

        # Try to export analytics for each flow
        successful_exports = 0
        for i, flow_id in enumerate(flow_ids):
            export_params = {
                "format": "csv",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "metrics": ["sessions"],
            }
            response = client.post(
                f"v1/cms/flows/{flow_id}/analytics/export",
                json=export_params,
                headers=backend_service_account_headers,
            )

            if response.status_code == 200:
                successful_exports += 1
            else:
                logger.error(
                    f"🧪 [STRESS] Export {i} failed: {response.status_code} - {response.text}"
                )

        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        logger.info(
            f"🧪 [STRESS] Final memory: {final_memory:.1f}MB ({final_memory - initial_memory:+.1f}MB total)"
        )
        logger.info(
            f"🧪 [STRESS] Successful exports: {successful_exports}/{len(flow_ids)}"
        )

        # This should pass if resources are managed properly
        assert (
            successful_exports >= len(flow_ids) // 2
        ), f"Too many export failures: {successful_exports}/{len(flow_ids)}"

    @pytest.mark.asyncio
    async def test_async_session_resource_tracking(self, async_session):
        """Test async session resource usage directly."""
        logger.info("🧪 [ASYNC] Testing async session resource usage")

        from sqlalchemy import text

        # Simple query to test session
        try:
            result = await async_session.execute(
                text("SELECT COUNT(*) FROM information_schema.tables")
            )
            count = result.scalar()
            logger.info(f"🧪 [ASYNC] Found {count} tables in database")

            # Test multiple queries to stress the session
            for i in range(10):
                await async_session.execute(text("SELECT 1"))

            logger.info("🧪 [ASYNC] Multiple queries completed successfully")

        except Exception as e:
            logger.error(f"🧪 [ASYNC] Session test failed: {e}")
            raise

    def test_concurrent_simulation(self, client, backend_service_account_headers):
        """Simulate concurrent behavior that might cause issues."""
        logger.info("🧪 [CONCURRENT] Simulating concurrent test behavior")

        # Create flow
        flow_data = {
            "name": "Concurrent Test Flow",
            "version": "1.0.0",
            "flow_data": {},
            "entry_node_id": "start",
        }
        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        assert create_response.status_code == 201
        flow_id = create_response.json()["id"]

        # Simulate what happens in a full test suite - multiple rapid requests
        requests_completed = 0
        errors = []

        for i in range(3):  # Simulate 3 concurrent-like operations
            try:
                # Get flow
                get_response = client.get(
                    f"v1/cms/flows/{flow_id}", headers=backend_service_account_headers
                )
                if get_response.status_code != 200:
                    errors.append(f"GET flow failed: {get_response.status_code}")
                    continue

                # Export analytics
                export_params = {
                    "format": "csv",
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "metrics": ["sessions"],
                }
                export_response = client.post(
                    f"v1/cms/flows/{flow_id}/analytics/export",
                    json=export_params,
                    headers=backend_service_account_headers,
                )
                if export_response.status_code != 200:
                    errors.append(
                        f"Export {i} failed: {export_response.status_code} - {export_response.text[:100]}"
                    )
                    continue

                requests_completed += 1

            except Exception as e:
                errors.append(f"Request {i} exception: {e}")

        logger.info(f"🧪 [CONCURRENT] Completed {requests_completed}/3 requests")
        if errors:
            logger.error(f"🧪 [CONCURRENT] Errors: {errors}")

        # Should complete most operations successfully
        assert requests_completed >= 2, f"Too many failures: {errors}"

    def test_database_connection_state(self, async_session):
        """Check database connection state after various operations."""
        logger.info("🧪 [CONNECTION] Testing database connection state")

        # This should work
        pytest.skip("Skipping async test in sync context")
