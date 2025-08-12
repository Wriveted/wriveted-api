"""
Internal API client for api_call action type.

Provides secure, authenticated API calls to internal Wriveted services
with proper authentication, error handling, and response processing.
"""

import logging
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel

from app.config import get_settings
from app.services.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerError,
    get_circuit_breaker,
)

logger = logging.getLogger(__name__)


class ApiCallConfig(BaseModel):
    """Configuration for an API call action."""

    endpoint: str  # API endpoint path (e.g., "/api/recommendations")
    method: str = "GET"  # HTTP method
    headers: Dict[str, str] = {}  # Additional headers
    query_params: Dict[str, Any] = {}  # Query parameters
    body: Optional[Dict[str, Any]] = None  # Request body
    timeout: int = 30  # Request timeout in seconds

    # Authentication
    auth_type: str = "internal"  # internal, bearer, api_key, none
    auth_config: Dict[str, Any] = {}  # Auth-specific configuration

    # Response handling
    response_mapping: Dict[str, str] = {}  # Map response fields to session variables
    store_full_response: bool = False  # Store entire response
    response_variable: str = "api_response"  # Variable name for response storage
    error_variable: Optional[str] = None  # Variable name for error storage

    # Circuit breaker configuration
    circuit_breaker: Dict[str, Any] = {}
    fallback_response: Optional[Dict[str, Any]] = None


class ApiCallResult(BaseModel):
    """Result of an API call action."""

    success: bool
    status_code: Optional[int] = None
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    variables_updated: Dict[str, Any] = {}
    circuit_breaker_used: bool = False
    fallback_used: bool = False


class InternalApiClient:
    """
    Client for making authenticated API calls to internal Wriveted services.

    Handles authentication, circuit breaker protection, and response mapping
    for api_call action types in chatbot flows.
    """

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.WRIVETED_INTERNAL_API
        self.session: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize the HTTP client."""
        if not self.session:
            # Configure client with authentication headers
            headers = {
                "User-Agent": "Wriveted-Chatbot/1.0",
                "Content-Type": "application/json",
            }

            # Add internal service authentication
            if hasattr(self.settings, "INTERNAL_API_KEY"):
                headers["Authorization"] = f"Bearer {self.settings.INTERNAL_API_KEY}"

            self.session = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(60.0),
                follow_redirects=True,
            )

    async def shutdown(self) -> None:
        """Shutdown the HTTP client."""
        if self.session:
            await self.session.aclose()
            self.session = None

    async def execute_api_call(
        self,
        config: ApiCallConfig,
        session_state: Dict[str, Any],
        composite_scopes: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> ApiCallResult:
        """
        Execute an API call with the given configuration.

        Args:
            config: API call configuration
            session_state: Current session state for variable substitution
            composite_scopes: Additional variable scopes (for composite nodes)

        Returns:
            ApiCallResult with response data and updated variables
        """
        if not self.session:
            await self.initialize()

        result = ApiCallResult(success=False)

        try:
            # Substitute variables in configuration
            resolved_config = self._resolve_variables(
                config, session_state, composite_scopes
            )

            # Set up circuit breaker
            circuit_breaker = self._get_api_circuit_breaker(resolved_config)

            # Execute API call through circuit breaker
            response_data = await circuit_breaker.call(
                self._make_api_request, resolved_config
            )

            result.success = True
            result.response_data = response_data
            result.circuit_breaker_used = True

            # Process response and update variables
            result.variables_updated = self._process_response(
                resolved_config, response_data
            )

            logger.info(
                "API call successful",
                endpoint=resolved_config.endpoint,
                method=resolved_config.method,
                status_code=getattr(response_data, "status_code", None),
            )

        except CircuitBreakerError as e:
            # Circuit breaker is open
            result.error_message = f"Circuit breaker open: {e}"
            result.circuit_breaker_used = True

            # Use fallback response if available
            if config.fallback_response:
                result.response_data = config.fallback_response
                result.success = True
                result.fallback_used = True
                result.variables_updated = self._process_response(
                    config, config.fallback_response
                )
                logger.info(
                    "Using API call fallback response", endpoint=config.endpoint
                )

        except httpx.HTTPStatusError as e:
            result.error_message = (
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )
            result.status_code = e.response.status_code
            logger.error(
                "API call HTTP error",
                endpoint=config.endpoint,
                status=e.response.status_code,
            )

        except httpx.TimeoutException:
            result.error_message = "API call timed out"
            logger.error(
                "API call timeout", endpoint=config.endpoint, timeout=config.timeout
            )

        except Exception as e:
            result.error_message = f"API call failed: {str(e)}"
            logger.error("API call error", endpoint=config.endpoint, error=str(e))

        return result

    def _resolve_variables(
        self,
        config: ApiCallConfig,
        session_state: Dict[str, Any],
        composite_scopes: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> ApiCallConfig:
        """Resolve variables in API call configuration."""
        from app.services.variable_resolver import create_session_resolver

        resolver = create_session_resolver(session_state, composite_scopes)

        # Create a copy to avoid modifying original
        resolved_data = config.model_dump()

        # Resolve variables in all string fields
        resolved_data = resolver.substitute_object(resolved_data)

        return ApiCallConfig(**resolved_data)

    def _get_api_circuit_breaker(self, config: ApiCallConfig):
        """Get or create circuit breaker for API endpoint."""
        # Create circuit breaker name from endpoint
        endpoint_key = config.endpoint.replace("/", "_").replace("-", "_")
        circuit_name = f"api_call_{endpoint_key}"

        # Configure circuit breaker
        circuit_config = CircuitBreakerConfig(
            failure_threshold=config.circuit_breaker.get("failure_threshold", 5),
            success_threshold=config.circuit_breaker.get("success_threshold", 3),
            timeout=config.circuit_breaker.get("timeout", 60.0),
            expected_exception=(
                httpx.RequestError,
                httpx.HTTPStatusError,
                httpx.TimeoutException,
            ),
            fallback_enabled=config.fallback_response is not None,
            fallback_response=config.fallback_response,
        )

        return get_circuit_breaker(circuit_name, circuit_config)

    async def _make_api_request(self, config: ApiCallConfig) -> Dict[str, Any]:
        """Make the actual API request."""
        # Prepare authentication
        headers = dict(config.headers)

        if config.auth_type == "bearer" and config.auth_config.get("token"):
            headers["Authorization"] = f"Bearer {config.auth_config['token']}"
        elif config.auth_type == "api_key":
            key_name = config.auth_config.get("header", "X-API-Key")
            headers[key_name] = config.auth_config.get("key", "")

        # Make request
        response = await self.session.request(
            method=config.method,
            url=config.endpoint,
            headers=headers,
            params=config.query_params,
            json=config.body
            if config.method.upper() in ["POST", "PUT", "PATCH"]
            else None,
            timeout=config.timeout,
        )

        response.raise_for_status()

        # Parse response
        try:
            return response.json()
        except:
            return {
                "status": response.status_code,
                "text": response.text[:1000] if response.text else None,
            }

    def _process_response(
        self, config: ApiCallConfig, response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process API response and extract variables."""
        variables = {}

        # Store full response if requested
        if config.store_full_response:
            variables[config.response_variable] = response_data

        # Apply response mapping
        for response_path, variable_name in config.response_mapping.items():
            value = self._extract_response_value(response_data, response_path)
            if value is not None:
                variables[variable_name] = value

        return variables

    def _extract_response_value(self, data: Dict[str, Any], path: str) -> Any:
        """Extract value from response using JSONPath-like syntax."""
        # Simple dot notation support (can be enhanced with full JSONPath later)
        keys = path.split(".")
        current = data

        try:
            for key in keys:
                if isinstance(current, dict):
                    current = current.get(key)
                elif isinstance(current, list) and key.isdigit():
                    index = int(key)
                    current = current[index] if 0 <= index < len(current) else None
                else:
                    return None
            return current
        except (KeyError, TypeError, ValueError, IndexError):
            return None


