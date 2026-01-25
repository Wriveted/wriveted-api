#!/usr/bin/env python3
"""Create an enhanced Spanish Numbers flow with rich text and visual elements."""

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
    return {
        "id": node_id,
        "type": "message",
        "content": {
            "rich_text": rich_text,
            "fallback_text": fallback_text,
        },
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


def number_tile(num: int, spanish: str, pronunciation: str) -> str:
    """Generate HTML for a number tile."""
    colors = [
        "#e74c3c",
        "#e67e22",
        "#f1c40f",
        "#27ae60",
        "#3498db",
        "#9b59b6",
        "#1abc9c",
        "#34495e",
        "#e91e8c",
        "#2ecc71",
    ]
    color = colors[num % 10]
    return f"""
    <div style="display: inline-block; margin: 6px; text-align: center;
                width: 70px; height: 80px; border-radius: 12px;
                background: {color}; box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                display: flex; flex-direction: column; align-items: center;
                justify-content: center; color: white;">
      <div style="font-size: 28px; font-weight: bold;">{num}</div>
      <div style="font-size: 12px; font-weight: bold; margin-top: 4px;">{spanish}</div>
      <div style="font-size: 8px; opacity: 0.8;">{pronunciation}</div>
    </div>
    """


def build_rich_numbers_flow(theme_id: Optional[str]) -> Dict[str, Any]:
    """Build an enhanced Spanish Numbers 1-10 lesson with rich visuals."""

    intro_html = """
    <div style="text-align: center; padding: 16px;">
      <h2 style="color: #3498db; margin: 0;">
        <span style="font-size: 32px;">&#128290;</span>
        Spanish Numbers 1-10
        <span style="font-size: 32px;">&#127919;</span>
      </h2>
      <p style="color: #666; margin-top: 8px;">
        Learn to count <em>uno, dos, tres...</em> in Spanish!
      </p>
    </div>
    """

    numbers_1_5_html = f"""
    <div style="padding: 12px;">
      <h3 style="color: #2c3e50; margin-bottom: 12px; text-align: center;">
        &#128290; Numbers 1-5
      </h3>
      <div style="display: flex; flex-wrap: wrap; justify-content: center;">
        {number_tile(1, "Uno", "OO-noh")}
        {number_tile(2, "Dos", "dohs")}
        {number_tile(3, "Tres", "trehs")}
        {number_tile(4, "Cuatro", "KWAH-troh")}
        {number_tile(5, "Cinco", "SEEN-koh")}
      </div>
      <p style="margin-top: 12px; text-align: center; font-size: 14px; color: #666;">
        &#127925; Try counting along: <em>uno, dos, tres, cuatro, cinco!</em>
      </p>
    </div>
    """

    correct1_html = """
    <div style="text-align: center; padding: 16px;">
      <div style="font-size: 48px;">&#127881;</div>
      <h3 style="color: #27ae60; margin: 8px 0;">¡Perfecto!</h3>
      <p>
        <strong style="color: #27ae60;">Tres</strong> = <strong>3</strong>
      </p>
      <div style="font-size: 48px; margin-top: 8px;">&#51;&#65039;&#8419;</div>
    </div>
    """

    wrong1_html = """
    <div style="text-align: center; padding: 16px;">
      <div style="font-size: 36px;">&#128161;</div>
      <h3 style="color: #f39c12; margin: 8px 0;">Not quite!</h3>
      <p><strong>Tres</strong> = <strong style="color: #3498db;">3</strong></p>
      <p style="font-size: 13px; color: #666; margin-top: 8px;">
        Remember: Uno=1, Dos=2, <strong>Tres=3</strong>, Cuatro=4, Cinco=5
      </p>
    </div>
    """

    numbers_6_10_html = f"""
    <div style="padding: 12px;">
      <h3 style="color: #2c3e50; margin-bottom: 12px; text-align: center;">
        &#128290; Numbers 6-10
      </h3>
      <div style="display: flex; flex-wrap: wrap; justify-content: center;">
        {number_tile(6, "Seis", "says")}
        {number_tile(7, "Siete", "SYEH-teh")}
        {number_tile(8, "Ocho", "OH-choh")}
        {number_tile(9, "Nueve", "NWEH-beh")}
        {number_tile(10, "Diez", "dyehs")}
      </div>
      <p style="margin-top: 12px; text-align: center; font-size: 14px; color: #666;">
        &#127925; Now you can count to 10! <em>...seis, siete, ocho, nueve, diez!</em>
      </p>
    </div>
    """

    correct2_html = """
    <div style="text-align: center; padding: 16px;">
      <div style="font-size: 48px;">&#127775;</div>
      <h3 style="color: #27ae60; margin: 8px 0;">¡Excelente!</h3>
      <p>
        <strong style="color: #9b59b6;">Siete</strong> = <strong>7</strong>
      </p>
      <p style="font-size: 13px; color: #666; margin-top: 8px;">
        You're becoming a number expert!
      </p>
    </div>
    """

    wrong2_html = """
    <div style="text-align: center; padding: 16px;">
      <div style="font-size: 36px;">&#128173;</div>
      <h3 style="color: #f39c12; margin: 8px 0;">Close!</h3>
      <p><strong>Siete</strong> = <strong style="color: #9b59b6;">7</strong></p>
      <p style="font-size: 13px; color: #666; margin-top: 8px;">
        Seis=6, <strong>Siete=7</strong>, Ocho=8
      </p>
    </div>
    """

    complete_html = """
    <div style="text-align: center; padding: 20px;">
      <div style="font-size: 56px;">&#127881; &#127942; &#127881;</div>
      <h2 style="color: #3498db; margin: 12px 0;">¡Fantástico!</h2>
      <p style="font-size: 16px;">
        You can now count to <strong>10</strong> in Spanish!
      </p>
      <div style="margin-top: 16px; padding: 16px; background: linear-gradient(135deg, #3498db 0%, #9b59b6 100%);
                  border-radius: 16px; color: white;">
        <p style="margin: 0; font-size: 16px; font-weight: bold;">
          &#49;&#65039;&#8419; Uno &middot;
          &#50;&#65039;&#8419; Dos &middot;
          &#51;&#65039;&#8419; Tres &middot;
          &#52;&#65039;&#8419; Cuatro &middot;
          &#53;&#65039;&#8419; Cinco
        </p>
        <p style="margin: 8px 0 0 0; font-size: 16px; font-weight: bold;">
          &#54;&#65039;&#8419; Seis &middot;
          &#55;&#65039;&#8419; Siete &middot;
          &#56;&#65039;&#8419; Ocho &middot;
          &#57;&#65039;&#8419; Nueve &middot;
          &#128287; Diez
        </p>
      </div>
    </div>
    """

    nodes = [
        rich_msg_node(
            "num_intro",
            intro_html,
            "Welcome to Spanish Numbers! Learn to count uno, dos, tres... in Spanish!",
            0,
            0,
        ),
        rich_msg_node(
            "num_1_5",
            numbers_1_5_html,
            "Numbers 1-5: Uno (OO-noh) = 1, Dos (dohs) = 2, Tres (trehs) = 3, Cuatro (KWAH-troh) = 4, Cinco (SEEN-koh) = 5",
            300,
            0,
        ),
        question_node(
            "num_quiz1",
            "What number is 'Tres'?",
            "temp.num_answer1",
            "choice",
            600,
            0,
            options=[
                {"label": "2", "value": "2"},
                {"label": "3", "value": "3"},
                {"label": "5", "value": "5"},
            ],
        ),
        condition_node(
            "num_check1",
            conditions=[{"if": "temp.num_answer1 == '3'", "then": "$0"}],
            default_path="$1",
            x=900,
            y=0,
        ),
        rich_msg_node("num_correct1", correct1_html, "¡Perfecto! Tres = 3", 1200, -120),
        rich_msg_node("num_wrong1", wrong1_html, "Not quite! Tres = 3", 1200, 120),
        rich_msg_node(
            "num_6_10",
            numbers_6_10_html,
            "Numbers 6-10: Seis (says) = 6, Siete (SYEH-teh) = 7, Ocho (OH-choh) = 8, Nueve (NWEH-beh) = 9, Diez (dyehs) = 10",
            1500,
            0,
        ),
        question_node(
            "num_quiz2",
            "What number is 'Siete'?",
            "temp.num_answer2",
            "choice",
            1800,
            0,
            options=[
                {"label": "6", "value": "6"},
                {"label": "7", "value": "7"},
                {"label": "8", "value": "8"},
            ],
        ),
        condition_node(
            "num_check2",
            conditions=[{"if": "temp.num_answer2 == '7'", "then": "$0"}],
            default_path="$1",
            x=2100,
            y=0,
        ),
        rich_msg_node(
            "num_correct2", correct2_html, "¡Excelente! Siete = 7", 2400, -120
        ),
        rich_msg_node("num_wrong2", wrong2_html, "Close! Siete = 7", 2400, 120),
        action_node(
            "num_mark_complete",
            [
                {
                    "type": "set_variable",
                    "variable": "temp.completed.numbers",
                    "value": True,
                }
            ],
            2700,
            0,
        ),
        rich_msg_node(
            "num_wrap",
            complete_html,
            "¡Fantástico! You can now count to 10 in Spanish!",
            3000,
            0,
        ),
    ]

    connections = [
        connection("num_intro", "num_1_5"),
        connection("num_1_5", "num_quiz1"),
        connection("num_quiz1", "num_check1"),
        connection("num_check1", "num_correct1", "$0"),
        connection("num_check1", "num_wrong1", "$1"),
        connection("num_correct1", "num_6_10"),
        connection("num_wrong1", "num_6_10"),
        connection("num_6_10", "num_quiz2"),
        connection("num_quiz2", "num_check2"),
        connection("num_check2", "num_correct2", "$0"),
        connection("num_check2", "num_wrong2", "$1"),
        connection("num_correct2", "num_mark_complete"),
        connection("num_wrong2", "num_mark_complete"),
        connection("num_mark_complete", "num_wrap"),
    ]

    return {
        "name": "Spanish Numbers 1-10: Visual Learning",
        "description": "An enhanced, kid-friendly Spanish numbers lesson with colorful tiles.",
        "version": "2.0.0",
        "entry_node_id": "num_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "spanish_basics",
            "lesson": "numbers_rich",
            "audience": "age_8_plus",
            "embeddable": True,
            "return_state": ["temp.completed.numbers"],
        },
    }


if __name__ == "__main__":
    import json

    print(json.dumps(build_rich_numbers_flow(None), indent=2))
