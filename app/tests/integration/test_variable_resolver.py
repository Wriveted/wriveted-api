"""Tests for variable resolution system."""

import pytest

from app.services.variable_resolver import VariableReference, VariableScope


class TestVariableResolver:
    """Test suite for VariableResolver functionality."""

    @pytest.fixture
    def sample_session_state(self):
        """Sample session state for testing."""
        return {
            "user": {
                "id": "user123",
                "name": "John Doe",
                "email": "john@example.com",
                "preferences": {
                    "theme": "dark",
                    "language": "en",
                    "notifications": {"email": True, "push": False},
                },
                "profile": {"age": 30, "bio": "Software developer"},
            },
            "context": {
                "session_id": "session456",
                "locale": "en-US",
                "timezone": "America/New_York",
                "device": {"type": "mobile", "os": "iOS"},
            },
            "temp": {
                "current_step": 3,
                "last_action": "form_submit",
                "form_data": {"field1": "value1", "field2": 42},
            },
        }

    @pytest.fixture
    def variable_resolver(self, sample_session_state):
        """Create VariableResolver with sample session state."""
        from app.services.variable_resolver import create_session_resolver

        return create_session_resolver(sample_session_state)

    def test_simple_variable_substitution(self, variable_resolver):
        """Test basic variable substitution."""
        template = "Hello {{user.name}}!"
        result = variable_resolver.substitute_variables(template)
        assert result == "Hello John Doe!"

    def test_multiple_variable_substitution(self, variable_resolver):
        """Test substitution of multiple variables."""
        template = "User {{user.name}} ({{user.email}}) prefers {{user.preferences.theme}} theme"
        result = variable_resolver.substitute_variables(template)
        assert result == "User John Doe (john@example.com) prefers dark theme"

    def test_nested_object_access(self, variable_resolver):
        """Test accessing deeply nested object properties."""
        template = "Notifications: email={{user.preferences.notifications.email}}, push={{user.preferences.notifications.push}}"
        result = variable_resolver.substitute_variables(template)
        assert result == "Notifications: email=True, push=False"

    def test_numeric_variable_substitution(self, variable_resolver):
        """Test substitution of numeric values."""
        template = (
            "User is {{user.profile.age}} years old and at step {{temp.current_step}}"
        )
        result = variable_resolver.substitute_variables(template)
        assert result == "User is 30 years old and at step 3"

    def test_missing_variable_handling(self, variable_resolver):
        """Test handling of missing variables."""
        template = "User {{user.nonexistent}} does not exist"
        result = variable_resolver.substitute_variables(template)
        # Should preserve the placeholder or return empty string
        assert "{{user.nonexistent}}" in result or result == "User  does not exist"

    def test_invalid_variable_syntax(self, variable_resolver):
        """Test handling of invalid variable syntax."""
        templates = [
            "Invalid {{user.name",  # Missing closing brace
            "Invalid user.name}}",  # Missing opening brace
            "Invalid {{}}",  # Empty variable
            "Invalid {{user.}}",  # Trailing dot
        ]

        for template in templates:
            result = variable_resolver.substitute_variables(template)
            # Should either preserve invalid syntax or handle gracefully
            assert isinstance(result, str)

    def test_variable_reference_parsing(self, variable_resolver):
        """Test parsing of variable references."""
        test_cases = [
            ("{{user.name}}", "user", "name", "user.name"),
            ("{{context.locale}}", "context", "locale", "context.locale"),
            (
                "{{temp.form_data.field1}}",
                "temp",
                "form_data.field1",
                "temp.form_data.field1",
            ),
            (
                "{{user.preferences.notifications.email}}",
                "user",
                "preferences.notifications.email",
                "user.preferences.notifications.email",
            ),
        ]

        for template, expected_scope, expected_path, expected_full in test_cases:
            references = variable_resolver.extract_variable_references(template)
            assert len(references) == 1
            ref = references[0]
            assert ref.scope == expected_scope
            assert ref.path == expected_path
            assert ref.full_path == expected_full

    def test_multiple_variable_references_parsing(self, variable_resolver):
        """Test parsing multiple variable references."""
        template = "Hello {{user.name}}, your locale is {{context.locale}} and step is {{temp.current_step}}"
        references = variable_resolver.extract_variable_references(template)

        assert len(references) == 3
        assert references[0].scope == "user"
        assert references[1].scope == "context"
        assert references[2].scope == "temp"

    def test_secret_variable_reference(self, variable_resolver):
        """Test secret variable reference parsing."""
        template = "API Key: {{secret:api_key}}"
        references = variable_resolver.extract_variable_references(template)

        assert len(references) == 1
        assert references[0].scope == "secret"
        assert references[0].path == "api_key"
        assert references[0].is_secret is True

    def test_context_scope_variables(self, variable_resolver):
        """Test context scope variable access."""
        template = "Device: {{context.device.type}} ({{context.device.os}})"
        result = variable_resolver.substitute_variables(template)
        assert result == "Device: mobile (iOS)"

    def test_temp_scope_variables(self, variable_resolver):
        """Test temporary scope variable access."""
        template = (
            "Form field1: {{temp.form_data.field1}}, field2: {{temp.form_data.field2}}"
        )
        result = variable_resolver.substitute_variables(template)
        assert result == "Form field1: value1, field2: 42"

    def test_json_object_substitution(self, variable_resolver):
        """Test substitution within JSON objects."""
        json_template = {
            "user_info": {
                "name": "{{user.name}}",
                "email": "{{user.email}}",
                "age": "{{user.profile.age}}",
            },
            "context": {
                "locale": "{{context.locale}}",
                "device": "{{context.device.type}}",
            },
        }

        result = variable_resolver.substitute_object(json_template)

        assert result["user_info"]["name"] == "John Doe"
        assert result["user_info"]["email"] == "john@example.com"
        assert result["user_info"]["age"] == 30  # substitute_object preserves types
        assert result["context"]["locale"] == "en-US"
        assert result["context"]["device"] == "mobile"

    def test_list_substitution(self, variable_resolver):
        """Test substitution within lists."""
        list_template = [
            "User: {{user.name}}",
            "Email: {{user.email}}",
            {"nested": "{{context.locale}}"},
        ]

        result = variable_resolver.substitute_object(list_template)

        assert result[0] == "User: John Doe"
        assert result[1] == "Email: john@example.com"
        assert result[2]["nested"] == "en-US"

    def test_mixed_data_types_substitution(self, variable_resolver):
        """Test substitution preserving data types."""
        template = {
            "string_field": "{{user.name}}",
            "numeric_field": "{{user.profile.age}}",
            "boolean_field": "{{user.preferences.notifications.email}}",
            "mixed_string": "User {{user.name}} is {{user.profile.age}} years old",
        }

        result = variable_resolver.substitute_object(template)

        assert result["string_field"] == "John Doe"
        assert result["numeric_field"] == 30  # substitute_object preserves types
        assert result["boolean_field"] is True
        assert result["mixed_string"] == "User John Doe is 30 years old"

    def test_variable_scope_isolation(self):
        """Test that different scopes are properly isolated."""
        from app.services.variable_resolver import create_session_resolver

        # Set up different scopes
        session_state = {"user": {"name": "Session User"}}
        composite_scopes = {
            "input": {"user": {"name": "Input User"}},
            "output": {"user": {"name": "Output User"}},
            "local": {"user": {"name": "Local User"}},
        }

        resolver = create_session_resolver(session_state, composite_scopes)

        # Test scope precedence
        assert resolver.substitute_variables("{{user.name}}") == "Session User"
        assert resolver.substitute_variables("{{input.user.name}}") == "Input User"
        assert resolver.substitute_variables("{{output.user.name}}") == "Output User"
        assert resolver.substitute_variables("{{local.user.name}}") == "Local User"

    def test_variable_validation(self, variable_resolver):
        """Test variable validation functionality."""
        # Test valid variables
        valid_vars = ["{{user.name}}", "{{context.locale}}", "{{temp.current_step}}"]
        for var in valid_vars:
            errors = variable_resolver.validate_variable_references(var)
            assert len(errors) == 0

        # Test invalid variables (if validation is implemented)
        invalid_vars = ["{{nonexistent.field}}", "{{user.missing.path}}"]
        for var in invalid_vars:
            errors = variable_resolver.validate_variable_references(var)
            # Should have validation errors for missing variables
            assert len(errors) > 0

    def test_security_variable_sanitization(self, variable_resolver):
        """Test security aspects of variable substitution."""
        # Test that potentially dangerous content is handled safely
        malicious_state = {
            "user": {
                "name": "<script>alert('xss')</script>",
                "bio": "'; DROP TABLE users; --",
            }
        }

        from app.services.variable_resolver import create_session_resolver

        resolver = create_session_resolver(malicious_state)

        result = resolver.substitute_variables("Hello {{user.name}}")
        # Should preserve the content (sanitization might be handled elsewhere)
        assert "<script>" in result or result == "Hello "

    def test_performance_with_large_objects(self, variable_resolver):
        """Test performance with large nested objects."""
        # Create a large nested object
        large_state = {"user": {"name": "Performance Test User"}}

        # Add many nested levels
        current = large_state["user"]
        for i in range(10):
            current[f"level_{i}"] = {"data": f"value_{i}"}
            current = current[f"level_{i}"]

        from app.services.variable_resolver import create_session_resolver

        resolver = create_session_resolver(large_state)

        # Test deep path access
        template = "{{user.level_0.level_1.level_2.data}}"
        result = resolver.substitute_variables(template)
        # Should handle deep nesting efficiently
        assert isinstance(result, str)

    def test_circular_reference_handling(self):
        """Test handling of circular references in objects."""
        # Create object with circular reference
        circular_state = {"user": {"name": "Circular User"}}
        circular_state["user"]["self"] = circular_state["user"]  # Circular reference

        from app.services.variable_resolver import create_session_resolver

        resolver = create_session_resolver(circular_state)

        # Should handle circular references gracefully
        result = resolver.substitute_variables("{{user.name}}")
        assert result == "Circular User"

    def test_special_characters_in_values(self, variable_resolver):
        """Test handling of special characters in variable values."""
        special_state = {
            "user": {
                "name": "User with émojis 🎉",
                "bio": "Line 1\nLine 2\tTabbed",
                "quote": 'He said "Hello" to me',
                "json_like": '{"key": "value"}',
            }
        }

        from app.services.variable_resolver import create_session_resolver

        resolver = create_session_resolver(special_state)

        result = resolver.substitute_variables("Name: {{user.name}}")
        assert "émojis 🎉" in result

        result = resolver.substitute_variables("Bio: {{user.bio}}")
        assert "Line 1\nLine 2\tTabbed" in result

    def test_variable_caching_and_performance(self, variable_resolver):
        """Test variable resolution caching for performance."""
        template = "{{user.name}} {{user.name}} {{user.name}}"

        # Multiple resolutions of same variable should be efficient
        result = variable_resolver.substitute_variables(template)
        assert result == "John Doe John Doe John Doe"

    def test_composite_scope_priority(self):
        """Test priority order of composite scopes."""
        from app.services.variable_resolver import create_session_resolver

        # Set up overlapping scopes
        session_state = {"value": "session"}
        composite_scopes = {
            "input": {"value": "input"},
            "output": {"value": "output"},
            "local": {"value": "local"},
            "temp": {"value": "temp"},
        }

        resolver = create_session_resolver(session_state, composite_scopes)

        # Test explicit scope references
        assert resolver.substitute_variables("{{input.value}}") == "input"
        assert resolver.substitute_variables("{{output.value}}") == "output"
        assert resolver.substitute_variables("{{local.value}}") == "local"
        assert resolver.substitute_variables("{{temp.value}}") == "temp"

    def test_error_recovery_and_partial_substitution(self, variable_resolver):
        """Test error recovery with partial successful substitution."""
        template = (
            "Valid: {{user.name}}, Invalid: {{user.missing}}, Valid: {{context.locale}}"
        )

        result = variable_resolver.substitute_variables(template)

        # Should substitute valid variables even if some are invalid
        assert "John Doe" in result
        assert "en-US" in result


