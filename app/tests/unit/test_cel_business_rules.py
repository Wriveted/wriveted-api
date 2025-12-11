"""
Unit tests for CEL-based business rules validation system.

Tests the flexible, configuration-driven approach to validating business rules
using CEL (Common Expression Language) expressions.
"""

import pytest

from app.models.cms import NodeType
from app.services.cel_business_rules import (
    BusinessRule,
    BusinessRulesEngine,
    validate_business_rules,
)
from app.services.node_input_validation import ValidationSeverity


class TestBusinessRule:
    """Test cases for the BusinessRule dataclass."""

    def test_valid_business_rule_creation(self):
        """Test creating a valid business rule."""
        rule = BusinessRule(
            id="test_rule",
            name="Test Rule",
            description="A test rule",
            expression="node_type == 'message'",
            severity=ValidationSeverity.WARNING,
            message="Test message",
        )

        assert rule.id == "test_rule"
        assert rule.name == "Test Rule"
        assert rule.severity == ValidationSeverity.WARNING

    def test_invalid_cel_expression_raises_error(self):
        """Test that invalid CEL expressions raise ValueError."""
        with pytest.raises(ValueError, match="Invalid CEL expression"):
            BusinessRule(
                id="bad_rule",
                name="Bad Rule",
                description="Rule with invalid CEL",
                expression="invalid CEL syntax $$",  # Invalid CEL
                severity=ValidationSeverity.ERROR,
                message="This should fail",
            )

    def test_business_rule_with_node_types(self):
        """Test business rule with specific node types."""
        rule = BusinessRule(
            id="webhook_rule",
            name="Webhook Rule",
            description="Rule for webhooks only",
            expression="has(content.url)",
            severity=ValidationSeverity.INFO,
            message="URL check",
            node_types=[NodeType.WEBHOOK, NodeType.ACTION],
        )

        assert NodeType.WEBHOOK in rule.node_types
        assert NodeType.MESSAGE not in rule.node_types


class TestBusinessRulesEngine:
    """Test cases for the BusinessRulesEngine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = BusinessRulesEngine()

    def test_engine_loads_default_rules(self):
        """Test that engine loads default rules."""
        assert len(self.engine.rules) > 0

        # Check that some expected default rules are present
        rule_ids = [rule.id for rule in self.engine.rules]
        assert "webhook_no_credentials_in_url" in rule_ids
        assert "question_max_choices" in rule_ids
        assert "action_unsafe_calculation" in rule_ids

    def test_add_custom_rule(self):
        """Test adding a custom business rule."""
        initial_count = len(self.engine.rules)

        custom_rule = BusinessRule(
            id="custom_test_rule",
            name="Custom Test Rule",
            description="A custom rule for testing",
            expression="content_size > 100",
            severity=ValidationSeverity.WARNING,
            message="Content is too long",
        )

        self.engine.add_rule(custom_rule)

        assert len(self.engine.rules) == initial_count + 1
        assert self.engine.get_rule_by_id("custom_test_rule") is not None

    def test_remove_rule(self):
        """Test removing a business rule."""
        # Add a rule first
        test_rule = BusinessRule(
            id="removable_rule",
            name="Removable Rule",
            description="Rule to be removed",
            expression="true",
            severity=ValidationSeverity.INFO,
            message="Will be removed",
        )
        self.engine.add_rule(test_rule)

        # Verify it exists
        assert self.engine.get_rule_by_id("removable_rule") is not None

        # Remove it
        self.engine.remove_rule("removable_rule")

        # Verify it's gone
        assert self.engine.get_rule_by_id("removable_rule") is None

    def test_get_rules_by_node_type(self):
        """Test filtering rules by node type."""
        webhook_rules = self.engine.get_rules_by_node_type(NodeType.WEBHOOK)
        question_rules = self.engine.get_rules_by_node_type(NodeType.QUESTION)

        # Should have different rules for different node types
        assert len(webhook_rules) > 0
        assert len(question_rules) > 0

        # Webhook rules should apply to webhooks
        for rule in webhook_rules:
            assert rule.node_types is None or NodeType.WEBHOOK in rule.node_types

    def test_validate_rule_expression(self):
        """Test CEL expression validation."""
        # Valid expressions
        assert self.engine.validate_rule_expression("true")
        assert self.engine.validate_rule_expression("node_type == 'message'")
        assert self.engine.validate_rule_expression("has(content.url)")

        # Invalid expressions
        assert not self.engine.validate_rule_expression("invalid syntax $$")
        assert not self.engine.validate_rule_expression("")

    def test_test_rule(self):
        """Test running a rule against test context."""
        # Create a simple test rule
        test_rule = BusinessRule(
            id="simple_test",
            name="Simple Test",
            description="Test rule",
            expression="has(content.test_field) && content.test_field == 'expected'",
            severity=ValidationSeverity.INFO,
            message="Test",
        )
        self.engine.add_rule(test_rule)

        # Test contexts
        matching_context = {"content": {"test_field": "expected"}, "node_type": "test"}

        non_matching_context = {
            "content": {"test_field": "different"},
            "node_type": "test",
        }

        # Test the rule
        assert self.engine.test_rule("simple_test", matching_context) is True
        assert self.engine.test_rule("simple_test", non_matching_context) is False

    def test_test_nonexistent_rule(self):
        """Test testing a rule that doesn't exist."""
        with pytest.raises(ValueError, match="Rule not found"):
            self.engine.test_rule("nonexistent_rule", {})


