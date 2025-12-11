"""Unit tests for PII masking service."""

import pytest

from app.services.pii_masker import PIIMasker, mask_state


class TestPIIMasker:
    """Test PII masking functionality."""

    @pytest.fixture
    def masker(self):
        """Create a fresh PII masker instance."""
        return PIIMasker()

    def test_mask_email_by_key(self, masker):
        """Test that email fields are masked based on key name."""
        state = {"user_email": "john@example.com", "name": "John"}
        result = masker.mask_state(state)

        assert "[MASKED:" in result["user_email"]
        assert "john@example.com" not in result["user_email"]
        assert result["name"] == "John"

    def test_mask_email_by_pattern(self, masker):
        """Test that email patterns in values are detected and masked."""
        state = {"message": "Contact me at john@example.com for details"}
        result = masker.mask_state(state)

        assert "[EMAIL]" in result["message"]
        assert "john@example.com" not in result["message"]
        assert "Contact me at" in result["message"]

    def test_mask_phone_by_key(self, masker):
        """Test that phone fields are masked based on key name."""
        state = {"phone_number": "+1-555-123-4567"}
        result = masker.mask_state(state)

        assert "[MASKED:" in result["phone_number"]
        assert "+1-555-123-4567" not in result["phone_number"]

    def test_mask_phone_by_pattern(self, masker):
        """Test that phone patterns in values are detected and masked."""
        state = {"info": "Call me at +64 21 123 4567 anytime"}
        result = masker.mask_state(state)

        assert "[PHONE]" in result["info"]
        assert "+64 21 123 4567" not in result["info"]

    def test_mask_sensitive_keys(self, masker):
        """Test that various sensitive key patterns are masked."""
        state = {
            "password": "secret123",
            "api_key": "sk_live_abc123",
            "auth_token": "jwt.token.here",
            "parent_email": "parent@school.edu",
            "student_name": "Jane Doe",
            "date_of_birth": "2015-03-20",
            "ssn": "123-45-6789",
            "credit_card": "4111111111111111",
        }
        result = masker.mask_state(state)

        for key, original_value in state.items():
            assert "[MASKED:" in result[key], f"Expected {key} to be masked"
            assert original_value not in result[key]

    def test_mask_nested_dict(self, masker):
        """Test that nested dictionaries are recursively masked."""
        state = {
            "user": {
                "profile": {
                    "email": "user@test.com",
                    "address": "123 Main St",
                }
            }
        }
        result = masker.mask_state(state)

        assert "[MASKED:" in result["user"]["profile"]["email"]
        assert "[MASKED:" in result["user"]["profile"]["address"]

    def test_mask_list_items(self, masker):
        """Test that list items containing PII are masked."""
        state = {
            # "emails" key triggers key-based masking (contains "email")
            "emails": ["john@test.com", "jane@test.com"],
            # List without sensitive key uses pattern detection
            "texts": ["Contact me at john@test.com please"],
            "messages": [
                {"text": "Hello", "from_email": "sender@test.com"},
            ],
        }
        result = masker.mask_state(state)

        # Key "emails" triggers key-based masking - entire values masked
        for email in result["emails"]:
            assert "[MASKED:" in email
            assert "@test.com" not in email

        # Pattern detection in non-sensitive key list
        assert "[EMAIL]" in result["texts"][0]

        # Nested dict in list
        assert "[MASKED:" in result["messages"][0]["from_email"]

    def test_mask_ip_address_by_pattern(self, masker):
        """Test that IP addresses are detected and masked."""
        state = {"log": "Request from 192.168.1.100 at 10:30"}
        result = masker.mask_state(state)

        assert "[IP]" in result["log"]
        assert "192.168.1.100" not in result["log"]

    def test_preserve_non_sensitive_data(self, masker):
        """Test that non-sensitive data is preserved unchanged."""
        state = {
            "count": 42,
            "enabled": True,
            "score": 3.14,
            "items": ["apple", "banana"],
            "metadata": {"version": "1.0", "status": "active"},
        }
        result = masker.mask_state(state)

        assert result["count"] == 42
        assert result["enabled"] is True
        assert result["score"] == 3.14
        assert result["items"] == ["apple", "banana"]
        assert result["metadata"]["version"] == "1.0"
        assert result["metadata"]["status"] == "active"

    def test_empty_state(self, masker):
        """Test handling of empty state."""
        assert masker.mask_state({}) == {}
        assert masker.mask_state(None) == {}

    def test_mask_url_credentials(self, masker):
        """Test masking of credentials in URLs."""
        url = "https://admin:password123@api.example.com/endpoint"
        result = masker.mask_url_credentials(url)

        assert "[USER]:[PASS]@" in result
        assert "admin" not in result
        assert "password123" not in result
        assert "api.example.com" in result

    def test_mask_url_no_credentials(self, masker):
        """Test that URLs without credentials are unchanged."""
        url = "https://api.example.com/endpoint"
        result = masker.mask_url_credentials(url)

        assert result == url

    def test_mask_headers(self, masker):
        """Test masking of sensitive HTTP headers."""
        headers = {
            "Authorization": "Bearer token123",
            "Content-Type": "application/json",
            "X-Api-Key": "secret_key",
            "Cookie": "session=abc123",
            "User-Agent": "Mozilla/5.0",
        }
        result = masker.mask_headers(headers)

        assert result["Authorization"] == "[REDACTED]"
        assert result["X-Api-Key"] == "[REDACTED]"
        assert result["Cookie"] == "[REDACTED]"
        assert result["Content-Type"] == "application/json"
        assert result["User-Agent"] == "Mozilla/5.0"

    def test_deterministic_masking(self, masker):
        """Test that same input produces same masked output."""
        state = {"email": "test@example.com"}

        result1 = masker.mask_state(state)
        result2 = masker.mask_state(state)

        assert result1["email"] == result2["email"]

    def test_preserve_length_option(self):
        """Test preserve_length option for masking."""
        masker = PIIMasker(preserve_length=True)
        state = {"email": "test@example.com"}
        result = masker.mask_state(state)

        # Masked value should be same length as original
        assert len(result["email"]) == len("test@example.com")
        assert all(c == "*" for c in result["email"])


class TestModuleFunctions:
    """Test module-level convenience functions."""

    def test_mask_state_function(self):
        """Test the module-level mask_state function."""
        state = {"email": "test@example.com", "count": 5}
        result = mask_state(state)

        assert "[MASKED:" in result["email"]
        assert result["count"] == 5
