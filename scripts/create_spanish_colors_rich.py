#!/usr/bin/env python3
"""Create an enhanced Spanish Colors flow with rich text and visual elements.

This is a kid-friendly, visually engaging version of the colors lesson
using HTML content, color swatches, and encouraging feedback.

Usage:
  python scripts/create_spanish_colors_rich.py <jwt_token> [--school-id SCHOOL_ID] [--theme-id THEME_ID]
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional

import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/v1")


def rich_msg_node(
    node_id: str, rich_text: str, fallback_text: str, x: int, y: int
) -> Dict[str, Any]:
    """Create a message node with rich HTML content and plain text fallback."""
    return {
        "id": node_id,
        "type": "message",
        "content": {
            "rich_text": rich_text,
            "fallback_text": fallback_text,
        },
        "position": {"x": x, "y": y},
    }


def msg_node(node_id: str, text: str, x: int, y: int) -> Dict[str, Any]:
    """Create a simple message node."""
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


def color_swatch(
    color_name: str, hex_color: str, spanish: str, pronunciation: str
) -> str:
    """Generate HTML for a color swatch with Spanish name."""
    text_color = (
        "#ffffff"
        if color_name.lower() in ["red", "blue", "green", "black", "purple"]
        else "#333333"
    )
    return f"""
    <div style="display: inline-block; margin: 8px; text-align: center;">
      <div style="width: 80px; height: 60px; background: {hex_color}; border-radius: 12px;
                  box-shadow: 0 4px 8px rgba(0,0,0,0.2); display: flex; align-items: center;
                  justify-content: center; margin-bottom: 4px;">
        <span style="color: {text_color}; font-weight: bold; font-size: 14px;">{spanish}</span>
      </div>
      <div style="font-size: 12px; color: #666;">
        <div>{color_name}</div>
        <div style="font-style: italic; font-size: 10px;">{pronunciation}</div>
      </div>
    </div>
    """


def build_rich_colors_flow(theme_id: Optional[str]) -> Dict[str, Any]:
    """Build an enhanced Spanish Colors lesson with rich visuals."""

    # Introduction with colorful header
    intro_html = """
    <div style="text-align: center; padding: 16px;">
      <h2 style="color: #e74c3c; margin: 0;">
        <span style="font-size: 28px;">&#127912;</span>
        Spanish Colors
        <span style="font-size: 28px;">&#127752;</span>
      </h2>
      <p style="color: #666; margin-top: 8px;">
        Let's learn <em>los colores</em> - the colors in Spanish!
      </p>
    </div>
    """

    # Primary colors with swatches
    primary_colors_html = f"""
    <div style="padding: 12px;">
      <h3 style="color: #2c3e50; margin-bottom: 12px;">
        &#128308; Primary Colors &#128309; &#128994;
      </h3>
      <div style="display: flex; flex-wrap: wrap; justify-content: center;">
        {color_swatch("Red", "#e74c3c", "Rojo", "ROH-hoh")}
        {color_swatch("Blue", "#3498db", "Azul", "ah-SOOL")}
        {color_swatch("Yellow", "#f1c40f", "Amarillo", "ah-mah-REE-yoh")}
        {color_swatch("Green", "#27ae60", "Verde", "BEHR-day")}
      </div>
      <p style="margin-top: 12px; text-align: center; font-size: 14px;">
        <strong>Tip:</strong> Try saying each word out loud!
      </p>
    </div>
    """

    # Quiz 1 correct feedback
    correct1_html = """
    <div style="text-align: center; padding: 16px;">
      <div style="font-size: 48px;">&#127881;</div>
      <h3 style="color: #27ae60; margin: 8px 0;">Perfecto!</h3>
      <p>
        <strong style="color: #27ae60;">Verde</strong> means
        <span style="color: #27ae60;">green</span>,
        like grass and trees!
      </p>
      <div style="width: 60px; height: 60px; background: #27ae60; border-radius: 50%;
                  margin: 12px auto; box-shadow: 0 4px 8px rgba(0,0,0,0.2);"></div>
    </div>
    """

    # Quiz 1 wrong feedback
    wrong1_html = """
    <div style="text-align: center; padding: 16px;">
      <div style="font-size: 36px;">&#128161;</div>
      <h3 style="color: #f39c12; margin: 8px 0;">Not quite!</h3>
      <p><strong>Verde</strong> means <span style="color: #27ae60; font-weight: bold;">green</span>.</p>
      <p style="font-size: 13px; color: #666; margin-top: 8px;">
        Remember: <strong style="color: #e74c3c;">Rojo</strong> = Red,
        <strong style="color: #3498db;">Azul</strong> = Blue
      </p>
    </div>
    """

    # More colors section
    more_colors_html = f"""
    <div style="padding: 12px;">
      <h3 style="color: #2c3e50; margin-bottom: 12px;">
        &#10024; More Awesome Colors! &#10024;
      </h3>
      <div style="display: flex; flex-wrap: wrap; justify-content: center;">
        {color_swatch("White", "#ecf0f1", "Blanco", "BLAHN-koh")}
        {color_swatch("Black", "#2c3e50", "Negro", "NEH-groh")}
        {color_swatch("Pink", "#e91e8c", "Rosa", "ROH-sah")}
        {color_swatch("Orange", "#e67e22", "Naranja", "nah-RAHN-hah")}
      </div>
    </div>
    """

    # Quiz 2 correct feedback
    correct2_html = """
    <div style="text-align: center; padding: 16px;">
      <div style="font-size: 48px;">&#127775;</div>
      <h3 style="color: #27ae60; margin: 8px 0;">Excelente!</h3>
      <p>
        <strong style="color: #2c3e50;">Negro</strong> means
        <span style="color: #2c3e50;">black</span>!
      </p>
      <p style="font-size: 13px; color: #666; margin-top: 8px;">
        You're becoming a color expert!
      </p>
    </div>
    """

    # Quiz 2 wrong feedback
    wrong2_html = """
    <div style="text-align: center; padding: 16px;">
      <div style="font-size: 36px;">&#128173;</div>
      <h3 style="color: #f39c12; margin: 8px 0;">Close!</h3>
      <p><strong>Negro</strong> means <strong style="color: #2c3e50;">black</strong>.</p>
      <p style="font-size: 13px; color: #666; margin-top: 8px;">
        <strong>Blanco</strong> = White, <strong style="color: #e91e8c;">Rosa</strong> = Pink
      </p>
    </div>
    """

    # Completion celebration
    complete_html = """
    <div style="text-align: center; padding: 20px;">
      <div style="font-size: 56px;">&#127881; &#127752; &#127881;</div>
      <h2 style="color: #9b59b6; margin: 12px 0;">Lesson Complete!</h2>
      <p style="font-size: 16px;">
        You now know <strong>8 Spanish colors</strong>!
      </p>
      <div style="display: flex; justify-content: center; flex-wrap: wrap; margin-top: 16px;">
        <span style="display: inline-block; width: 24px; height: 24px; border-radius: 50%;
                     background: #e74c3c; margin: 4px;"></span>
        <span style="display: inline-block; width: 24px; height: 24px; border-radius: 50%;
                     background: #3498db; margin: 4px;"></span>
        <span style="display: inline-block; width: 24px; height: 24px; border-radius: 50%;
                     background: #f1c40f; margin: 4px;"></span>
        <span style="display: inline-block; width: 24px; height: 24px; border-radius: 50%;
                     background: #27ae60; margin: 4px;"></span>
        <span style="display: inline-block; width: 24px; height: 24px; border-radius: 50%;
                     background: #ecf0f1; border: 1px solid #ccc; margin: 4px;"></span>
        <span style="display: inline-block; width: 24px; height: 24px; border-radius: 50%;
                     background: #2c3e50; margin: 4px;"></span>
        <span style="display: inline-block; width: 24px; height: 24px; border-radius: 50%;
                     background: #e91e8c; margin: 4px;"></span>
        <span style="display: inline-block; width: 24px; height: 24px; border-radius: 50%;
                     background: #e67e22; margin: 4px;"></span>
      </div>
      <p style="margin-top: 16px; color: #666; font-style: italic;">
        Keep practicing and you'll be a Spanish color master!
      </p>
    </div>
    """

    nodes = [
        rich_msg_node(
            "color_intro",
            intro_html,
            "Welcome to Spanish Colors! Let's learn los colores - the colors in Spanish!",
            0,
            0,
        ),
        rich_msg_node(
            "color_primary",
            primary_colors_html,
            "Primary Colors: Rojo (ROH-hoh) = Red, Azul (ah-SOOL) = Blue, Amarillo (ah-mah-REE-yoh) = Yellow, Verde (BEHR-day) = Green. Try saying each word out loud!",
            300,
            0,
        ),
        question_node(
            "color_quiz1",
            "What color is 'Verde'?",
            "temp.color_answer1",
            "choice",
            600,
            0,
            options=[
                {"label": "Red", "value": "red"},
                {"label": "Green", "value": "green"},
                {"label": "Blue", "value": "blue"},
            ],
        ),
        condition_node(
            "color_check1",
            conditions=[{"if": "temp['color_answer1'] == 'green'", "then": "$0"}],
            default_path="$1",
            x=900,
            y=0,
        ),
        rich_msg_node(
            "color_correct1",
            correct1_html,
            "Perfecto! Verde means green, like grass and trees!",
            1200,
            -120,
        ),
        rich_msg_node(
            "color_wrong1",
            wrong1_html,
            "Not quite! Verde means green. Remember: Rojo = Red, Azul = Blue",
            1200,
            120,
        ),
        rich_msg_node(
            "color_more",
            more_colors_html,
            "More Awesome Colors! Blanco (BLAHN-koh) = White, Negro (NEH-groh) = Black, Rosa (ROH-sah) = Pink, Naranja (nah-RAHN-hah) = Orange.",
            1500,
            0,
        ),
        question_node(
            "color_quiz2",
            "What is the Spanish word for 'Black'?",
            "temp.color_answer2",
            "choice",
            1800,
            0,
            options=[
                {"label": "Blanco", "value": "blanco"},
                {"label": "Negro", "value": "negro"},
                {"label": "Rosa", "value": "rosa"},
            ],
        ),
        condition_node(
            "color_check2",
            conditions=[{"if": "temp['color_answer2'] == 'negro'", "then": "$0"}],
            default_path="$1",
            x=2100,
            y=0,
        ),
        rich_msg_node(
            "color_correct2",
            correct2_html,
            "Excelente! Negro means black! You're becoming a color expert!",
            2400,
            -120,
        ),
        rich_msg_node(
            "color_wrong2",
            wrong2_html,
            "Close! Negro means black. Blanco = White, Rosa = Pink",
            2400,
            120,
        ),
        action_node(
            "color_mark_complete",
            [
                {
                    "type": "set_variable",
                    "variable": "temp.completed.colors",
                    "value": True,
                }
            ],
            2700,
            0,
        ),
        rich_msg_node(
            "color_wrap",
            complete_html,
            "Lesson Complete! You now know 8 Spanish colors! Keep practicing and you'll be a Spanish color master!",
            3000,
            0,
        ),
    ]

    connections = [
        connection("color_intro", "color_primary"),
        connection("color_primary", "color_quiz1"),
        connection("color_quiz1", "color_check1"),
        connection("color_check1", "color_correct1", "$0"),
        connection("color_check1", "color_wrong1", "$1"),
        connection("color_correct1", "color_more"),
        connection("color_wrong1", "color_more"),
        connection("color_more", "color_quiz2"),
        connection("color_quiz2", "color_check2"),
        connection("color_check2", "color_correct2", "$0"),
        connection("color_check2", "color_wrong2", "$1"),
        connection("color_correct2", "color_mark_complete"),
        connection("color_wrong2", "color_mark_complete"),
        connection("color_mark_complete", "color_wrap"),
    ]

    return {
        "name": "Spanish Colors: Visual Learning",
        "description": "An enhanced, kid-friendly Spanish colors lesson with rich visuals and engaging feedback.",
        "version": "2.0.0",
        "entry_node_id": "color_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "spanish_basics",
            "lesson": "colors_rich",
            "audience": "age_8_plus",
            "embeddable": True,
            "return_state": ["temp.completed.colors"],
            "features": ["rich_text", "visual_swatches", "celebratory_feedback"],
        },
    }


def create_flow(
    token: str,
    flow_data: Dict[str, Any],
    api_base: str,
    school_id: Optional[str] = None,
    visibility: str = "public",
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
        description="Create enhanced Spanish Colors flow via API."
    )
    parser.add_argument("token", help="JWT token for CMS API")
    parser.add_argument(
        "--school-id", dest="school_id", help="School ID to own this flow"
    )
    parser.add_argument(
        "--visibility",
        default="public",
        choices=["private", "school", "public", "wriveted"],
        help="Visibility level for the flow (default: public)",
    )
    parser.add_argument(
        "--theme-id", dest="theme_id", help="Optional theme ID to attach"
    )
    parser.add_argument(
        "--api-base", dest="api_base", default=API_BASE, help="API base URL"
    )
    args = parser.parse_args()

    flow = create_flow(
        args.token,
        build_rich_colors_flow(args.theme_id),
        args.api_base,
        args.school_id,
        args.visibility,
    )

    print("Created Spanish Colors (Rich) flow:")
    print(f"- {flow['name']} (ID: {flow['id']})")
    print(f"  Visibility: {args.visibility}, School: {args.school_id or 'None'}")
    print(
        f"\nBuilder URL: http://localhost:3000/admin/chatflows/flows/{flow['id']}/builder/"
    )


if __name__ == "__main__":
    main()
