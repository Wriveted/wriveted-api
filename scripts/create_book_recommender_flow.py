#!/usr/bin/env python3
"""Create a simple book recommendation chatflow.

This is a minimal book recommender that asks about reading preferences
and suggests books. Designed to be embedded as a composite node
in larger flows.

Usage:
  python scripts/create_book_recommender_flow.py <jwt_token> [--school-id SCHOOL_ID]
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional

import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/v1")


def msg_node(node_id: str, text: str, x: int, y: int) -> Dict[str, Any]:
    return {
        "id": node_id,
        "type": "message",
        "content": {"messages": [{"content": text}]},
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


def build_book_recommender_flow(theme_id: Optional[str]) -> Dict[str, Any]:
    """Simple book recommender flow."""
    nodes = [
        msg_node(
            "rec_intro",
            "Hi! I'm here to help you find your next great book. Let me ask you a few questions.",
            0,
            0,
        ),
        question_node(
            "rec_genre",
            "What kind of stories do you like?",
            "temp.preferred_genre",
            "choice",
            300,
            0,
            options=[
                {"label": "Adventure & Action", "value": "adventure"},
                {"label": "Fantasy & Magic", "value": "fantasy"},
                {"label": "Mystery & Detective", "value": "mystery"},
                {"label": "Funny Stories", "value": "humor"},
            ],
        ),
        question_node(
            "rec_length",
            "How long do you like your books?",
            "temp.book_length",
            "choice",
            600,
            0,
            options=[
                {"label": "Short and quick", "value": "short"},
                {"label": "Medium - a few chapters", "value": "medium"},
                {"label": "Long epic adventures", "value": "long"},
            ],
        ),
        condition_node(
            "rec_route",
            conditions=[
                {
                    "if": {"var": "temp.preferred_genre", "eq": "adventure"},
                    "then": "option_0",
                },
                {
                    "if": {"var": "temp.preferred_genre", "eq": "fantasy"},
                    "then": "option_1",
                },
                {
                    "if": {"var": "temp.preferred_genre", "eq": "mystery"},
                    "then": "option_2",
                },
            ],
            default_path="default",
            x=900,
            y=0,
        ),
        msg_node(
            "rec_adventure",
            "For adventure lovers, try 'Hatchet' by Gary Paulsen or 'My Side of the Mountain' by Jean Craighead George!",
            1200,
            -270,
        ),
        msg_node(
            "rec_fantasy",
            "For fantasy fans, check out 'Percy Jackson' by Rick Riordan or 'The Wild Robot' by Peter Brown!",
            1200,
            -90,
        ),
        msg_node(
            "rec_mystery",
            "For mystery lovers, try 'Escape from Mr. Lemoncello's Library' or 'The Westing Game'!",
            1200,
            90,
        ),
        msg_node(
            "rec_humor",
            "For laughs, read 'Diary of a Wimpy Kid' or 'Dog Man' by Dav Pilkey!",
            1200,
            270,
        ),
        action_node(
            "rec_save_prefs",
            [
                {
                    "type": "set_variable",
                    "variable": "user.reading_preference",
                    "value": "{{temp.preferred_genre}}",
                },
                {
                    "type": "set_variable",
                    "variable": "temp.recommendation_complete",
                    "value": True,
                },
            ],
            1500,
            0,
        ),
        msg_node(
            "rec_wrap",
            "I've noted your reading preferences. Happy reading!",
            1800,
            0,
        ),
    ]

    connections = [
        connection("rec_intro", "rec_genre"),
        connection("rec_genre", "rec_length"),
        connection("rec_length", "rec_route"),
        connection("rec_route", "rec_adventure", "$0"),
        connection("rec_route", "rec_fantasy", "$1"),
        connection("rec_route", "rec_mystery", "$2"),
        connection("rec_route", "rec_humor", "DEFAULT"),
        connection("rec_adventure", "rec_save_prefs"),
        connection("rec_fantasy", "rec_save_prefs"),
        connection("rec_mystery", "rec_save_prefs"),
        connection("rec_humor", "rec_save_prefs"),
        connection("rec_save_prefs", "rec_wrap"),
    ]

    return {
        "name": "Book Recommender",
        "description": "A simple book recommendation chatflow that asks preferences and suggests books.",
        "version": "1.0.0",
        "entry_node_id": "rec_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "book_recommender",
            "audience": "age_8_plus",
            "embeddable": True,
            "return_state": [
                "user.reading_preference",
                "temp.recommendation_complete",
            ],
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
    parser = argparse.ArgumentParser(
        description="Create Book Recommender flow via API."
    )
    parser.add_argument("token", help="JWT token for CMS API")
    parser.add_argument(
        "--school-id", dest="school_id", help="School ID to own this flow"
    )
    parser.add_argument(
        "--visibility",
        default="wriveted",
        choices=["private", "school", "public", "wriveted"],
        help="Visibility level (default: wriveted for global content)",
    )
    parser.add_argument("--theme-id", dest="theme_id", help="Optional theme ID")
    parser.add_argument(
        "--api-base", dest="api_base", default=API_BASE, help="API base URL"
    )
    args = parser.parse_args()

    flow = create_flow(
        args.token,
        build_book_recommender_flow(args.theme_id),
        args.api_base,
        args.school_id,
        args.visibility,
    )

    print("Created Book Recommender flow:")
    print(f"- {flow['name']} (ID: {flow['id']})")
    print(f"  Visibility: {args.visibility}, School: {args.school_id or 'None'}")
    print(
        f"  Builder URL: http://localhost:3000/admin/chatflows/flows/{flow['id']}/builder/"
    )
    print(f"\nTo embed this flow as a composite node, use flow ID: {flow['id']}")


if __name__ == "__main__":
    main()
