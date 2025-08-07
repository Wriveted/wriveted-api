"""Tests for circuit breaker functionality."""

import asyncio
from datetime import datetime, timedelta

import pytest

from app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerState,
    get_circuit_breaker,
    get_registry,
)


class TestCircuitBreaker:
    """Test suite for CircuitBreaker functionality."""

    @pytest.fixture
    def circuit_breaker_config(self):
        """Basic circuit breaker configuration."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=1.0,
            fallback_enabled=True,
            fallback_response={"fallback": True, "message": "Service unavailable"},
        )

    @pytest.fixture
    def circuit_breaker(self, circuit_breaker_config):
        """Create a circuit breaker instance."""
        return CircuitBreaker("test_service", circuit_breaker_config)

    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state_success(self, circuit_breaker):
        """Test successful calls in CLOSED state."""

        async def success_func():
            return {"success": True}

        result = await circuit_breaker.call(success_func)

        assert result == {"success": True}
        assert circuit_breaker.stats.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.stats.success_count == 1
        assert circuit_breaker.stats.total_successes == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_tracking(self, circuit_breaker):
        """Test failure tracking and state transitions."""

        async def failing_func():
            raise Exception("Service error")

        # Generate failures up to threshold
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

            if i < 2:  # Before threshold
                assert circuit_breaker.stats.state == CircuitBreakerState.CLOSED
            else:  # At threshold
                assert circuit_breaker.stats.state == CircuitBreakerState.OPEN

        assert circuit_breaker.stats.failure_count == 3
        assert circuit_breaker.stats.total_failures == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_state_rejection(self):
        """Test that OPEN state rejects calls when fallback is disabled."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            fallback_enabled=False,  # Disable fallback to test error raising
        )
        cb = CircuitBreaker("test_rejection", config)

        async def failing_func():
            raise Exception("Service error")

        # Force circuit to OPEN state
        for _ in range(3):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb.stats.state == CircuitBreakerState.OPEN

        # Now calls should be rejected
        with pytest.raises(CircuitBreakerError) as exc_info:
            await cb.call(failing_func)

        assert "is open" in str(exc_info.value)
        error = exc_info.value
        assert isinstance(error, CircuitBreakerError)
        assert error.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_fallback_response(self, circuit_breaker):
        """Test fallback response when circuit is open."""

        async def failing_func():
            raise Exception("Service error")

        # Force circuit to OPEN state
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

        # Should return fallback response instead of raising
        result = await circuit_breaker.call(failing_func)

        assert result == {"fallback": True, "message": "Service unavailable"}

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_transition(self, circuit_breaker):
        """Test transition from OPEN to HALF_OPEN after timeout."""

        async def failing_func():
            raise Exception("Service error")

        # Force to OPEN state
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.stats.state == CircuitBreakerState.OPEN

        # Wait for timeout (simulate by adjusting last_failure_time)
        circuit_breaker.stats.last_failure_time = datetime.utcnow() - timedelta(
            seconds=2
        )

        # Next call should transition to HALF_OPEN
        with pytest.raises(Exception):  # Still fails but state changes
            await circuit_breaker.call(failing_func)

        # Should be back to OPEN after failure in HALF_OPEN
        assert circuit_breaker.stats.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_to_closed(self, circuit_breaker):
        """Test recovery from HALF_OPEN to CLOSED state."""

        async def sometimes_failing_func(should_fail=True):
            if should_fail:
                raise Exception("Service error")
            return {"success": True}

        # Force to OPEN state
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(sometimes_failing_func, True)

        # Simulate timeout passage
        circuit_breaker.stats.last_failure_time = datetime.utcnow() - timedelta(
            seconds=2
        )

        # Force to HALF_OPEN by making a call
        circuit_breaker.stats.state = CircuitBreakerState.HALF_OPEN
        circuit_breaker.stats.failure_count = 0
        circuit_breaker.stats.success_count = 0

        # Make successful calls to reach success threshold
        for _ in range(2):  # success_threshold = 2
            result = await circuit_breaker.call(sometimes_failing_func, False)
            assert result == {"success": True}

        # Should now be CLOSED
        assert circuit_breaker.stats.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_sync_function_support(self, circuit_breaker):
        """Test circuit breaker with synchronous functions."""

        def sync_success_func():
            return {"sync": True}

        def sync_failing_func():
            raise Exception("Sync error")

        # Test success
        result = await circuit_breaker.call(sync_success_func)
        assert result == {"sync": True}

        # Test failure
        with pytest.raises(Exception):
            await circuit_breaker.call(sync_failing_func)

    @pytest.mark.asyncio
    async def test_circuit_breaker_stats_tracking(self, circuit_breaker):
        """Test comprehensive stats tracking."""

        async def mixed_func(should_fail=False):
            if should_fail:
                raise Exception("Error")
            return {"success": True}

        # Mix of successes and failures
        await circuit_breaker.call(mixed_func, False)  # Success
        with pytest.raises(Exception):
            await circuit_breaker.call(mixed_func, True)  # Failure
        await circuit_breaker.call(mixed_func, False)  # Success

        stats = circuit_breaker.get_stats()
        assert stats.total_calls == 3
        assert stats.total_successes == 2
        assert stats.total_failures == 1
        assert stats.last_success_time is not None
        assert stats.last_failure_time is not None

    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self, circuit_breaker):
        """Test manual circuit breaker reset."""

        async def failing_func():
            raise Exception("Service error")

        # Force to OPEN state
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.stats.state == CircuitBreakerState.OPEN

        # Reset manually
        await circuit_breaker.reset()

        assert circuit_breaker.stats.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.stats.failure_count == 0
        assert circuit_breaker.stats.success_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_unexpected_exception(self, circuit_breaker):
        """Test handling of unexpected exceptions."""

        async def unexpected_error_func():
            raise KeyError("Unexpected error type")

        # Configure to only catch Exception (which includes KeyError)
        # This should still be caught and counted as failure
        with pytest.raises(KeyError):
            await circuit_breaker.call(unexpected_error_func)

        # Should count as failure since KeyError is subclass of Exception
        assert circuit_breaker.stats.failure_count == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_no_fallback(self):
        """Test circuit breaker without fallback enabled."""
        config = CircuitBreakerConfig(failure_threshold=2, fallback_enabled=False)
        cb = CircuitBreaker("no_fallback", config)

        async def failing_func():
            raise Exception("Service error")

        # Force to OPEN state
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        # Should raise CircuitBreakerError, not return fallback
        with pytest.raises(CircuitBreakerError):
            await cb.call(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_breaker_concurrent_access(self, circuit_breaker):
        """Test circuit breaker with concurrent access."""

        async def slow_func(delay=0.1, should_fail=False):
            await asyncio.sleep(delay)
            if should_fail:
                raise Exception("Slow error")
            return {"completed": True}

        # Run multiple concurrent operations
        tasks = []
        for i in range(5):
            # Create a bound function to avoid lambda closure issues
            should_fail = i % 2 == 0
            task = asyncio.create_task(
                circuit_breaker.call(slow_func, 0.05, should_fail)
            )
            tasks.append(task)

        # Wait for all to complete (some will fail)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check that we got a mix of results and exceptions
        successes = [r for r in results if isinstance(r, dict)]
        failures = [r for r in results if isinstance(r, Exception)]

        assert len(successes) + len(failures) == 5
        assert len(successes) > 0  # Some should succeed
        assert len(failures) > 0  # Some should fail


class TestCircuitBreakerRegistry:
    """Test suite for CircuitBreakerRegistry."""

    def test_get_or_create_circuit_breaker(self):
        """Test getting or creating circuit breakers."""
        registry = get_registry()

        # Clear registry for clean test
        registry._breakers.clear()

        # Create new circuit breaker
        cb1 = registry.get_or_create("service1")
        assert cb1.name == "service1"

        # Get existing circuit breaker
        cb2 = registry.get_or_create("service1")
        assert cb1 is cb2  # Should be same instance

        # Create different circuit breaker
        cb3 = registry.get_or_create("service2")
        assert cb3.name == "service2"
        assert cb3 is not cb1

    def test_get_circuit_breaker_function(self):
        """Test the get_circuit_breaker convenience function."""
        # Clear registry
        get_registry()._breakers.clear()

        cb1 = get_circuit_breaker("api_service")
        cb2 = get_circuit_breaker("api_service")

        assert cb1 is cb2
        assert cb1.name == "api_service"

    def test_custom_circuit_breaker_config(self):
        """Test creating circuit breaker with custom config."""
        config = CircuitBreakerConfig(
            failure_threshold=5, success_threshold=3, timeout=30.0
        )

        cb = get_circuit_breaker("custom_service", config)

        assert cb.config.failure_threshold == 5
        assert cb.config.success_threshold == 3
        assert cb.config.timeout == 30.0

    @pytest.mark.asyncio
    async def test_registry_get_all_stats(self):
        """Test getting stats for all circuit breakers."""
        registry = get_registry()
        registry._breakers.clear()

        # Create and use some circuit breakers
        cb1 = registry.get_or_create("service1")
        cb2 = registry.get_or_create("service2")

        async def success_func():
            return True

        await cb1.call(success_func)
        await cb2.call(success_func)

        # Get all stats
        all_stats = registry.get_all_stats()

        assert len(all_stats) == 2
        assert "service1" in all_stats
        assert "service2" in all_stats
        assert all_stats["service1"].total_successes == 1
        assert all_stats["service2"].total_successes == 1

    @pytest.mark.asyncio
    async def test_registry_reset_all(self):
        """Test resetting all circuit breakers."""
        registry = get_registry()
        registry._breakers.clear()

        # Create circuit breakers and force failures
        cb1 = registry.get_or_create("service1")
        cb2 = registry.get_or_create("service2")

        async def failing_func():
            raise Exception("Error")

        # Generate some failures
        for _ in range(2):
            with pytest.raises(Exception):
                await cb1.call(failing_func)
            with pytest.raises(Exception):
                await cb2.call(failing_func)

        # Verify failures recorded
        assert cb1.stats.failure_count == 2
        assert cb2.stats.failure_count == 2

        # Reset all
        await registry.reset_all()

        # Verify all reset
        assert cb1.stats.failure_count == 0
        assert cb2.stats.failure_count == 0
        assert cb1.stats.state == CircuitBreakerState.CLOSED
        assert cb2.stats.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker with other components."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_webhook_simulation(self):
        """Test circuit breaker protecting webhook calls."""
        import aiohttp

        # Create circuit breaker with lower failure threshold for testing
        config = CircuitBreakerConfig(failure_threshold=3, fallback_enabled=True)
        cb = get_circuit_breaker("webhook_test", config)
        await cb.reset()  # Ensure clean state

        async def mock_webhook_call(url, should_fail=False):
            """Simulate a webhook call."""
            if should_fail:
                raise aiohttp.ClientError("Connection failed")
            return {"status": "success", "data": "webhook response"}

        # Test successful webhook calls
        result = await cb.call(mock_webhook_call, "https://api.example.com", False)
        assert result["status"] == "success"

        # Test webhook failures leading to circuit opening
        for _ in range(3):  # Default failure threshold
            with pytest.raises(aiohttp.ClientError):
                await cb.call(mock_webhook_call, "https://api.example.com", True)

        assert cb.stats.state == CircuitBreakerState.OPEN

        # Subsequent calls should be rejected or return fallback
        try:
            result = await cb.call(mock_webhook_call, "https://api.example.com", True)
            # If fallback is enabled, we get fallback response
            assert "fallback" in result or result is None
        except CircuitBreakerError:
            # If no fallback, we get circuit breaker error
            pass

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_simulation(self):
        """Test circuit breaker recovery in realistic scenario."""
        # Create circuit breaker with lower failure threshold for testing
        config = CircuitBreakerConfig(
            failure_threshold=3, success_threshold=2, fallback_enabled=True
        )
        cb = get_circuit_breaker("recovery_test", config)
        await cb.reset()  # Clean state

        call_results = []

        async def api_call(service_healthy=True):
            """Simulate API that can be healthy or unhealthy."""
            if not service_healthy:
                raise Exception("Service unavailable")
            return {"timestamp": datetime.utcnow().isoformat(), "healthy": True}

        # Phase 1: Service is healthy
        for _ in range(5):
            result = await cb.call(api_call, True)
            call_results.append(("success", result))

        assert cb.stats.state == CircuitBreakerState.CLOSED

        # Phase 2: Service becomes unhealthy
        for _ in range(3):
            try:
                result = await cb.call(api_call, False)
                call_results.append(("success", result))
            except Exception as e:
                call_results.append(("failure", str(e)))

        assert cb.stats.state == CircuitBreakerState.OPEN

        # Phase 3: Circuit is open, calls are rejected
        for _ in range(3):
            try:
                result = await cb.call(api_call, False)
                call_results.append(("fallback", result))
            except CircuitBreakerError:
                call_results.append(("rejected", "Circuit breaker open"))

        # Phase 4: Simulate timeout and recovery
        cb.stats.last_failure_time = datetime.utcnow() - timedelta(seconds=2)
        cb.stats.state = CircuitBreakerState.HALF_OPEN
        cb.stats.failure_count = 0
        cb.stats.success_count = 0

        # Service becomes healthy again
        for _ in range(2):  # success_threshold = 2
            result = await cb.call(api_call, True)
            call_results.append(("recovery", result))

        assert cb.stats.state == CircuitBreakerState.CLOSED

        # Verify the sequence of events
        success_count = len([r for r in call_results if r[0] == "success"])
        failure_count = len([r for r in call_results if r[0] == "failure"])
        recovery_count = len([r for r in call_results if r[0] == "recovery"])

        assert success_count == 5  # Initial healthy calls
        assert failure_count == 3  # Failures that opened circuit
        assert recovery_count == 2  # Recovery calls that closed circuit
