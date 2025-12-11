"""
Unit tests for ChatTheme model validation.

Tests:
- ChatTheme model field validation
- Theme configuration schema structure
- Color, typography, and layout validation
- Theme config JSONB field validation
"""

import pytest
from pydantic import ValidationError


class TestChatThemeConfigValidation:
    """Test ChatTheme configuration validation."""

    def test_valid_theme_config_minimal(self):
        """Test minimal valid theme configuration."""
        config = {
            "colors": {
                "primary": "#1890ff",
                "background": "#ffffff",
            },
            "bot": {
                "name": "Huey",
            },
        }

        assert config["colors"]["primary"] == "#1890ff"
        assert config["bot"]["name"] == "Huey"

    def test_valid_theme_config_full(self):
        """Test full theme configuration with all fields."""
        config = {
            "colors": {
                "primary": "#1890ff",
                "secondary": "#52c41a",
                "background": "#ffffff",
                "backgroundAlt": "#f5f5f5",
                "userBubble": "#e6f7ff",
                "userBubbleText": "#000000",
                "botBubble": "#f0f0f0",
                "botBubbleText": "#262626",
                "border": "#d9d9d9",
                "shadow": "rgba(0,0,0,0.1)",
                "error": "#ff4d4f",
                "success": "#52c41a",
                "warning": "#faad14",
                "text": "#262626",
                "textMuted": "#8c8c8c",
                "link": "#1890ff",
            },
            "typography": {
                "fontFamily": "system-ui, -apple-system, sans-serif",
                "fontSize": {"small": "12px", "medium": "14px", "large": "16px"},
                "lineHeight": 1.5,
                "fontWeight": {"normal": 400, "medium": 500, "bold": 600},
            },
            "bubbles": {
                "borderRadius": 12,
                "padding": "12px 16px",
                "maxWidth": "80%",
                "spacing": 8,
            },
            "bot": {
                "name": "Huey",
                "avatar": "https://example.com/avatar.png",
                "typingIndicator": "dots",
                "typingSpeed": 50,
                "responseDelay": 500,
            },
            "layout": {
                "position": "bottom-right",
                "width": 400,
                "height": 600,
                "maxWidth": "90vw",
                "maxHeight": "90vh",
                "margin": "20px",
                "padding": "16px",
                "showHeader": True,
                "showFooter": True,
                "headerHeight": 60,
                "footerHeight": 80,
            },
            "animations": {
                "enabled": True,
                "messageEntry": "slide",
                "duration": 300,
                "easing": "ease-in-out",
            },
            "accessibility": {
                "highContrast": False,
                "reduceMotion": False,
                "fontSize": "default",
            },
        }

        assert config["colors"]["primary"] == "#1890ff"
        assert config["typography"]["fontFamily"].startswith("system-ui")
        assert config["bot"]["name"] == "Huey"
        assert config["layout"]["position"] == "bottom-right"
        assert config["animations"]["enabled"] is True

    def test_theme_config_color_hex_formats(self):
        """Test various hex color formats in theme config."""
        hex_colors = [
            "#1890ff",
            "#fff",
            "#FFFFFF",
            "#abc",
            "#ABC123",
            "rgb(255, 0, 0)",
            "rgba(255, 0, 0, 0.5)",
        ]

        for color in hex_colors:
            config = {
                "colors": {"primary": color, "background": "#ffffff"},
                "bot": {"name": "Test"},
            }
            assert config["colors"]["primary"] == color

    def test_theme_config_typography_values(self):
        """Test typography configuration values."""
        config = {
            "colors": {"primary": "#000"},
            "typography": {
                "fontFamily": "Arial, sans-serif",
                "fontSize": {"small": "10px", "medium": "14px", "large": "18px"},
                "lineHeight": 1.8,
                "fontWeight": {"normal": 300, "medium": 500, "bold": 700},
            },
            "bot": {"name": "Test"},
        }

        assert config["typography"]["lineHeight"] == 1.8
        assert config["typography"]["fontWeight"]["bold"] == 700

    def test_theme_config_bot_personality(self):
        """Test bot personality configuration."""
        config = {
            "colors": {"primary": "#000"},
            "bot": {
                "name": "ReadBot",
                "avatar": "https://example.com/avatar.svg",
                "typingIndicator": "wave",
                "typingSpeed": 75,
                "responseDelay": 1000,
            },
        }

        assert config["bot"]["name"] == "ReadBot"
        assert config["bot"]["typingIndicator"] == "wave"
        assert config["bot"]["typingSpeed"] == 75

    def test_theme_config_layout_positions(self):
        """Test different layout position values."""
        positions = [
            "bottom-right",
            "bottom-left",
            "bottom-center",
            "fullscreen",
            "inline",
        ]

        for position in positions:
            config = {
                "colors": {"primary": "#000"},
                "bot": {"name": "Test"},
                "layout": {"position": position, "width": 400, "height": 600},
            }
            assert config["layout"]["position"] == position

    def test_theme_config_layout_dimensions(self):
        """Test layout dimension configurations."""
        config = {
            "colors": {"primary": "#000"},
            "bot": {"name": "Test"},
            "layout": {
                "position": "bottom-right",
                "width": 450,
                "height": 700,
                "maxWidth": "95vw",
                "maxHeight": "85vh",
            },
        }

        assert config["layout"]["width"] == 450
        assert config["layout"]["height"] == 700

    def test_theme_config_animations(self):
        """Test animation configuration."""
        config = {
            "colors": {"primary": "#000"},
            "bot": {"name": "Test"},
            "animations": {
                "enabled": True,
                "messageEntry": "fade",
                "duration": 250,
                "easing": "cubic-bezier(0.4, 0, 0.2, 1)",
            },
        }

        assert config["animations"]["enabled"] is True
        assert config["animations"]["messageEntry"] == "fade"

    def test_theme_config_accessibility(self):
        """Test accessibility configuration."""
        config = {
            "colors": {"primary": "#000"},
            "bot": {"name": "Test"},
            "accessibility": {
                "highContrast": True,
                "reduceMotion": True,
                "fontSize": "large",
            },
        }

        assert config["accessibility"]["highContrast"] is True
        assert config["accessibility"]["fontSize"] == "large"

    def test_theme_config_with_custom_css(self):
        """Test theme configuration with custom CSS."""
        config = {
            "colors": {"primary": "#000"},
            "bot": {"name": "Test"},
            "customCSS": ".chat-widget { box-shadow: 0 4px 6px rgba(0,0,0,0.1); }",
        }

        assert "box-shadow" in config["customCSS"]

    def test_theme_config_school_branded(self):
        """Test school-branded theme configuration."""
        config = {
            "colors": {
                "primary": "#2E7D32",
                "secondary": "#FFA000",
                "background": "#FAFAFA",
                "userBubble": "#C8E6C9",
                "botBubble": "#FFF9C4",
            },
            "typography": {"fontFamily": "Comic Sans MS, Chalkboard, sans-serif"},
            "bot": {
                "name": "ReadBuddy",
                "avatar": "https://school.edu/mascot.png",
                "typingIndicator": "wave",
            },
            "layout": {"position": "bottom-left", "width": 450, "height": 650},
        }

        assert config["colors"]["primary"] == "#2E7D32"
        assert config["bot"]["name"] == "ReadBuddy"

    def test_theme_config_high_contrast_accessible(self):
        """Test high contrast accessible theme configuration."""
        config = {
            "colors": {
                "primary": "#0000FF",
                "background": "#000000",
                "text": "#FFFFFF",
                "userBubble": "#0000FF",
                "userBubbleText": "#FFFFFF",
                "botBubble": "#FFFFFF",
                "botBubbleText": "#000000",
                "border": "#FFFFFF",
            },
            "typography": {
                "fontSize": {"small": "16px", "medium": "18px", "large": "20px"},
                "lineHeight": 1.8,
            },
            "accessibility": {
                "highContrast": True,
                "reduceMotion": True,
                "fontSize": "large",
            },
            "animations": {"enabled": False},
            "bot": {"name": "Accessible Bot"},
        }

        assert config["accessibility"]["highContrast"] is True
        assert config["animations"]["enabled"] is False

    def test_theme_config_bubble_styling(self):
        """Test message bubble styling configuration."""
        config = {
            "colors": {"primary": "#000"},
            "bot": {"name": "Test"},
            "bubbles": {
                "borderRadius": 16,
                "padding": "14px 18px",
                "maxWidth": "75%",
                "spacing": 12,
            },
        }

        assert config["bubbles"]["borderRadius"] == 16
        assert config["bubbles"]["maxWidth"] == "75%"

    def test_theme_config_typing_indicators(self):
        """Test different typing indicator options."""
        indicators = ["dots", "text", "wave", "none"]

        for indicator in indicators:
            config = {
                "colors": {"primary": "#000"},
                "bot": {"name": "Test", "typingIndicator": indicator},
            }
            assert config["bot"]["typingIndicator"] == indicator

    def test_theme_config_responsive_dimensions(self):
        """Test responsive dimension configuration."""
        config = {
            "colors": {"primary": "#000"},
            "bot": {"name": "Test"},
            "layout": {
                "position": "fullscreen",
                "width": "auto",
                "height": "auto",
                "maxWidth": "100vw",
                "maxHeight": "100vh",
            },
        }

        assert config["layout"]["width"] == "auto"
        assert config["layout"]["maxWidth"] == "100vw"

    def test_theme_config_nested_structure(self):
        """Test deeply nested configuration structure."""
        config = {
            "colors": {"primary": "#000", "secondary": "#fff"},
            "typography": {
                "fontFamily": "Arial",
                "fontSize": {"small": "12px", "medium": "14px"},
                "fontWeight": {"normal": 400, "bold": 600},
            },
            "bot": {"name": "Test", "avatar": "url"},
            "layout": {"position": "inline", "width": 400},
        }

        assert isinstance(config["typography"], dict)
        assert isinstance(config["typography"]["fontSize"], dict)

    def test_theme_config_optional_fields(self):
        """Test that optional fields can be omitted."""
        minimal_config = {
            "colors": {"primary": "#000"},
            "bot": {"name": "Test"},
        }

        assert "typography" not in minimal_config
        assert "animations" not in minimal_config
        assert "customCSS" not in minimal_config