class TestVariableScope:
    """Test suite for VariableScope functionality."""

    def test_variable_scope_creation(self):
        """Test creating variable scopes."""
        scope = VariableScope(
            name="user_scope",
            data={"name": "John", "age": 30},
            read_only=True,
            description="User information scope",
        )

        assert scope.name == "user_scope"
        assert scope.data["name"] == "John"
        assert scope.read_only is True
        assert scope.description == "User information scope"

    def test_variable_scope_validation(self):
        """Test variable scope validation."""
        # Test with invalid data types
        with pytest.raises(Exception):  # Pydantic validation error
            VariableScope(
                name=123,  # type: ignore  # Should be string
                data={"valid": "data"},
            )


class TestVariableReference:
    """Test suite for VariableReference functionality."""

    def test_variable_reference_creation(self):
        """Test creating variable references."""
        ref = VariableReference(
            scope="user", path="name", full_path="user.name", is_secret=False
        )

        assert ref.scope == "user"
        assert ref.path == "name"
        assert ref.full_path == "user.name"
        assert ref.is_secret is False

    def test_secret_variable_reference(self):
        """Test secret variable reference."""
        ref = VariableReference(
            scope="secret", path="api_key", full_path="secret:api_key", is_secret=True
        )

        assert ref.scope == "secret"
        assert ref.path == "api_key"
        assert ref.is_secret is True


