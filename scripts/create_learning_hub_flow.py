#!/usr/bin/env python3
"""Create a Learning Hub that composes flows from multiple schools.

This demonstrates cross-school composite node composition:
- Book Recommender: Wriveted global content (visibility: wriveted)
- Cipher Clubhouse: From E2E Testing school (visibility: public)
- Spanish Basics: From Spanish Language Academy (visibility: public)

Usage:
  python scripts/create_learning_hub_flow.py <jwt_token> \
    --book-recommender-id <id> \
    --cipher-hub-id <id> \
    --spanish-hub-id <id>
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional

import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/v1")


def msg_node(node_id: str, text: str, x: int, y: int) -> Dict[str, Any]:
    """Create a message node with direct text content."""
    return {
        "id": node_id,
        "type": "message",
        "content": {"text": text},
        "position": {"x": x, "y": y},
    }


def question_node(
    node_id: str,
    text: str,
    variable: str,
    input_type: str,
    x: int,
    y: int,
    options: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    content: Dict[str, Any] = {
        "question": {"text": text},
        "variable": variable,
        "input_type": input_type,
    }
    if options:
        content["options"] = options
    return {
        "id": node_id,
        "type": "question",
        "content": content,
        "position": {"x": x, "y": y},
    }


def condition_node(
    node_id: str,
    conditions: List[Dict[str, Any]],
    default_path: str,
    x: int,
    y: int,
) -> Dict[str, Any]:
    return {
        "id": node_id,
        "type": "condition",
        "content": {
            "conditions": conditions,
            "default_path": default_path,
        },
        "position": {"x": x, "y": y},
    }


def action_node(
    node_id: str, actions: List[Dict[str, Any]], x: int, y: int
) -> Dict[str, Any]:
    return {
        "id": node_id,
        "type": "action",
        "content": {"actions": actions},
        "position": {"x": x, "y": y},
    }


def composite_node(
    node_id: str,
    composite_flow_id: str,
    composite_name: str,
    x: int,
    y: int,
) -> Dict[str, Any]:
    return {
        "id": node_id,
        "type": "composite",
        "content": {
            "composite_flow_id": composite_flow_id,
            "composite_name": composite_name,
        },
        "position": {"x": x, "y": y},
    }


def connection(
    source: str, target: str, connection_type: str = "DEFAULT"
) -> Dict[str, Any]:
    return {
        "source": source,
        "target": target,
        "type": connection_type,
    }


def snapshot(
    nodes: List[Dict[str, Any]],
    connections: List[Dict[str, Any]],
    theme_id: Optional[str],
) -> Dict[str, Any]:
    data: Dict[str, Any] = {"nodes": nodes, "connections": connections}
    if theme_id:
        data["theme_id"] = theme_id
    return data


def build_learning_hub_flow(
    book_recommender_id: str,
    cipher_hub_id: str,
    spanish_hub_id: str,
    theme_id: Optional[str],
) -> Dict[str, Any]:
    """
    Master learning hub that composes flows from multiple schools.

    This demonstrates:
    1. Cross-school composite node embedding
    2. Visibility-based access control
    3. State sharing across sub-flows
    """
    nodes = [
        msg_node(
            "hub_intro",
            "Welcome to the Learning Hub! This is your gateway to learning adventures.",
            0,
            0,
        ),
        question_node(
            "hub_name",
            "First, what's your name?",
            "user.name",
            "text",
            300,
            0,
        ),
        msg_node(
            "hub_welcome",
            "Great to meet you, {{user.name}}! We have three amazing learning experiences for you.",
            600,
            0,
        ),
        question_node(
            "hub_activity",
            "What would you like to do today?",
            "temp.activity_choice",
            "choice",
            900,
            0,
            options=[
                {"label": "Find a new book to read", "value": "books"},
                {"label": "Learn secret codes (Ciphers)", "value": "ciphers"},
                {"label": "Learn some Spanish", "value": "spanish"},
            ],
        ),
        condition_node(
            "hub_route",
            conditions=[
                {
                    "if": "temp.activity_choice == 'books'",
                    "then": "$0",
                },
                {
                    "if": "temp.activity_choice == 'ciphers'",
                    "then": "$1",
                },
            ],
            default_path="default",
            x=1200,
            y=0,
        ),
        # Composite nodes referencing flows from different schools
        composite_node(
            "hub_books",
            book_recommender_id,
            "Book Recommender (Wriveted Global)",
            1500,
            -180,
        ),
        composite_node(
            "hub_ciphers",
            cipher_hub_id,
            "Cipher Clubhouse (E2E Testing School)",
            1500,
            0,
        ),
        composite_node(
            "hub_spanish",
            spanish_hub_id,
            "Spanish Basics (Spanish Language Academy)",
            1500,
            180,
        ),
        msg_node(
            "hub_after_activity",
            "Nice work, {{user.name}}! You've completed an activity.",
            1800,
            0,
        ),
        question_node(
            "hub_another",
            "Would you like to try another activity?",
            "temp.try_another",
            "choice",
            2100,
            0,
            options=[
                {"label": "Yes, show me more!", "value": "yes"},
                {"label": "No, I'm done for now", "value": "no"},
            ],
        ),
        condition_node(
            "hub_another_route",
            conditions=[{"if": "temp.try_another == 'yes'", "then": "$0"}],
            default_path="$1",
            x=2400,
            y=0,
        ),
        msg_node(
            "hub_summary",
            "Here's what you explored today:",
            2700,
            0,
        ),
        # Summary of activities - shows state shared from sub-flows
        msg_node(
            "hub_final",
            "Thanks for learning with us, {{user.name}}! Keep exploring and stay curious!",
            3000,
            0,
        ),
    ]

    connections = [
        connection("hub_intro", "hub_name"),
        connection("hub_name", "hub_welcome"),
        connection("hub_welcome", "hub_activity"),
        connection("hub_activity", "hub_route"),
        connection("hub_route", "hub_books", "$0"),
        connection("hub_route", "hub_ciphers", "$1"),
        connection("hub_route", "hub_spanish", "DEFAULT"),
        connection("hub_books", "hub_after_activity"),
        connection("hub_ciphers", "hub_after_activity"),
        connection("hub_spanish", "hub_after_activity"),
        connection("hub_after_activity", "hub_another"),
        connection("hub_another", "hub_another_route"),
        connection("hub_another_route", "hub_activity", "$0"),
        connection("hub_another_route", "hub_summary", "$1"),
        connection("hub_summary", "hub_final"),
    ]

    return {
        "name": "Learning Hub: Multi-School Experience",
        "description": "A master hub composing flows from multiple schools: Book Recommender (Wriveted), Cipher Clubhouse (E2E Testing), Spanish Basics (Spanish Academy).",
        "version": "1.0.0",
        "entry_node_id": "hub_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "learning_hub",
            "audience": "age_8_plus",
            "cross_school_composition": True,
            "composed_flows": {
                "book_recommender": {
                    "flow_id": book_recommender_id,
                    "source": "wriveted_global",
                    "visibility": "wriveted",
                },
                "cipher_clubhouse": {
                    "flow_id": cipher_hub_id,
                    "source": "e2e_testing_school",
                    "visibility": "public",
                },
                "spanish_basics": {
                    "flow_id": spanish_hub_id,
                    "source": "spanish_language_academy",
                    "visibility": "public",
                },
            },
            "versioning_notes": "Sub-flows are referenced by ID. Version changes in sub-flows will affect this hub. Consider pinning to specific versions for production stability.",
        },
    }


def create_flow(
    token: str,
    flow_data: Dict[str, Any],
    api_base: str,
    school_id: Optional[str] = None,
    visibility: str = "wriveted",
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    if school_id:
        flow_data["school_id"] = school_id
    flow_data["visibility"] = visibility

    response = requests.post(
        f"{api_base}/cms/flows", headers=headers, json=flow_data, timeout=30
    )

    if response.status_code != 201:
        print(f"Error creating flow: {response.status_code}")
        print(response.text)
        sys.exit(1)

    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Learning Hub flow via API.")
    parser.add_argument("token", help="JWT token for CMS API")
    parser.add_argument(
        "--book-recommender-id",
        required=True,
        dest="book_id",
        help="Book Recommender flow ID",
    )
    parser.add_argument(
        "--cipher-hub-id",
        required=True,
        dest="cipher_id",
        help="Cipher Clubhouse hub flow ID",
    )
    parser.add_argument(
        "--spanish-hub-id",
        required=True,
        dest="spanish_id",
        help="Spanish Basics hub flow ID",
    )
    parser.add_argument(
        "--school-id", dest="school_id", help="School ID to own this flow"
    )
    parser.add_argument(
        "--visibility",
        default="wriveted",
        choices=["private", "school", "public", "wriveted"],
        help="Visibility level (default: wriveted)",
    )
    parser.add_argument("--theme-id", dest="theme_id", help="Optional theme ID")
    parser.add_argument(
        "--api-base", dest="api_base", default=API_BASE, help="API base URL"
    )
    args = parser.parse_args()

    flow = create_flow(
        args.token,
        build_learning_hub_flow(
            book_recommender_id=args.book_id,
            cipher_hub_id=args.cipher_id,
            spanish_hub_id=args.spanish_id,
            theme_id=args.theme_id,
        ),
        args.api_base,
        args.school_id,
        args.visibility,
    )

    print("Created Learning Hub flow:")
    print(f"- {flow['name']} (ID: {flow['id']})")
    print(
        f"  Visibility: {args.visibility}, School: {args.school_id or 'None (Global)'}"
    )
    print(
        f"  Builder URL: http://localhost:3000/admin/chatflows/flows/{flow['id']}/builder/"
    )
    print(f"\nThis hub composes flows from:")
    print(f"  - Book Recommender: {args.book_id}")
    print(f"  - Cipher Clubhouse: {args.cipher_id}")
    print(f"  - Spanish Basics: {args.spanish_id}")


if __name__ == "__main__":
    main()
