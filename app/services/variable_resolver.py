"""
Enhanced variable resolution system for chatbot flows.

Supports all variable scopes with validation and nested object access:
- {{user.name}} - User data (session scope)
- {{context.locale}} - Context variables (session scope)
- {{temp.current_book}} - Temporary variables (session scope)
- {{input.user_age}} - Composite node input variables
- {{output.reading_level}} - Composite node output variables
- {{local.temp_value}} - Local scope variables (node-specific)
- {{secret:api_key}} - Secret references (injected at runtime)
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class VariableScope(BaseModel):
    """Represents a variable scope with validation rules."""

    name: str
    data: Dict[str, Any]
    read_only: bool = False
    description: str = ""


class VariableReference(BaseModel):
    """Parsed variable reference with scope and path information."""

    scope: str  # user, context, temp, input, output, local, secret
    path: str  # The part after the scope (e.g., "name" in user.name)
    full_path: str  # Complete path including scope
    is_secret: bool = False


class VariableValidationError(Exception):
    """Raised when variable reference validation fails."""

    pass


class VariableResolver:
    """
    Enhanced variable resolution system with scope management.

    Provides secure, validated variable substitution with support for
    all chatbot variable scopes and nested object access.
    """

    def __init__(self):
        self.scopes: Dict[str, VariableScope] = {}
        self.secret_resolver: Optional[Callable[[str], str]] = None

        # Variable reference pattern: {{scope.path}} or {{secret:key}}
        self.variable_pattern = re.compile(r"\{\{([^}]+)\}\}")
        self.secret_pattern = re.compile(r"^secret:(.+)$")

        # Valid scope names
        self.valid_scopes = {"user", "context", "temp", "input", "output", "local"}

    def set_secret_resolver(self, resolver: Callable[[str], str]) -> None:
        """Set the secret resolver function for {{secret:key}} references."""
        self.secret_resolver = resolver

    def set_scope(
        self,
        scope_name: str,
        data: Dict[str, Any],
        read_only: bool = False,
        description: str = "",
    ) -> None:
        """Set data for a specific variable scope."""
        if scope_name not in self.valid_scopes:
            raise ValueError(
                f"Invalid scope '{scope_name}'. Valid scopes: {self.valid_scopes}"
            )

        self.scopes[scope_name] = VariableScope(
            name=scope_name,
            data=data or {},
            read_only=read_only,
            description=description,
        )

    def get_scope_data(self, scope_name: str) -> Dict[str, Any]:
        """Get data for a specific scope."""
        scope = self.scopes.get(scope_name)
        return scope.data if scope else {}

    def update_scope_variable(self, scope_name: str, path: str, value: Any) -> None:
        """Update a variable in a specific scope."""
        if scope_name not in self.scopes:
            self.scopes[scope_name] = VariableScope(name=scope_name, data={})

        scope = self.scopes[scope_name]
        if scope.read_only:
            raise VariableValidationError(
                f"Cannot modify read-only scope '{scope_name}'"
            )

        self._set_nested_value(scope.data, path, value)

    def set_composite_scopes(self, composite_scope: Dict[str, Any]) -> None:
        """Set up composite node scopes (input, output, local, temp)."""
        for scope_name, scope_data in composite_scope.items():
            if isinstance(scope_data, dict):
                self.set_scope(scope_name, scope_data)

    def parse_variable_reference(self, variable_str: str) -> VariableReference:
        """
        Parse a variable reference string into components.

        Args:
            variable_str: Variable string like "user.name" or "secret:api_key"

        Returns:
            VariableReference with parsed components
        """
        # Check for secret reference
        secret_match = self.secret_pattern.match(variable_str)
        if secret_match:
            return VariableReference(
                scope="secret",
                path=secret_match.group(1),
                full_path=variable_str,
                is_secret=True,
            )

        # Parse regular scope.path reference
        parts = variable_str.split(".", 1)
        if len(parts) < 2:
            raise VariableValidationError(
                f"Invalid variable reference: '{variable_str}'. Expected format: 'scope.path'"
            )

        scope, path = parts

        if scope not in self.valid_scopes:
            raise VariableValidationError(
                f"Invalid scope '{scope}'. Valid scopes: {self.valid_scopes}"
            )

        return VariableReference(
            scope=scope, path=path, full_path=variable_str, is_secret=False
        )

    def resolve_variable(self, variable_ref: VariableReference) -> Any:
        """
        Resolve a single variable reference to its value.

        Args:
            variable_ref: Parsed variable reference

        Returns:
            The resolved value or None if not found
        """
        if variable_ref.is_secret:
            if not self.secret_resolver:
                logger.warning(
                    f"No secret resolver configured for {variable_ref.full_path}"
                )
                return None

            try:
                return self.secret_resolver(variable_ref.path)
            except Exception as e:
                logger.error(f"Failed to resolve secret '{variable_ref.path}': {e}")
                return None

        # Resolve from scope data
        scope = self.scopes.get(variable_ref.scope)
        if not scope:
            logger.debug(f"Scope '{variable_ref.scope}' not found")
            return None

        return self._get_nested_value(scope.data, variable_ref.path)

    def substitute_variables(self, text: str, preserve_unresolved: bool = True) -> str:
        """
        Substitute all variable references in text.

        Args:
            text: Text containing variable references like {{user.name}}
            preserve_unresolved: If True, keep unresolved variables as-is

        Returns:
            Text with variables substituted
        """
        if not isinstance(text, str):
            return str(text) if text is not None else ""

        def replace_variable(match):
            variable_str = match.group(1).strip()

            try:
                variable_ref = self.parse_variable_reference(variable_str)
                value = self.resolve_variable(variable_ref)

                if value is not None:
                    # Convert to string, handling special types
                    if isinstance(value, (dict, list)):
                        return json.dumps(value)
                    elif isinstance(value, datetime):
                        return value.isoformat()
                    elif isinstance(value, UUID):
                        return str(value)
                    else:
                        return str(value)
                else:
                    # Variable not found
                    if preserve_unresolved:
                        return match.group(0)  # Return original {{var}}
                    else:
                        return ""

            except VariableValidationError as e:
                logger.warning(f"Variable validation error: {e}")
                if preserve_unresolved:
                    return match.group(0)
                else:
                    return ""
            except Exception as e:
                logger.error(f"Error resolving variable '{variable_str}': {e}")
                if preserve_unresolved:
                    return match.group(0)
                else:
                    return ""

        return self.variable_pattern.sub(replace_variable, text)

    def substitute_object(self, obj: Any, preserve_unresolved: bool = True) -> Any:
        """
        Recursively substitute variables in complex objects.

        When the entire value is a single variable reference (e.g. "{{user.age}}"),
        the raw typed value is returned (int, dict, list, etc.) instead of a string.
        Mixed templates like "Hello {{user.name}}" still return strings.

        Args:
            obj: Object to process (dict, list, string, etc.)
            preserve_unresolved: If True, keep unresolved variables as-is

        Returns:
            Object with variables substituted
        """
        if isinstance(obj, str):
            # Check if the entire string is a single variable reference
            stripped = obj.strip()
            match = self.variable_pattern.fullmatch(stripped)
            if match:
                variable_str = match.group(1).strip()
                try:
                    variable_ref = self.parse_variable_reference(variable_str)
                    value = self.resolve_variable(variable_ref)
                    if value is not None:
                        return value
                    elif preserve_unresolved:
                        return obj
                    else:
                        return None
                except VariableValidationError:
                    if preserve_unresolved:
                        return obj
                    return None
            # Multiple references or mixed text — fall back to string substitution
            return self.substitute_variables(obj, preserve_unresolved)
        elif isinstance(obj, dict):
            return {
                key: self.substitute_object(value, preserve_unresolved)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [self.substitute_object(item, preserve_unresolved) for item in obj]
        else:
            return obj

    def extract_variable_references(self, text: str) -> List[VariableReference]:
        """
        Extract all variable references from text.

        Args:
            text: Text to analyze

        Returns:
            List of parsed variable references
        """
        if not isinstance(text, str):
            return []

        references = []
        for match in self.variable_pattern.finditer(text):
            variable_str = match.group(1).strip()
            try:
                ref = self.parse_variable_reference(variable_str)
                references.append(ref)
            except VariableValidationError:
                # Skip invalid references
                pass

        return references

    def validate_variable_references(self, text: str) -> List[str]:
        """
        Validate all variable references in text.

        Args:
            text: Text to validate

        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []

        # Find all variable patterns, including invalid ones
        for match in self.variable_pattern.finditer(text):
            variable_str = match.group(1).strip()

            try:
                # Try to parse the variable reference
                ref = self.parse_variable_reference(variable_str)

                # Check if scope exists (except for secrets)
                if not ref.is_secret and ref.scope not in self.scopes:
                    errors.append(
                        f"Undefined scope '{ref.scope}' in variable '{ref.full_path}'"
                    )
                    continue  # Skip to next reference if scope is invalid

                # Check if variable exists in scope
                value = self.resolve_variable(ref)
                if value is None and not ref.is_secret:
                    errors.append(
                        f"Variable '{ref.full_path}' not found in scope '{ref.scope}'"
                    )

            except VariableValidationError as e:
                # This catches invalid scopes and malformed references
                errors.append(str(e))
            except Exception as e:
                errors.append(
                    f"Error validating variable '{{{{{variable_str}}}}}': {e}"
                )

        return errors

    def get_available_variables(self) -> Dict[str, List[str]]:
        """
        Get a list of all available variables by scope.

        Returns:
            Dictionary mapping scope names to lists of available variable paths
        """
        result = {}
        for scope_name, scope in self.scopes.items():
            variables = self._flatten_dict_keys(scope.data)
            result[scope_name] = variables

        return result

    def _get_nested_value(self, data: Dict[str, Any], key_path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        keys = key_path.split(".")
        value = data

        try:
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                elif isinstance(value, list) and key.isdigit():
                    index = int(key)
                    value = value[index] if 0 <= index < len(value) else None
                else:
                    return None
            return value
        except (KeyError, TypeError, ValueError, IndexError):
            return None

    def _set_nested_value(
        self, data: Dict[str, Any], key_path: str, value: Any
    ) -> None:
        """Set nested value in dictionary using dot notation."""
        keys = key_path.split(".")
        current = data

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

    def _flatten_dict_keys(self, data: Dict[str, Any], prefix: str = "") -> List[str]:
        """Recursively flatten dictionary keys into dot-notation paths."""
        keys = []

        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.append(full_key)

            if isinstance(value, dict):
                keys.extend(self._flatten_dict_keys(value, full_key))

        return keys


# Example secret resolver using Google Secret Manager
async def google_secret_resolver(secret_key: str) -> Optional[str]:
    """
    Example secret resolver for Google Secret Manager.

    Args:
        secret_key: Secret key to resolve

    Returns:
        Secret value or None if not found
    """
    try:
        # Import here to avoid dependency issues
        from google.cloud import secretmanager  # type: ignore

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/your-project/secrets/{secret_key}/versions/latest"

        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")

    except Exception as e:
        logger.error(f"Failed to resolve secret '{secret_key}': {e}")
        return None


# Factory function for creating resolver with session state
def create_session_resolver(
    session_state: Dict[str, Any],
    composite_scopes: Optional[Dict[str, Dict[str, Any]]] = None,
) -> VariableResolver:
    """
    Create a variable resolver initialized with session state.

    Args:
        session_state: Current session state dictionary
        composite_scopes: Additional scopes for composite nodes (input, output, local)

    Returns:
        Configured VariableResolver instance
    """
    resolver = VariableResolver()

    # Set up main session scopes
    resolver.set_scope(
        "user",
        session_state.get("user", {}),
        read_only=True,
        description="User profile data",
    )
    resolver.set_scope(
        "context",
        session_state.get("context", {}),
        read_only=True,
        description="Session context variables",
    )
    resolver.set_scope(
        "temp", session_state.get("temp", {}), description="Temporary session variables"
    )

    # Set up composite node scopes if provided
    if composite_scopes:
        for scope_name, scope_data in composite_scopes.items():
            read_only = scope_name == "input"  # Input is read-only
            resolver.set_scope(scope_name, scope_data, read_only=read_only)

    return resolver