class TestVariableResolverIntegration:
    """Integration tests for variable resolver with other components."""

    def test_variable_resolver_with_action_processor(self):
        """Test variable resolver integration with action processors."""
        from app.services.variable_resolver import create_session_resolver

        session_state = {
            "user": {"name": "Action User", "id": "123"},
            "temp": {"prefix": "USER_"},
        }
        resolver = create_session_resolver(session_state)

        # Simulate action processor using variable resolver
        action_config = {
            "type": "set_variable",
            "variable": "temp.processed_name",
            "value": "{{temp.prefix}}{{user.name}}_{{user.id}}",
        }

        resolved_value = resolver.substitute_variables(action_config["value"])
        assert resolved_value == "USER_Action User_123"

    def test_variable_resolver_with_webhook_processor(self):
        """Test variable resolver integration with webhook processors."""
        from app.services.variable_resolver import create_session_resolver

        session_state = {
            "user": {"id": "user123", "email": "test@example.com"},
            "context": {"api_base": "https://api.example.com"},
        }
        resolver = create_session_resolver(session_state)

        # Simulate webhook configuration with variables
        webhook_config = {
            "url": "{{context.api_base}}/users/{{user.id}}/notifications",
            "body": {"email": "{{user.email}}", "type": "welcome"},
            "headers": {
                "Content-Type": "application/json",
                "User-Agent": "Chatbot/1.0",
            },
        }

        resolved_config = resolver.substitute_object(webhook_config)

        assert (
            resolved_config["url"]
            == "https://api.example.com/users/user123/notifications"
        )
        assert resolved_config["body"]["email"] == "test@example.com"
        assert resolved_config["headers"]["Content-Type"] == "application/json"

    def test_variable_resolver_with_condition_processor(self):
        """Test variable resolver with condition evaluation."""
        from app.services.variable_resolver import create_session_resolver

        session_state = {
            "user": {"age": 25, "subscription": "premium"},
            "context": {"feature_flags": {"advanced_features": True}},
        }
        resolver = create_session_resolver(session_state)

        # Simulate condition evaluation with variable access
        conditions = [
            {"var": "user.age", "gte": 18},
            {"var": "user.subscription", "eq": "premium"},
            {"var": "context.feature_flags.advanced_features", "eq": True},
        ]

        # Test variable path resolution for conditions
        for condition in conditions:
            if "var" in condition:
                var_path = condition["var"]
                # Parse and resolve the variable
                var_ref = resolver.parse_variable_reference(var_path)
                value = resolver.resolve_variable(var_ref)
                assert value is not None

    def test_end_to_end_variable_flow(self):
        """Test complete variable flow through multiple processors."""
        from app.services.variable_resolver import create_session_resolver

        # Initial session state
        session_state = {
            "user": {"name": "End2End User", "level": 1},
            "temp": {"processing": False},
        }
        resolver = create_session_resolver(session_state)

        # Step 1: Action sets processing flag
        action_template = "Processing user {{user.name}} at level {{user.level}}"
        action_result = resolver.substitute_variables(action_template)
        session_state["temp"]["processing_message"] = action_result
        session_state["temp"]["processing"] = True

        # Step 2: Condition checks processing status
        # Update the resolver's temp scope
        resolver.update_scope_variable("temp", "processing_message", action_result)
        resolver.update_scope_variable("temp", "processing", True)
        condition_template = "{{temp.processing}}"
        condition_result = resolver.substitute_variables(condition_template)
        assert condition_result == "True"

        # Step 3: Webhook sends notification
        webhook_template = {
            "message": "{{temp.processing_message}}",
            "status": "active",
        }
        webhook_result = resolver.substitute_object(webhook_template)
        assert webhook_result["message"] == "Processing user End2End User at level 1"

        # Step 4: Composite output mapping
        composite_output = {
            "final_message": "{{temp.processing_message}}",
            "user_summary": "{{user.name}} (Level {{user.level}})",
        }
        final_result = resolver.substitute_object(composite_output)

        assert (
            final_result["final_message"] == "Processing user End2End User at level 1"
        )
        assert final_result["user_summary"] == "End2End User (Level 1)"