class TestBusinessRulesValidation:
    """Test cases for node validation using business rules."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = BusinessRulesEngine()
        self.node_id = "test_node"

    def test_webhook_credentials_in_url_error(self):
        """Test webhook URL with credentials triggers error."""
        content = {"url": "https://user:password@api.example.com/webhook"}

        results = self.engine.validate_node(self.node_id, NodeType.WEBHOOK, content)

        # Should have an error for credentials in URL
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(errors) > 0
        assert any("credentials" in error.message.lower() for error in errors)

    def test_webhook_localhost_warning(self):
        """Test webhook localhost URL triggers warning."""
        content = {"url": "http://localhost:8080/webhook"}

        results = self.engine.validate_node(self.node_id, NodeType.WEBHOOK, content)

        # Should have a warning for localhost URL
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) > 0
        assert any("localhost" in warning.message.lower() for warning in warnings)

    def test_question_too_many_choices_warning(self):
        """Test question with too many choices triggers warning."""
        content = {
            "question": {"text": "Choose an option"},
            "input_type": "choice",
            "options": [
                {"value": f"option{i}"} for i in range(15)
            ],  # 15 options > 10 limit
        }

        results = self.engine.validate_node(self.node_id, NodeType.QUESTION, content)

        # Should have a warning for too many choices
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) > 0
        assert any("choices" in warning.message.lower() for warning in warnings)

    def test_question_too_few_choices_error(self):
        """Test question with too few choices triggers error."""
        content = {
            "question": {"text": "Choose an option"},
            "input_type": "choice",
            "options": [{"value": "only_one"}],  # Only 1 option < 2 minimum
        }

        results = self.engine.validate_node(self.node_id, NodeType.QUESTION, content)

        # Should have an error for too few choices
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(errors) > 0
        assert any("at least 2" in error.message.lower() for error in errors)

    def test_condition_always_true_warning(self):
        """Test condition with always-true first condition triggers warning."""
        content = {
            "conditions": [
                {"if": True, "then": "always_path"},  # Always true
                {"if": {"var": "temp.test", "eq": "value"}, "then": "never_reached"},
            ]
        }

        results = self.engine.validate_node(self.node_id, NodeType.CONDITION, content)

        # Should have a warning for unreachable conditions
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) > 0
        assert any(
            "always true" in warning.message.lower()
            or "unreachable" in warning.message.lower()
            for warning in warnings
        )

    def test_action_unsafe_calculation_warning(self):
        """Test action with unsafe calculation triggers warning."""
        content = {
            "actions": [
                {
                    "type": "calculate",
                    "params": {
                        "expression": "__import__('os').system('rm -rf /')",  # Unsafe!
                        "result_variable": "temp.result",
                    },
                }
            ]
        }

        results = self.engine.validate_node(self.node_id, NodeType.ACTION, content)

        # Should have a warning for unsafe calculation
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) > 0
        assert any("unsafe" in warning.message.lower() for warning in warnings)

    def test_action_invalid_variable_name_error(self):
        """Test action with invalid variable name triggers error."""
        content = {
            "actions": [
                {
                    "type": "set_variable",
                    "params": {
                        "variable": "123invalid_name",  # Invalid: starts with number
                        "value": "test",
                    },
                }
            ]
        }

        results = self.engine.validate_node(self.node_id, NodeType.ACTION, content)

        # Should have an error for invalid variable name
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(errors) > 0
        assert any("variable name" in error.message.lower() for error in errors)

    def test_webhook_timeout_warning(self):
        """Test webhook with unreasonable timeout triggers warning."""
        content = {
            "url": "https://api.example.com/webhook",
            "timeout": 300,  # 5 minutes - too long
        }

        results = self.engine.validate_node(self.node_id, NodeType.WEBHOOK, content)

        # Should have a warning for long timeout
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) > 0
        assert any("timeout" in warning.message.lower() for warning in warnings)

    def test_message_empty_content_warning(self):
        """Test message with no messages triggers warning."""
        content = {
            "messages": []  # No messages configured
        }

        results = self.engine.validate_node(self.node_id, NodeType.MESSAGE, content)

        # Should have a warning for no messages
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) > 0
        assert any("no messages" in warning.message.lower() for warning in warnings)

    def test_no_violations_for_good_content(self):
        """Test that good content produces no violations."""
        content = {"messages": [{"content": "Hello! This is a meaningful message."}]}

        results = self.engine.validate_node(self.node_id, NodeType.MESSAGE, content)

        # Should have no errors or warnings for good content
        violations = [
            r
            for r in results
            if r.severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING]
        ]
        assert len(violations) == 0

    def test_node_type_filtering(self):
        """Test that rules are only applied to appropriate node types."""
        # Webhook-specific content applied to a message node
        content = {
            "url": "http://localhost/webhook"  # Would trigger webhook warnings
        }

        results = self.engine.validate_node(self.node_id, NodeType.MESSAGE, content)

        # Should not trigger webhook-specific warnings on a message node
        webhook_warnings = [r for r in results if "webhook" in r.message.lower()]
        assert len(webhook_warnings) == 0


class TestConvenienceFunction:
    """Test the convenience function."""

    def test_validate_business_rules_function(self):
        """Test the validate_business_rules convenience function."""
        content = {
            "url": "https://user:pass@api.example.com/hook"  # Should trigger error
        }

        results = validate_business_rules("test", NodeType.WEBHOOK, content)

        assert len(results) > 0
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(errors) > 0
