"""Unit tests for XSS protection in CMS schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.cms import ContentCreate


class TestXSSProtection:
    """Test XSS protection using bleach library."""

    def test_safe_content_passes(self):
        """Test that safe content passes validation."""
        safe_content_cases = [
            {"text": "Plain text content"},
            {"text": "<p>Safe <strong>HTML</strong></p>"},
            {"text": '<a href="https://example.com">Safe link</a>'},
            {"setup": "Safe joke setup", "punchline": "Safe punchline"},
        ]

        for content in safe_content_cases:
            # Should not raise ValidationError
            content_obj = ContentCreate(
                type="joke", content=content, tags=["test"], status="draft"
            )
            assert content_obj.content == content

    def test_dangerous_content_rejected(self):
        """Test that dangerous XSS content is rejected."""
        dangerous_content_cases = [
            {"text": "<script>alert('xss')</script>"},
            {"text": '<iframe src="javascript:alert(1)"></iframe>'},
            {"text": '<div onclick="alert(1)">Click</div>'},
            {"text": '<a href="javascript:alert(1)">Click</a>'},
            {"setup": "Safe", "punchline": "<script>alert('xss')</script>"},
            {"text": '<img src="x" onerror="alert(1)">'},
        ]

        for content in dangerous_content_cases:
            with pytest.raises(ValidationError) as exc_info:
                ContentCreate(
                    type="joke", content=content, tags=["test"], status="draft"
                )

            # Verify the error message mentions dangerous HTML
            error_message = str(exc_info.value)
            assert "dangerous HTML" in error_message

    def test_mixed_content_rejected(self):
        """Test that content mixing safe and unsafe elements is rejected."""
        mixed_content = {"text": '<p>Safe content</p><script>alert("xss")</script>'}

        with pytest.raises(ValidationError) as exc_info:
            ContentCreate(
                type="joke", content=mixed_content, tags=["test"], status="draft"
            )

        assert "dangerous HTML" in str(exc_info.value)

    def test_nested_content_protection(self):
        """Test that nested content in dictionaries is also protected."""
        nested_dangerous = {"content": {"text": "<script>alert('nested')</script>"}}

        with pytest.raises(ValidationError) as exc_info:
            ContentCreate(
                type="joke", content=nested_dangerous, tags=["test"], status="draft"
            )

        assert "dangerous HTML" in str(exc_info.value)

    def test_list_content_protection(self):
        """Test that content in lists is also protected."""
        list_with_dangerous = {
            "options": ["Safe option", "<script>alert('xss')</script>"]
        }

        with pytest.raises(ValidationError) as exc_info:
            ContentCreate(
                type="question",
                content=list_with_dangerous,
                tags=["test"],
                status="draft",
            )

        assert "dangerous HTML" in str(exc_info.value)

    def test_allowed_html_tags(self):
        """Test that allowed HTML tags pass through correctly."""
        allowed_html = {
            "text": """
            <h1>Heading</h1>
            <p>Paragraph with <strong>bold</strong> and <em>italic</em></p>
            <ul>
                <li>List item 1</li>
                <li>List item 2</li>
            </ul>
            <a href="https://example.com" title="Example">Link</a>
            <blockquote>Quote</blockquote>
            <code>code snippet</code>
            """
        }

        # Should not raise ValidationError
        content_obj = ContentCreate(
            type="message", content=allowed_html, tags=["test"], status="draft"
        )
        assert content_obj.content == allowed_html

    def test_empty_content_rejected(self):
        """Test that empty content is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ContentCreate(type="joke", content={}, tags=["test"], status="draft")

        assert "Content cannot be empty" in str(exc_info.value)
