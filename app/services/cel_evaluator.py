"""CEL (Common Expression Language) evaluator service for safe expression evaluation."""

from typing import Any, Dict

from cel import evaluate
from structlog import get_logger

logger = get_logger()


def evaluate_cel_expression(expression: str, context: Dict[str, Any]) -> Any:
    """
    Safely evaluates a CEL expression against a given data context.
    
    Args:
        expression: CEL expression string to evaluate
        context: Dictionary containing variables for the expression
        
    Returns:
        Result of the expression evaluation
        
    Raises:
        ValueError: If expression is invalid or evaluation fails
        TypeError: If context contains unsupported types
    """
    try:
        # Evaluate using the common-expression-language library
        result = evaluate(expression, context)
        
        logger.debug(
            "CEL expression evaluated successfully",
            expression=expression,
            result=result,
            context_keys=list(context.keys())
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "CEL expression evaluation failed",
            expression=expression,
            error=str(e),
            context_keys=list(context.keys())
        )
        raise ValueError(f"Failed to evaluate expression '{expression}': {str(e)}")


def validate_cel_expression(expression: str) -> bool:
    """
    Validate that a CEL expression is syntactically correct.
    
    Args:
        expression: CEL expression string to validate
        
    Returns:
        True if expression is valid, False otherwise
    """
    try:
        # Try to evaluate with empty context to check syntax
        evaluate(expression, {})
        return True
    except Exception:
        return False


def get_supported_operators() -> Dict[str, str]:
    """
    Get list of supported operators and functions in CEL.
    
    Returns:
        Dictionary mapping operator/function names to descriptions
    """
    return {
        "+": "Addition",
        "-": "Subtraction", 
        "*": "Multiplication",
        "/": "Division",
        "%": "Modulo",
        "==": "Equality",
        "!=": "Inequality",
        "<": "Less than",
        "<=": "Less than or equal",
        ">": "Greater than",
        ">=": "Greater than or equal",
        "&&": "Logical AND",
        "||": "Logical OR",
        "!": "Logical NOT",
        "size": "Get size of string/list/map",
        "int": "Convert to integer",
        "double": "Convert to double",
        "string": "Convert to string",
        "type": "Get type of value",
        "has": "Check if field exists",
        "in": "Check membership in list/map"
    }