#!/usr/bin/env python3
"""Create an enhanced Spanish Greetings flow with rich text and visual elements."""

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


def greeting_card(spanish: str, english: str, pronunciation: str, emoji: str) -> str:
    """Generate HTML for a greeting card."""
    return f"""
    <div style="display: inline-block; margin: 8px; text-align: center;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 16px 24px; border-radius: 16px; min-width: 120px;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);">
      <div style="font-size: 32px; margin-bottom: 8px;">{emoji}</div>
      <div style="color: white; font-weight: bold; font-size: 18px;">{spanish}</div>
      <div style="color: rgba(255,255,255,0.8); font-size: 12px; margin-top: 4px;">
        {english}
      </div>
      <div style="color: rgba(255,255,255,0.7); font-style: italic; font-size: 10px; margin-top: 2px;">
        {pronunciation}
      </div>
    </div>
    """


def build_rich_greetings_flow(theme_id: Optional[str]) -> Dict[str, Any]:
    """Build an enhanced Spanish Greetings lesson with rich visuals."""

    intro_html = """
    <div style="text-align: center; padding: 16px;">
      <h2 style="color: #667eea; margin: 0;">
        <span style="font-size: 32px;">&#128075;</span>
        Spanish Greetings
        <span style="font-size: 32px;">&#127881;</span>
      </h2>
      <p style="color: #666; margin-top: 8px;">
        Learn to say hello and goodbye in Spanish!
      </p>
    </div>
    """

    hello_html = f"""
    <div style="padding: 12px;">
      <h3 style="color: #2c3e50; margin-bottom: 12px; text-align: center;">
        &#128522; Saying Hello
      </h3>
      <div style="display: flex; flex-wrap: wrap; justify-content: center;">
        {greeting_card("Hola", "Hello", "OH-lah", "&#128075;")}
        {greeting_card("Buenos días", "Good morning", "BWEH-nohs DEE-ahs", "&#127774;")}
        {greeting_card("Buenas tardes", "Good afternoon", "BWEH-nahs TAR-des", "&#127773;")}
      </div>
    </div>
    """

    correct1_html = """
    <div style="text-align: center; padding: 16px;">
      <div style="font-size: 48px;">&#127881;</div>
      <h3 style="color: #27ae60; margin: 8px 0;">¡Muy bien!</h3>
      <p>
        <strong style="color: #667eea;">Hola</strong> is how you say
        <span style="color: #667eea; font-weight: bold;">Hello</span> in Spanish!
      </p>
      <p style="font-size: 24px; margin-top: 8px;">&#128075; &#128522;</p>
    </div>
    """

    wrong1_html = """
    <div style="text-align: center; padding: 16px;">
      <div style="font-size: 36px;">&#128161;</div>
      <h3 style="color: #f39c12; margin: 8px 0;">Not quite!</h3>
      <p><strong>Hola</strong> means <strong style="color: #667eea;">Hello</strong>.</p>
      <p style="font-size: 13px; color: #666; margin-top: 8px;">
        <em>Adiós</em> = Goodbye, <em>Gracias</em> = Thank you
      </p>
    </div>
    """

    goodbye_html = f"""
    <div style="padding: 12px;">
      <h3 style="color: #2c3e50; margin-bottom: 12px; text-align: center;">
        &#128587; Saying Goodbye
      </h3>
      <div style="display: flex; flex-wrap: wrap; justify-content: center;">
        {greeting_card("Adiós", "Goodbye", "ah-DYOHS", "&#128075;")}
        {greeting_card("Hasta luego", "See you later", "AHS-tah LWEH-goh", "&#128587;")}
        {greeting_card("Buenas noches", "Good night", "BWEH-nahs NOH-ches", "&#127769;")}
      </div>
    </div>
    """

    correct2_html = """
    <div style="text-align: center; padding: 16px;">
      <div style="font-size: 48px;">&#127775;</div>
      <h3 style="color: #27ae60; margin: 8px 0;">¡Excelente!</h3>
      <p>
        <strong style="color: #764ba2;">Adiós</strong> means
        <span style="color: #764ba2; font-weight: bold;">Goodbye</span>!
      </p>
    </div>
    """

    wrong2_html = """
    <div style="text-align: center; padding: 16px;">
      <div style="font-size: 36px;">&#128173;</div>
      <h3 style="color: #f39c12; margin: 8px 0;">Almost!</h3>
      <p><strong>Adiós</strong> means <strong style="color: #764ba2;">Goodbye</strong>.</p>
      <p style="font-size: 13px; color: #666; margin-top: 8px;">
        <em>Hasta luego</em> = See you later
      </p>
    </div>
    """

    complete_html = """
    <div style="text-align: center; padding: 20px;">
      <div style="font-size: 56px;">&#128079; &#127881; &#128079;</div>
      <h2 style="color: #667eea; margin: 12px 0;">¡Felicidades!</h2>
      <p style="font-size: 16px;">
        You've learned <strong>6 Spanish greetings</strong>!
      </p>
      <div style="margin-top: 16px; padding: 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                  border-radius: 12px; color: white;">
        <p style="margin: 0; font-size: 14px;">
          <strong>Hola</strong> &#128075; <strong>Buenos días</strong> &#127774;
          <strong>Buenas tardes</strong> &#127773;<br/>
          <strong>Adiós</strong> &#128587; <strong>Hasta luego</strong>
          <strong>Buenas noches</strong> &#127769;
        </p>
      </div>
    </div>
    """

    nodes = [
        rich_msg_node(
            "greet_intro",
            intro_html,
            "Welcome to Spanish Greetings! Learn to say hello and goodbye in Spanish!",
            0,
            0,
        ),
        rich_msg_node(
            "greet_hello",
            hello_html,
            "Saying Hello: Hola (OH-lah) = Hello, Buenos días (BWEH-nohs DEE-ahs) = Good morning, Buenas tardes (BWEH-nahs TAR-des) = Good afternoon",
            300,
            0,
        ),
        question_node(
            "greet_quiz1",
            "What does 'Hola' mean?",
            "temp.greet_answer1",
            "choice",
            600,
            0,
            options=[
                {"label": "Hello", "value": "hello"},
                {"label": "Goodbye", "value": "goodbye"},
                {"label": "Thank you", "value": "thankyou"},
            ],
        ),
        condition_node(
            "greet_check1",
            conditions=[{"if": "temp['greet_answer1'] == 'hello'", "then": "$0"}],
            default_path="$1",
            x=900,
            y=0,
        ),
        rich_msg_node(
            "greet_correct1", correct1_html, "¡Muy bien! Hola means Hello!", 1200, -120
        ),
        rich_msg_node(
            "greet_wrong1", wrong1_html, "Not quite! Hola means Hello.", 1200, 120
        ),
        rich_msg_node(
            "greet_goodbye",
            goodbye_html,
            "Saying Goodbye: Adiós (ah-DYOHS) = Goodbye, Hasta luego (AHS-tah LWEH-goh) = See you later, Buenas noches (BWEH-nahs NOH-ches) = Good night",
            1500,
            0,
        ),
        question_node(
            "greet_quiz2",
            "What is the Spanish word for 'Goodbye'?",
            "temp.greet_answer2",
            "choice",
            1800,
            0,
            options=[
                {"label": "Hola", "value": "hola"},
                {"label": "Adiós", "value": "adios"},
                {"label": "Gracias", "value": "gracias"},
            ],
        ),
        condition_node(
            "greet_check2",
            conditions=[{"if": "temp['greet_answer2'] == 'adios'", "then": "$0"}],
            default_path="$1",
            x=2100,
            y=0,
        ),
        rich_msg_node(
            "greet_correct2",
            correct2_html,
            "¡Excelente! Adiós means Goodbye!",
            2400,
            -120,
        ),
        rich_msg_node(
            "greet_wrong2", wrong2_html, "Almost! Adiós means Goodbye.", 2400, 120
        ),
        action_node(
            "greet_mark_complete",
            [
                {
                    "type": "set_variable",
                    "variable": "temp.completed.greetings",
                    "value": True,
                }
            ],
            2700,
            0,
        ),
        rich_msg_node(
            "greet_wrap",
            complete_html,
            "¡Felicidades! You've learned 6 Spanish greetings!",
            3000,
            0,
        ),
    ]

    connections = [
        connection("greet_intro", "greet_hello"),
        connection("greet_hello", "greet_quiz1"),
        connection("greet_quiz1", "greet_check1"),
        connection("greet_check1", "greet_correct1", "$0"),
        connection("greet_check1", "greet_wrong1", "$1"),
        connection("greet_correct1", "greet_goodbye"),
        connection("greet_wrong1", "greet_goodbye"),
        connection("greet_goodbye", "greet_quiz2"),
        connection("greet_quiz2", "greet_check2"),
        connection("greet_check2", "greet_correct2", "$0"),
        connection("greet_check2", "greet_wrong2", "$1"),
        connection("greet_correct2", "greet_mark_complete"),
        connection("greet_wrong2", "greet_mark_complete"),
        connection("greet_mark_complete", "greet_wrap"),
    ]

    return {
        "name": "Spanish Greetings: Visual Learning",
        "description": "An enhanced, kid-friendly Spanish greetings lesson with rich visuals.",
        "version": "2.0.0",
        "entry_node_id": "greet_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "spanish_basics",
            "lesson": "greetings_rich",
            "audience": "age_8_plus",
            "embeddable": True,
            "return_state": ["temp.completed.greetings"],
        },
    }


if __name__ == "__main__":
    import json

    print(json.dumps(build_rich_greetings_flow(None), indent=2))
