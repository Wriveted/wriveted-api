#!/usr/bin/env python3
"""Create a Spanish Basics Rich Hub flow via API.

This hub composes the rich Spanish lesson flows:
- Greetings (rich)
- Numbers (rich)
- Colors (rich)

Usage:
  python scripts/create_spanish_rich_hub_flow.py <jwt_token> \
    --greetings-id <id> --numbers-id <id> --colors-id <id> [--school-id SCHOOL_ID] [--theme-id THEME_ID]
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
        "content": {"conditions": conditions, "default_path": default_path},
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
    return {"source": source, "target": target, "type": connection_type}


def snapshot(
    nodes: List[Dict[str, Any]],
    connections: List[Dict[str, Any]],
    theme_id: Optional[str],
) -> Dict[str, Any]:
    data: Dict[str, Any] = {"nodes": nodes, "connections": connections}
    if theme_id:
        data["theme_id"] = theme_id
    return data


def build_spanish_rich_hub_flow(
    greetings_id: str,
    numbers_id: str,
    colors_id: str,
    theme_id: Optional[str],
) -> Dict[str, Any]:
    nodes = [
        msg_node(
            "hub_intro",
            "¡Hola! Welcome to Spanish Basics (Visual). Let's learn with colors and cards!",
            0,
            0,
        ),
        question_node(
            "hub_name",
            "What's your name?",
            "temp.student_name",
            "text",
            300,
            0,
        ),
        msg_node(
            "hub_welcome",
            "Nice to meet you, {{temp.student_name}}! Choose a lesson:",
            600,
            0,
        ),
        question_node(
            "hub_lesson_choice",
            "Which lesson would you like?",
            "temp.lesson_choice",
            "choice",
            900,
            0,
            options=[
                {"label": "Greetings (Hola, Adiós)", "value": "greetings"},
                {"label": "Numbers (Uno, Dos)", "value": "numbers"},
                {"label": "Colors (Rojo, Azul)", "value": "colors"},
            ],
        ),
        condition_node(
            "hub_route",
            conditions=[
                {"if": "temp.lesson_choice == 'greetings'", "then": "$0"},
                {"if": "temp.lesson_choice == 'numbers'", "then": "$1"},
            ],
            default_path="default",
            x=1200,
            y=0,
        ),
        composite_node("hub_greetings", greetings_id, "Greetings (Visual)", 1500, -180),
        composite_node("hub_numbers", numbers_id, "Numbers (Visual)", 1500, 0),
        composite_node("hub_colors", colors_id, "Colors (Visual)", 1500, 180),
        msg_node(
            "hub_after_lesson",
            "Great job! Want to try another visual lesson?",
            1800,
            0,
        ),
        question_node(
            "hub_continue",
            "What would you like to do next?",
            "temp.continue_choice",
            "choice",
            2100,
            0,
            options=[
                {"label": "Another lesson", "value": "more"},
                {"label": "I'm done", "value": "done"},
            ],
        ),
        condition_node(
            "hub_continue_route",
            conditions=[{"if": "temp.continue_choice == 'more'", "then": "$0"}],
            default_path="$1",
            x=2400,
            y=0,
        ),
        msg_node(
            "hub_final",
            "Adiós, {{temp.student_name}}! Keep practicing your Spanish.",
            2700,
            0,
        ),
    ]

    connections = [
        connection("hub_intro", "hub_name"),
        connection("hub_name", "hub_welcome"),
        connection("hub_welcome", "hub_lesson_choice"),
        connection("hub_lesson_choice", "hub_route"),
        connection("hub_route", "hub_greetings", "$0"),
        connection("hub_route", "hub_numbers", "$1"),
        connection("hub_route", "hub_colors", "DEFAULT"),
        connection("hub_greetings", "hub_after_lesson"),
        connection("hub_numbers", "hub_after_lesson"),
        connection("hub_colors", "hub_after_lesson"),
        connection("hub_after_lesson", "hub_continue"),
        connection("hub_continue", "hub_continue_route"),
        connection("hub_continue_route", "hub_lesson_choice", "$0"),
        connection("hub_continue_route", "hub_final", "$1"),
    ]

    return {
        "name": "Spanish Basics: Visual Hub",
        "description": "A visual, kid-friendly Spanish learning hub with rich lesson flows.",
        "version": "2.0.0",
        "entry_node_id": "hub_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "spanish_basics",
            "lesson": "hub_rich",
            "audience": "age_8_plus",
            "embeddable": True,
            "return_state": [
                "temp.completed.greetings",
                "temp.completed.numbers",
                "temp.completed.colors",
                "temp.student_name",
            ],
        },
    }


def create_or_update_flow(
    token: str,
    flow_data: Dict[str, Any],
    api_base: str,
    flow_id: Optional[str] = None,
    visibility: str = "public",
    school_id: Optional[str] = None,
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    flow_data["visibility"] = visibility
    flow_data["publish"] = True
    if school_id:
        flow_data["school_id"] = school_id

    if flow_id:
        response = requests.put(
            f"{api_base}/cms/flows/{flow_id}",
            headers=headers,
            json=flow_data,
            timeout=30,
        )
        action = "Updated"
    else:
        response = requests.post(
            f"{api_base}/cms/flows", headers=headers, json=flow_data, timeout=30
        )
        action = "Created"

    if response.status_code not in (200, 201):
        print(f"Error: {response.status_code}")
        print(response.text)
        sys.exit(1)

    result = response.json()
    print(f"{action} flow: {result.get('name')} (ID: {result.get('id')})")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create Spanish Basics Visual Hub flow."
    )
    parser.add_argument("token", help="JWT token for CMS API")
    parser.add_argument("--greetings-id", required=True, help="Greetings rich flow ID")
    parser.add_argument("--numbers-id", required=True, help="Numbers rich flow ID")
    parser.add_argument("--colors-id", required=True, help="Colors rich flow ID")
    parser.add_argument("--flow-id", help="Existing hub flow ID to update")
    parser.add_argument(
        "--school-id", dest="school_id", help="School ID to own the flow"
    )
    parser.add_argument(
        "--visibility",
        default="public",
        choices=["private", "school", "public", "wriveted"],
        help="Visibility level for the flow (default: public)",
    )
    parser.add_argument("--theme-id", dest="theme_id", help="Optional theme ID")
    parser.add_argument(
        "--api-base", dest="api_base", default=API_BASE, help="API base URL"
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Only print JSON output, don't call API",
    )
    args = parser.parse_args()

    flow_data = build_spanish_rich_hub_flow(
        greetings_id=args.greetings_id,
        numbers_id=args.numbers_id,
        colors_id=args.colors_id,
        theme_id=args.theme_id,
    )

    if args.json_only:
        import json

        print(json.dumps(flow_data, indent=2))
        return

    create_or_update_flow(
        args.token,
        flow_data,
        api_base=args.api_base,
        flow_id=args.flow_id,
        visibility=args.visibility,
        school_id=args.school_id,
    )


if __name__ == "__main__":
    main()
