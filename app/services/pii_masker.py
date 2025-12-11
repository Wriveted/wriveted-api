"""PII (Personally Identifiable Information) masking service.

Masks sensitive data in trace state snapshots to prevent storage of
personally identifiable information while preserving debugging utility.
"""

import hashlib
import re
from typing import Any, Dict, Set


class PIIMasker:
    """Mask personally identifiable information in trace data."""

    # Keys that should always be masked (case-insensitive substring match)
    SENSITIVE_KEYS: Set[str] = {
        "email",
        "phone",
        "telephone",
        "mobile",
        "address",
        "street",
        "postcode",
        "zipcode",
        "zip_code",
        "postal_code",
        "ssn",
        "social_security",
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
        "auth",
        "credential",
        "parent_name",
        "parent_email",
        "guardian",
        "student_name",
        "child_name",
        "full_name",
        "first_name",
        "last_name",
        "surname",
        "given_name",
        "family_name",
        "date_of_birth",
        "dob",
        "birthday",
        "birth_date",
        "credit_card",
        "card_number",
        "cvv",
        "account_number",
        "routing_number",
        "bank_account",
        "ip_address",
        "user_agent",
    }

    # Regex patterns to detect and mask
    EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    PHONE_PATTERN = re.compile(r"\+?[\d\s\-\(\)]{10,}")
    # IP addresses (both v4 and simple v6)
    IP_PATTERN = re.compile(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b|" r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
    )

    def __init__(self, mask_char: str = "*", preserve_length: bool = False):
        """Initialize the PII masker.

        Args:
            mask_char: Character to use for masking (default: *)
            preserve_length: If True, mask with same length as original.
                           If False, use hash-based placeholder (default: False)
        """
        self.mask_char = mask_char
        self.preserve_length = preserve_length

    def mask_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively mask PII in state dictionary.

        Args:
            state: Session state dictionary to mask

        Returns:
            New dictionary with PII masked
        """
        if not state:
            return {}
        return self._mask_recursive(state)

    def _mask_recursive(self, obj: Any, parent_key: str = "") -> Any:
        """Recursively process object and mask sensitive data."""
        if isinstance(obj, dict):
            return {key: self._mask_recursive(value, key) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._mask_recursive(item, parent_key) for item in obj]
        elif isinstance(obj, str):
            return self._mask_string(obj, parent_key)
        # Pass through other types unchanged (int, float, bool, None)
        return obj

    def _mask_string(self, value: str, key: str) -> str:
        """Mask a string value if it appears to contain PII.

        Args:
            value: String value to check
            key: The key/field name this value is associated with

        Returns:
            Original value or masked version
        """
        # Check if key indicates sensitive data
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in self.SENSITIVE_KEYS):
            return self._mask_value(value, f"key:{key}")

        # Check for patterns in value
        masked = value

        # Replace emails
        if self.EMAIL_PATTERN.search(masked):
            masked = self.EMAIL_PATTERN.sub("[EMAIL]", masked)

        # Replace phone numbers
        if self.PHONE_PATTERN.search(masked):
            masked = self.PHONE_PATTERN.sub("[PHONE]", masked)

        # Replace IP addresses
        if self.IP_PATTERN.search(masked):
            masked = self.IP_PATTERN.sub("[IP]", masked)

        return masked

    def _mask_value(self, value: str, context: str = "") -> str:
        """Create a masked version of a value.

        Args:
            value: Value to mask
            context: Context string for hash-based masking

        Returns:
            Masked value
        """
        if not value:
            return value

        if self.preserve_length:
            return self.mask_char * len(value)

        # Create deterministic hash for correlation
        # (same value always produces same hash)
        hash_input = f"{context}:{value}" if context else value
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
        return f"[MASKED:{hash_value}]"

    def mask_url_credentials(self, url: str) -> str:
        """Mask credentials in URLs (user:pass@host).

        Args:
            url: URL that may contain credentials

        Returns:
            URL with credentials masked
        """
        # Pattern: protocol://user:password@host
        cred_pattern = re.compile(r"(https?://)([^:]+):([^@]+)@")
        return cred_pattern.sub(r"\1[USER]:[PASS]@", url)

    def mask_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Mask sensitive HTTP headers.

        Args:
            headers: HTTP headers dictionary

        Returns:
            Headers with sensitive values masked
        """
        sensitive_headers = {
            "authorization",
            "x-api-key",
            "x-auth-token",
            "cookie",
            "set-cookie",
            "proxy-authorization",
        }

        masked = {}
        for key, value in headers.items():
            if key.lower() in sensitive_headers:
                masked[key] = "[REDACTED]"
            else:
                masked[key] = value
        return masked


# Module-level instance for convenience
pii_masker = PIIMasker()


def mask_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to mask PII in state."""
    return pii_masker.mask_state(state)
