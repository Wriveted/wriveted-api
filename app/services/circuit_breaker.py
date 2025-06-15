"""
Circuit breaker implementation for external service calls.

Provides resilient handling of external API calls with failure detection,
automatic recovery, and graceful degradation.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, calls rejected
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 3  # Successes to close from half-open
    timeout: float = 60.0  # Seconds before trying half-open
    expected_exception: tuple = (Exception,)  # Exceptions that count as failures

    # Optional fallback configuration
    fallback_enabled: bool = True
    fallback_response: Optional[Dict[str, Any]] = None


class CircuitBreakerStats(BaseModel):
    """Circuit breaker statistics and metrics."""

    state: CircuitBreakerState
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreakerError(Exception):
    """Raised when circuit breaker rejects a call."""

    def __init__(
        self, message: str, state: CircuitBreakerState, stats: CircuitBreakerStats
    ):
        super().__init__(message)
        self.state = state
        self.stats = stats


class CircuitBreaker:
    """
    Circuit breaker for protecting against failing external services.

    Monitors failure rates and automatically prevents calls to failing
    services, with automatic recovery testing.
    """

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.stats = CircuitBreakerStats(state=CircuitBreakerState.CLOSED)
        self._lock = asyncio.Lock()

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function call through the circuit breaker.

        Args:
            func: Function to call
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open and rejecting calls
        """
        async with self._lock:
            self.stats.total_calls += 1

            # Check if we should allow the call
            if not self._should_allow_call():
                logger.warning(
                    f"Circuit breaker {self.name} rejecting call - state: {self.stats.state}"
                )

                # Return fallback response if configured
                if (
                    self.config.fallback_enabled
                    and self.config.fallback_response is not None
                ):
                    logger.info(
                        f"Circuit breaker {self.name} returning fallback response"
                    )
                    return self.config.fallback_response

                raise CircuitBreakerError(
                    f"Circuit breaker {self.name} is {self.stats.state.value}",
                    self.stats.state,
                    self.stats,
                )

        # Execute the call
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Record success
            await self._record_success()
            return result

        except self.config.expected_exception as e:
            # Record failure for expected exceptions
            await self._record_failure()
            raise
        except Exception as e:
            # Unexpected exceptions are not counted as circuit breaker failures
            logger.error(f"Unexpected error in circuit breaker {self.name}: {e}")
            raise

    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self.stats.success_count += 1
            self.stats.total_successes += 1
            self.stats.last_success_time = datetime.utcnow()

            logger.debug(
                f"Circuit breaker {self.name} recorded success - count: {self.stats.success_count}"
            )

            # Transition states based on success
            if self.stats.state == CircuitBreakerState.HALF_OPEN:
                if self.stats.success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            elif self.stats.state == CircuitBreakerState.OPEN:
                # This shouldn't happen, but reset if it does
                self._transition_to_closed()

    async def _record_failure(self) -> None:
        """Record a failed call."""
        async with self._lock:
            self.stats.failure_count += 1
            self.stats.total_failures += 1
            self.stats.last_failure_time = datetime.utcnow()

            logger.warning(
                f"Circuit breaker {self.name} recorded failure - count: {self.stats.failure_count}"
            )

            # Transition states based on failure
            if self.stats.state == CircuitBreakerState.CLOSED:
                if self.stats.failure_count >= self.config.failure_threshold:
                    self._transition_to_open()
            elif self.stats.state == CircuitBreakerState.HALF_OPEN:
                # Any failure in half-open state goes back to open
                self._transition_to_open()

    def _should_allow_call(self) -> bool:
        """Check if a call should be allowed based on current state."""
        if self.stats.state == CircuitBreakerState.CLOSED:
            return True
        elif self.stats.state == CircuitBreakerState.OPEN:
            # Check if timeout has passed
            if self.stats.last_failure_time:
                time_since_failure = datetime.utcnow() - self.stats.last_failure_time
                if time_since_failure.total_seconds() >= self.config.timeout:
                    self._transition_to_half_open()
                    return True
            return False
        elif self.stats.state == CircuitBreakerState.HALF_OPEN:
            return True

        return False

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        logger.info(f"Circuit breaker {self.name} transitioning to CLOSED")
        self.stats.state = CircuitBreakerState.CLOSED
        self.stats.failure_count = 0
        self.stats.success_count = 0

    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        logger.warning(f"Circuit breaker {self.name} transitioning to OPEN")
        self.stats.state = CircuitBreakerState.OPEN
        self.stats.success_count = 0

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
        self.stats.state = CircuitBreakerState.HALF_OPEN
        self.stats.failure_count = 0
        self.stats.success_count = 0

    def get_stats(self) -> CircuitBreakerStats:
        """Get current circuit breaker statistics."""
        return self.stats.copy()

    async def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        async with self._lock:
            logger.info(f"Manually resetting circuit breaker {self.name}")
            self._transition_to_closed()


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_or_create(
        self, name: str, config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create new one."""
        if name not in self._breakers:
            if config is None:
                config = CircuitBreakerConfig()
            self._breakers[name] = CircuitBreaker(name, config)

        return self._breakers[name]

    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers."""
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}

    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            await breaker.reset()


# Global registry instance
_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str, config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """Get or create a circuit breaker from the global registry."""
    return _registry.get_or_create(name, config)


def get_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    return _registry