# Global client instance
_api_client: Optional[InternalApiClient] = None


def get_api_client() -> InternalApiClient:
    """Get the global API client instance."""
    global _api_client
    if _api_client is None:
        _api_client = InternalApiClient()
    return _api_client


# Example API call configurations for common Wriveted endpoints


def create_book_recommendations_call(
    user_id: str, preferences: Dict[str, Any]
) -> ApiCallConfig:
    """Create API call config for book recommendations."""
    return ApiCallConfig(
        endpoint="/api/recommendations",
        method="POST",
        body={"user_id": user_id, "preferences": preferences, "limit": 10},
        response_mapping={
            "recommendations": "recommendations",
            "count": "recommendation_count",
        },
        timeout=15,
        circuit_breaker={"failure_threshold": 3, "timeout": 30.0},
        fallback_response={"recommendations": [], "count": 0, "fallback": True},
    )


def create_user_profile_call(user_id: str) -> ApiCallConfig:
    """Create API call config for user profile data."""
    return ApiCallConfig(
        endpoint=f"/api/users/{user_id}/profile",
        method="GET",
        response_mapping={
            "reading_level": "user.reading_level",
            "interests": "user.interests",
            "reading_history": "user.reading_history",
        },
        timeout=10,
        circuit_breaker={"failure_threshold": 5},
        fallback_response={
            "reading_level": "intermediate",
            "interests": [],
            "reading_history": [],
        },
    )


def create_reading_assessment_call(
    user_id: str, assessment_data: Dict[str, Any]
) -> ApiCallConfig:
    """Create API call config for reading level assessment."""
    return ApiCallConfig(
        endpoint="/api/assessment/reading-level",
        method="POST",
        body={"user_id": user_id, "assessment_data": assessment_data},
        response_mapping={
            "reading_level": "assessment.reading_level",
            "confidence": "assessment.confidence",
            "recommendations": "assessment.next_steps",
        },
        timeout=20,
        circuit_breaker={"failure_threshold": 3, "timeout": 45.0},
    )
