"""Integration tests for CMS Theme Management API endpoints."""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_global_theme_as_admin(
    async_client_authenticated_as_wriveted_user: AsyncClient,
):
    """Test creating a global theme as admin user."""
    theme_data = {
        "name": "Global Test Theme",
        "description": "A test theme for global use",
        "school_id": None,
        "config": {
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
                "fontFamily": "system-ui, sans-serif",
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
                "avatar": "",
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
                "messageEntry": "fade",
                "duration": 300,
                "easing": "ease-in-out",
            },
            "accessibility": {
                "highContrast": False,
                "reduceMotion": False,
                "fontSize": "default",
            },
        },
        "is_active": True,
        "is_default": False,
        "version": "1.0",
    }

    response = await async_client_authenticated_as_wriveted_user.post(
        "/api/v1/cms/themes", json=theme_data
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == theme_data["name"]
    assert data["description"] == theme_data["description"]
    assert data["school_id"] is None
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "config" in data
    return data["id"]


@pytest.mark.asyncio
async def test_list_themes(
    async_client_authenticated_as_wriveted_user: AsyncClient,
):
    """Test listing themes."""
    response = await async_client_authenticated_as_wriveted_user.get(
        "/api/v1/cms/themes"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_get_theme(
    async_client_authenticated_as_wriveted_user: AsyncClient,
):
    """Test getting a specific theme."""
    create_response = await async_client_authenticated_as_wriveted_user.post(
        "/api/v1/cms/themes",
        json={
            "name": "Test Theme for Get",
            "config": {
                "colors": {"primary": "#1890ff", "secondary": "#52c41a"},
                "typography": {
                    "fontFamily": "system-ui",
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
                    "avatar": "",
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
                    "messageEntry": "fade",
                    "duration": 300,
                    "easing": "ease-in-out",
                },
                "accessibility": {
                    "highContrast": False,
                    "reduceMotion": False,
                    "fontSize": "default",
                },
            },
        },
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    theme_id = create_response.json()["id"]

    get_response = await async_client_authenticated_as_wriveted_user.get(
        f"/api/v1/cms/themes/{theme_id}"
    )

    assert get_response.status_code == status.HTTP_200_OK
    data = get_response.json()
    assert data["id"] == theme_id
    assert data["name"] == "Test Theme for Get"


@pytest.mark.asyncio
async def test_update_theme(
    async_client_authenticated_as_wriveted_user: AsyncClient,
):
    """Test updating a theme."""
    create_response = await async_client_authenticated_as_wriveted_user.post(
        "/api/v1/cms/themes",
        json={
            "name": "Theme to Update",
            "config": {
                "colors": {"primary": "#1890ff", "secondary": "#52c41a"},
                "typography": {
                    "fontFamily": "system-ui",
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
                    "avatar": "",
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
                    "messageEntry": "fade",
                    "duration": 300,
                    "easing": "ease-in-out",
                },
                "accessibility": {
                    "highContrast": False,
                    "reduceMotion": False,
                    "fontSize": "default",
                },
            },
        },
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    theme_id = create_response.json()["id"]

    update_response = await async_client_authenticated_as_wriveted_user.put(
        f"/api/v1/cms/themes/{theme_id}",
        json={"name": "Updated Theme Name", "description": "Updated description"},
    )

    assert update_response.status_code == status.HTTP_200_OK
    data = update_response.json()
    assert data["name"] == "Updated Theme Name"
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_delete_theme(
    async_client_authenticated_as_wriveted_user: AsyncClient,
):
    """Test soft deleting a theme."""
    create_response = await async_client_authenticated_as_wriveted_user.post(
        "/api/v1/cms/themes",
        json={
            "name": "Theme to Delete",
            "config": {
                "colors": {"primary": "#1890ff", "secondary": "#52c41a"},
                "typography": {
                    "fontFamily": "system-ui",
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
                    "avatar": "",
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
                    "messageEntry": "fade",
                    "duration": 300,
                    "easing": "ease-in-out",
                },
                "accessibility": {
                    "highContrast": False,
                    "reduceMotion": False,
                    "fontSize": "default",
                },
            },
        },
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    theme_id = create_response.json()["id"]

    delete_response = await async_client_authenticated_as_wriveted_user.delete(
        f"/api/v1/cms/themes/{theme_id}"
    )

    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    get_response = await async_client_authenticated_as_wriveted_user.get(
        f"/api/v1/cms/themes/{theme_id}"
    )
    assert get_response.status_code == status.HTTP_200_OK
    data = get_response.json()
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_non_admin_cannot_create_global_theme(
    async_client_authenticated_as_service_account: AsyncClient,
):
    """Test that non-admin users cannot create global themes."""
    theme_data = {
        "name": "Unauthorized Global Theme",
        "school_id": None,
        "config": {
            "colors": {"primary": "#1890ff"},
            "typography": {
                "fontFamily": "system-ui",
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
                "avatar": "",
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
                "messageEntry": "fade",
                "duration": 300,
                "easing": "ease-in-out",
            },
            "accessibility": {
                "highContrast": False,
                "reduceMotion": False,
                "fontSize": "default",
            },
        },
    }

    response = await async_client_authenticated_as_service_account.post(
        "/api/v1/cms/themes", json=theme_data
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_nonexistent_theme(
    async_client_authenticated_as_wriveted_user: AsyncClient,
):
    """Test getting a theme that doesn't exist."""
    fake_id = uuid4()
    response = await async_client_authenticated_as_wriveted_user.get(
        f"/api/v1/cms/themes/{fake_id}"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
