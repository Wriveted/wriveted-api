"""
CEL-based Business Rules Validation System.

This module provides a flexible, configuration-driven approach to validating business rules
using CEL (Common Expression Language) expressions. Rules can be easily modified without
code changes and support complex validation logic.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from structlog import get_logger

from app.models.cms import NodeType
from app.services.cel_evaluator import evaluate_cel_expression, validate_cel_expression
from app.services.node_input_validation import ValidationResult, ValidationSeverity

logger = get_logger()


@dataclass
class BusinessRule:
    """
    A business rule that uses CEL expressions for validation.
    """

    id: str
    name: str
    description: str
    expression: str  # CEL expression that should evaluate to boolean
    severity: ValidationSeverity
    message: str
    suggested_fix: Optional[str] = None
    node_types: Optional[List[NodeType]] = None  # If None, applies to all node types

    def __post_init__(self):
        """Validate the CEL expression on creation."""
        # Test with a comprehensive sample context to validate syntax
        test_context = {
            "node_type": "test",
            "content": {
                "url": "https://example.com",
                "actions": [
                    {
                        "type": "calculate",
                        "params": {"expression": "2 + 2", "variable": "temp.result"},
                    }
                ],
                "messages": [{"content": "test message"}],
                "conditions": [{"if": False, "then": "path1"}],
                "options": [{"value": "option1"}, {"value": "option2"}],
                "headers": {"Authorization": "Bearer token"},
                "timeout": 30,
                "input_type": "choice",
                "question": {"text": "Test question"},
            },
            "node_id": "test_node_id",
            "content_size": 100,
        }

        try:
            from app.services.cel_evaluator import evaluate_cel_expression

            # Try to evaluate - if it doesn't throw an exception, syntax is valid
            evaluate_cel_expression(self.expression, test_context)
        except Exception as e:
            raise ValueError(
                f"Invalid CEL expression in rule '{self.id}': {self.expression}. Error: {str(e)}"
            )


class BusinessRulesEngine:
    """
    CEL-based business rules validation engine.

    This engine evaluates configurable CEL expressions against node content
    to identify business rule violations, security issues, and best practice concerns.
    """

    def __init__(self):
        self.logger = logger
        self.rules = self._load_default_rules()

    def _load_default_rules(self) -> List[BusinessRule]:
        """Load default business rules for node validation."""
        return [
            # Security Rules
            BusinessRule(
                id="webhook_no_credentials_in_url",
                name="Webhook URL Security",
                description="Webhook URLs should not contain embedded credentials",
                expression='node_type == "webhook" && has(content.url) && content.url.contains("@") && content.url.contains("://")',
                severity=ValidationSeverity.ERROR,
                message="Webhook URL contains embedded credentials",
                suggested_fix="Use headers for authentication instead of URL credentials",
                node_types=[NodeType.WEBHOOK],
            ),
            BusinessRule(
                id="webhook_no_localhost",
                name="Webhook External URLs",
                description="Webhook URLs should not point to internal/localhost addresses",
                expression="""
                node_type == "webhook" && has(content.url) && (
                    content.url.contains("localhost") ||
                    content.url.contains("127.0.0.1") ||
                    content.url.contains("internal") ||
                    content.url.contains("local") ||
                    content.url.contains("LOCALHOST") ||
                    content.url.contains("LOCAL") ||
                    content.url.contains("INTERNAL")
                )
                """,
                severity=ValidationSeverity.WARNING,
                message="Webhook URL points to internal/localhost address",
                suggested_fix="Use external URLs for webhook endpoints",
                node_types=[NodeType.WEBHOOK],
            ),
            # Accessibility Rules
            BusinessRule(
                id="question_max_choices",
                name="Question Choice Limit",
                description="Questions should not have too many choices for usability",
                expression="""
                node_type == "question" && 
                has(content.input_type) && content.input_type == "choice" &&
                has(content.options) && size(content.options) > 10
                """,
                severity=ValidationSeverity.WARNING,
                message="Question has more than 10 choices, may be difficult for users",
                suggested_fix="Consider reducing number of choices or using text input with validation",
                node_types=[NodeType.QUESTION],
            ),
            BusinessRule(
                id="question_min_choices",
                name="Question Choice Minimum",
                description="Choice questions must have at least 2 options",
                expression="""
                node_type == "question" && 
                has(content.input_type) && content.input_type == "choice" &&
                (!has(content.options) || size(content.options) < 2)
                """,
                severity=ValidationSeverity.ERROR,
                message="Choice questions must have at least 2 options",
                suggested_fix="Add more choice options or change input type to text",
                node_types=[NodeType.QUESTION],
            ),
            # Logic Rules
            BusinessRule(
                id="condition_always_true_unreachable",
                name="Unreachable Conditions",
                description="Check for conditions that may be unreachable due to always-true predecessors",
                expression="""
                node_type == "condition" &&
                has(content.conditions) && size(content.conditions) > 1 &&
                (content.conditions[0].if == true || content.conditions[0].if == "true" || content.conditions[0].if == 1)
                """,
                severity=ValidationSeverity.WARNING,
                message="First condition is always true, subsequent conditions may be unreachable",
                suggested_fix="Review condition order and logic",
                node_types=[NodeType.CONDITION],
            ),
            # Action Safety Rules
            BusinessRule(
                id="action_unsafe_calculation",
                name="Unsafe Calculation Detection",
                description="Detect potentially unsafe calculation expressions",
                expression="""
                node_type == "action" && has(content.actions) &&
                size(content.actions) > 0 &&
                content.actions[0].type == "calculate" && 
                has(content.actions[0].params.expression) &&
                (content.actions[0].params.expression.contains("__") ||
                 content.actions[0].params.expression.contains("import") ||
                 content.actions[0].params.expression.contains("exec") ||
                 content.actions[0].params.expression.contains("eval") ||
                 content.actions[0].params.expression.contains("open") ||
                 content.actions[0].params.expression.contains("subprocess"))
                """,
                severity=ValidationSeverity.WARNING,
                message="Action contains potentially unsafe calculation expression",
                suggested_fix="Use safe mathematical operations only",
                node_types=[NodeType.ACTION],
            ),
            # Performance Rules
            BusinessRule(
                id="webhook_reasonable_timeout",
                name="Webhook Timeout Bounds",
                description="Webhook timeouts should be reasonable for user experience",
                expression="""
                node_type == "webhook" && 
                has(content.timeout) && 
                (content.timeout > 120 || content.timeout < 1)
                """,
                severity=ValidationSeverity.WARNING,
                message="Webhook timeout should be between 1-120 seconds for good UX",
                suggested_fix="Consider shorter timeout for better user experience",
                node_types=[NodeType.WEBHOOK],
            ),
            # Content Quality Rules
            BusinessRule(
                id="message_empty_content",
                name="Message Content Quality",
                description="Message nodes should have meaningful content",
                expression="""
                node_type == "message" &&
                has(content.messages) &&
                size(content.messages) == 0
                """,
                severity=ValidationSeverity.WARNING,
                message="Message node has no messages configured",
                suggested_fix="Add at least one message to the node",
                node_types=[NodeType.MESSAGE],
            ),
            # Variable Safety Rules
            BusinessRule(
                id="action_variable_naming",
                name="Variable Naming Convention",
                description="Variables should follow naming conventions",
                expression="""
                node_type == "action" && has(content.actions) &&
                size(content.actions) > 0 &&
                has(content.actions[0].params.variable) &&
                !matches(content.actions[0].params.variable, "^[a-zA-Z_][a-zA-Z0-9_.]*$")
                """,
                severity=ValidationSeverity.ERROR,
                message="Variable names must start with letter/underscore and contain only alphanumeric characters, dots, and underscores",
                suggested_fix="Use valid variable names like 'temp.user_input' or 'local.counter'",
                node_types=[NodeType.ACTION],
            ),
            # Webhook Security Headers
            BusinessRule(
                id="webhook_secure_headers",
                name="Webhook Security Headers",
                description="Webhooks should use secure authentication headers",
                expression="""
                node_type == "webhook" &&
                has(content.headers) &&
                !has(content.headers.Authorization) &&
                !has(content.headers.authorization) &&
                size(content.headers) == 0
                """,
                severity=ValidationSeverity.INFO,
                message="Consider adding authentication headers for webhook security",
                suggested_fix="Add Authorization, X-API-Key, or X-Auth-Token header",
                node_types=[NodeType.WEBHOOK],
            ),
        ]

    def add_rule(self, rule: BusinessRule):
        """Add a custom business rule."""
        self.rules.append(rule)
        self.logger.info("Added business rule", rule_id=rule.id, rule_name=rule.name)

    def remove_rule(self, rule_id: str):
        """Remove a business rule by ID."""
        self.rules = [r for r in self.rules if r.id != rule_id]
        self.logger.info("Removed business rule", rule_id=rule_id)

    def validate_node(
        self, node_id: str, node_type: NodeType, node_content: Dict[str, Any]
    ) -> List[ValidationResult]:
        """
        Validate a node against all applicable business rules.

        Args:
            node_id: Unique identifier for the node
            node_type: Type of the node
            node_content: Node content dictionary

        Returns:
            List of validation results
        """
        results = []

        # Build context for CEL evaluation
        context = {
            "node_id": node_id,
            "node_type": node_type.value,
            "content": node_content,
            "content_size": len(str(node_content)),
            # Helper functions
            "has_field": lambda obj, field: field in obj
            if isinstance(obj, dict)
            else False,
            "trim": lambda s: s.strip() if isinstance(s, str) else str(s).strip(),
        }

        # Apply rules that match this node type
        applicable_rules = [
            rule
            for rule in self.rules
            if rule.node_types is None or node_type in rule.node_types
        ]

        self.logger.debug(
            "Evaluating business rules",
            node_id=node_id,
            node_type=node_type.value,
            rule_count=len(applicable_rules),
        )

        for rule in applicable_rules:
            try:
                # Evaluate the CEL expression
                violation = evaluate_cel_expression(rule.expression, context)

                if violation:
                    result = ValidationResult(
                        is_valid=(rule.severity != ValidationSeverity.ERROR),
                        severity=rule.severity,
                        message=f"{rule.name}: {rule.message}",
                        field_path=None,  # CEL rules operate on entire node content
                        suggested_fix=rule.suggested_fix,
                    )
                    results.append(result)

                    self.logger.debug(
                        "Business rule violation detected",
                        rule_id=rule.id,
                        rule_name=rule.name,
                        node_id=node_id,
                        severity=rule.severity.value,
                    )

            except Exception as e:
                self.logger.error(
                    "Business rule evaluation failed",
                    rule_id=rule.id,
                    rule_name=rule.name,
                    node_id=node_id,
                    error=str(e),
                )

                # Add error as warning - rule evaluation shouldn't break validation
                result = ValidationResult(
                    is_valid=True,  # Don't fail validation due to rule errors
                    severity=ValidationSeverity.WARNING,
                    message=f"Business rule '{rule.name}' evaluation failed: {str(e)}",
                    suggested_fix="Check business rule configuration",
                )
                results.append(result)

        self.logger.debug(
            "Business rules validation completed",
            node_id=node_id,
            violations=len([r for r in results if not r.is_valid]),
        )

        return results

    def get_rules_by_node_type(self, node_type: NodeType) -> List[BusinessRule]:
        """Get all business rules that apply to a specific node type."""
        return [
            rule
            for rule in self.rules
            if rule.node_types is None or node_type in rule.node_types
        ]

    def get_rule_by_id(self, rule_id: str) -> Optional[BusinessRule]:
        """Get a business rule by its ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None

    def validate_rule_expression(self, expression: str) -> bool:
        """Validate that a CEL expression is syntactically correct."""
        return validate_cel_expression(expression)

    def test_rule(self, rule_id: str, test_context: Dict[str, Any]) -> Any:
        """Test a business rule against a sample context."""
        rule = self.get_rule_by_id(rule_id)
        if not rule:
            raise ValueError(f"Rule not found: {rule_id}")

        try:
            return evaluate_cel_expression(rule.expression, test_context)
        except Exception as e:
            self.logger.error("Rule test failed", rule_id=rule_id, error=str(e))
            raise


# Global instance for use throughout the application
business_rules_engine = BusinessRulesEngine()


def validate_business_rules(
    node_id: str, node_type: NodeType, node_content: Dict[str, Any]
) -> List[ValidationResult]:
    """
    Convenience function to validate business rules for a node.

    Args:
        node_id: Unique identifier for the node
        node_type: Type of the node
        node_content: Node content dictionary

    Returns:
        List of validation results
    """
    return business_rules_engine.validate_node(node_id, node_type, node_content)
