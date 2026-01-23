#!/usr/bin/env python3
"""
Integration tests for CMS content full-text search (FTS) support.
"""

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_cms_content_search_document_exists(async_session):
    """Verify the generated tsvector column and GIN index exist."""
    # Column exists
    col = await async_session.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'cms_content' AND column_name = 'search_document'
            """
        )
    )
    assert col.scalar() == 1

    # Index exists
    idx = await async_session.execute(
        text(
            """
            SELECT 1
            FROM pg_indexes
            WHERE tablename = 'cms_content' AND indexname = 'ix_cms_content_search_document'
            """
        )
    )
    assert idx.scalar() == 1


def test_cms_content_search_fts(client, backend_service_account_headers):
    """Ensure search matches on fields included in the generated tsvector."""
    # Create items that should be searchable via FTS
    items = [
        {
            "type": "question",
            "content": {"question": "What is the capital of Atlantis?"},
            "tags": ["mythical", "geography"],
        },
        {
            "type": "joke",
            "content": {
                "setup": "Why did the coder cross the road?",
                "punchline": "To get to the other IDE",
            },
            "tags": ["humor", "dev"],
        },
    ]

    for it in items:
        r = client.post(
            "v1/cms/content", json=it, headers=backend_service_account_headers
        )
        assert r.status_code == 201

    # Search for 'Atlantis' (from question)
    r = client.get(
        "v1/cms/content",
        params={"search": "Atlantis"},
        headers=backend_service_account_headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert any(
        "Atlantis".lower() in (d.get("content", {}).get("question", "")).lower()
        for d in data
    )

    # Search for 'coder' (from setup)
    r = client.get(
        "v1/cms/content",
        params={"search": "coder"},
        headers=backend_service_account_headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert any("coder" in (d.get("content", {}).get("setup", "")).lower() for d in data)
