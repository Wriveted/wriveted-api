#!/usr/bin/env python3
"""Create the Spanish Basics flows (hub + lesson subflows) via API.

Creates a multi-lesson, kid-friendly Spanish learning chatflow set:
- Main hub flow with composite nodes linking to each lesson
- Individual lesson flows (Greetings, Numbers, Colors, Animals)

Demonstrates cross-school flow composition - these flows can be embedded
as composite nodes in flows from other schools.

Usage:
  python scripts/create_spanish_basics_flow.py <jwt_token> [--school-id SCHOOL_ID] [--theme-id THEME_ID]
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


def build_greetings_flow(theme_id: Optional[str]) -> Dict[str, Any]:
    """Lesson 1: Basic Spanish greetings."""
    nodes = [
        msg_node(
            "greet_intro",
            "Welcome to Spanish Greetings! Let's learn how to say hello and goodbye.",
            0,
            0,
        ),
        msg_node(
            "greet_hola",
            "The most common greeting is 'Hola' (OH-lah). It means 'Hello'!",
            300,
            0,
        ),
        question_node(
            "greet_quiz1",
            "How do you say 'Hello' in Spanish?",
            "temp.greet_answer1",
            "choice",
            600,
            0,
            options=[
                {"label": "Hola", "value": "hola"},
                {"label": "Adios", "value": "adios"},
                {"label": "Gracias", "value": "gracias"},
            ],
        ),
        condition_node(
            "greet_check1",
            conditions=[
                {"if": {"var": "temp.greet_answer1", "eq": "hola"}, "then": "option_0"}
            ],
            default_path="option_1",
            x=900,
            y=0,
        ),
        msg_node(
            "greet_correct1",
            "Muy bien! (Very good!) Hola means Hello.",
            1200,
            -120,
        ),
        msg_node(
            "greet_wrong1",
            "Not quite. Hola means Hello. Adios means Goodbye!",
            1200,
            120,
        ),
        msg_node(
            "greet_adios",
            "Now let's learn 'Adios' (ah-dee-OHS). It means 'Goodbye'!",
            1500,
            0,
        ),
        msg_node(
            "greet_buenas",
            "'Buenos dias' (bway-nohs DEE-ahs) means 'Good morning'. 'Buenas noches' means 'Good night'.",
            1800,
            0,
        ),
        question_node(
            "greet_quiz2",
            "If you meet someone in the morning, what would you say?",
            "temp.greet_answer2",
            "choice",
            2100,
            0,
            options=[
                {"label": "Buenos dias", "value": "dias"},
                {"label": "Buenas noches", "value": "noches"},
                {"label": "Adios", "value": "adios"},
            ],
        ),
        condition_node(
            "greet_check2",
            conditions=[
                {"if": {"var": "temp.greet_answer2", "eq": "dias"}, "then": "option_0"}
            ],
            default_path="option_1",
            x=2400,
            y=0,
        ),
        msg_node(
            "greet_correct2",
            "Excelente! Buenos dias is perfect for the morning.",
            2700,
            -120,
        ),
        msg_node(
            "greet_wrong2",
            "Close! Buenos dias is for morning. Buenas noches is for night.",
            2700,
            120,
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
            3000,
            0,
        ),
        msg_node(
            "greet_wrap",
            "Greetings lesson complete! You now know: Hola, Adios, Buenos dias, Buenas noches.",
            3300,
            0,
        ),
    ]

    connections = [
        connection("greet_intro", "greet_hola"),
        connection("greet_hola", "greet_quiz1"),
        connection("greet_quiz1", "greet_check1"),
        connection("greet_check1", "greet_correct1", "$0"),
        connection("greet_check1", "greet_wrong1", "$1"),
        connection("greet_correct1", "greet_adios"),
        connection("greet_wrong1", "greet_adios"),
        connection("greet_adios", "greet_buenas"),
        connection("greet_buenas", "greet_quiz2"),
        connection("greet_quiz2", "greet_check2"),
        connection("greet_check2", "greet_correct2", "$0"),
        connection("greet_check2", "greet_wrong2", "$1"),
        connection("greet_correct2", "greet_mark_complete"),
        connection("greet_wrong2", "greet_mark_complete"),
        connection("greet_mark_complete", "greet_wrap"),
    ]

    return {
        "name": "Spanish Basics: Greetings",
        "description": "Learn basic Spanish greetings - Hello, Goodbye, and more.",
        "version": "1.0.0",
        "entry_node_id": "greet_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "spanish_basics",
            "lesson": "greetings",
            "audience": "age_8_plus",
            "embeddable": True,
            "return_state": ["temp.completed.greetings"],
        },
    }


def build_numbers_flow(theme_id: Optional[str]) -> Dict[str, Any]:
    """Lesson 2: Numbers 1-10 in Spanish."""
    nodes = [
        msg_node(
            "num_intro",
            "Welcome to Spanish Numbers! Let's count from 1 to 10.",
            0,
            0,
        ),
        msg_node(
            "num_1to5",
            "1=Uno, 2=Dos, 3=Tres, 4=Cuatro, 5=Cinco. Say them out loud: OO-no, DOHS, TREHS, KWAH-troh, SEEN-koh.",
            300,
            0,
        ),
        question_node(
            "num_quiz1",
            "What is 'three' in Spanish?",
            "temp.num_answer1",
            "choice",
            600,
            0,
            options=[
                {"label": "Tres", "value": "tres"},
                {"label": "Dos", "value": "dos"},
                {"label": "Cuatro", "value": "cuatro"},
            ],
        ),
        condition_node(
            "num_check1",
            conditions=[
                {"if": {"var": "temp.num_answer1", "eq": "tres"}, "then": "option_0"}
            ],
            default_path="option_1",
            x=900,
            y=0,
        ),
        msg_node(
            "num_correct1",
            "Correcto! Tres means three.",
            1200,
            -120,
        ),
        msg_node(
            "num_wrong1",
            "Not quite. Tres means three. Dos is two, Cuatro is four.",
            1200,
            120,
        ),
        msg_node(
            "num_6to10",
            "6=Seis, 7=Siete, 8=Ocho, 9=Nueve, 10=Diez. Say them: SAYS, see-EH-tay, OH-choh, NWAY-bay, dee-EHS.",
            1500,
            0,
        ),
        question_node(
            "num_quiz2",
            "What is 'eight' in Spanish?",
            "temp.num_answer2",
            "choice",
            1800,
            0,
            options=[
                {"label": "Seis", "value": "seis"},
                {"label": "Ocho", "value": "ocho"},
                {"label": "Nueve", "value": "nueve"},
            ],
        ),
        condition_node(
            "num_check2",
            conditions=[
                {"if": {"var": "temp.num_answer2", "eq": "ocho"}, "then": "option_0"}
            ],
            default_path="option_1",
            x=2100,
            y=0,
        ),
        msg_node(
            "num_correct2",
            "Muy bien! Ocho means eight.",
            2400,
            -120,
        ),
        msg_node(
            "num_wrong2",
            "Close! Ocho means eight. Seis is six, Nueve is nine.",
            2400,
            120,
        ),
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
        msg_node(
            "num_wrap",
            "Numbers lesson complete! You can now count 1-10 in Spanish!",
            3000,
            0,
        ),
    ]

    connections = [
        connection("num_intro", "num_1to5"),
        connection("num_1to5", "num_quiz1"),
        connection("num_quiz1", "num_check1"),
        connection("num_check1", "num_correct1", "$0"),
        connection("num_check1", "num_wrong1", "$1"),
        connection("num_correct1", "num_6to10"),
        connection("num_wrong1", "num_6to10"),
        connection("num_6to10", "num_quiz2"),
        connection("num_quiz2", "num_check2"),
        connection("num_check2", "num_correct2", "$0"),
        connection("num_check2", "num_wrong2", "$1"),
        connection("num_correct2", "num_mark_complete"),
        connection("num_wrong2", "num_mark_complete"),
        connection("num_mark_complete", "num_wrap"),
    ]

    return {
        "name": "Spanish Basics: Numbers 1-10",
        "description": "Learn to count from 1 to 10 in Spanish.",
        "version": "1.0.0",
        "entry_node_id": "num_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "spanish_basics",
            "lesson": "numbers",
            "audience": "age_8_plus",
            "embeddable": True,
            "return_state": ["temp.completed.numbers"],
        },
    }


def build_colors_flow(theme_id: Optional[str]) -> Dict[str, Any]:
    """Lesson 3: Colors in Spanish."""
    nodes = [
        msg_node(
            "color_intro",
            "Welcome to Spanish Colors! Let's learn some colores.",
            0,
            0,
        ),
        msg_node(
            "color_basic",
            "Rojo=Red, Azul=Blue, Verde=Green, Amarillo=Yellow. ROH-hoh, ah-SOOL, BEHR-day, ah-mah-REE-yoh.",
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
            conditions=[
                {"if": {"var": "temp.color_answer1", "eq": "green"}, "then": "option_0"}
            ],
            default_path="option_1",
            x=900,
            y=0,
        ),
        msg_node(
            "color_correct1",
            "Perfecto! Verde means green, like grass and trees.",
            1200,
            -120,
        ),
        msg_node(
            "color_wrong1",
            "Not quite. Verde means green. Rojo is red, Azul is blue.",
            1200,
            120,
        ),
        msg_node(
            "color_more",
            "More colors: Blanco=White, Negro=Black, Rosa=Pink, Naranja=Orange.",
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
            conditions=[
                {"if": {"var": "temp.color_answer2", "eq": "negro"}, "then": "option_0"}
            ],
            default_path="option_1",
            x=2100,
            y=0,
        ),
        msg_node(
            "color_correct2",
            "Excelente! Negro means black.",
            2400,
            -120,
        ),
        msg_node(
            "color_wrong2",
            "Close! Negro means black. Blanco is white, Rosa is pink.",
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
        msg_node(
            "color_wrap",
            "Colors lesson complete! You now know 8 Spanish colors!",
            3000,
            0,
        ),
    ]

    connections = [
        connection("color_intro", "color_basic"),
        connection("color_basic", "color_quiz1"),
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
        "name": "Spanish Basics: Colors",
        "description": "Learn colors in Spanish.",
        "version": "1.0.0",
        "entry_node_id": "color_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "spanish_basics",
            "lesson": "colors",
            "audience": "age_8_plus",
            "embeddable": True,
            "return_state": ["temp.completed.colors"],
        },
    }


def build_spanish_hub_flow(
    greetings_id: str,
    numbers_id: str,
    colors_id: str,
    theme_id: Optional[str],
) -> Dict[str, Any]:
    """Main Spanish hub that routes to lesson sub-flows."""
    nodes = [
        msg_node(
            "hub_intro",
            "Hola! Welcome to Spanish Basics. I'm here to help you learn some Spanish words.",
            0,
            0,
        ),
        question_node(
            "hub_name",
            "What's your name? (You can say it in English!)",
            "temp.student_name",
            "text",
            300,
            0,
        ),
        msg_node(
            "hub_welcome",
            "Nice to meet you, {{temp.student_name}}! Let's pick a lesson.",
            600,
            0,
        ),
        question_node(
            "hub_lesson_choice",
            "Which lesson would you like to start with?",
            "temp.lesson_choice",
            "choice",
            900,
            0,
            options=[
                {"label": "Greetings (Hola, Adios)", "value": "greetings"},
                {"label": "Numbers (Uno, Dos, Tres)", "value": "numbers"},
                {"label": "Colors (Rojo, Azul)", "value": "colors"},
            ],
        ),
        condition_node(
            "hub_route",
            conditions=[
                {
                    "if": {"var": "temp.lesson_choice", "eq": "greetings"},
                    "then": "option_0",
                },
                {
                    "if": {"var": "temp.lesson_choice", "eq": "numbers"},
                    "then": "option_1",
                },
            ],
            default_path="default",
            x=1200,
            y=0,
        ),
        composite_node(
            "hub_greetings",
            greetings_id,
            "Greetings Lesson",
            1500,
            -180,
        ),
        composite_node(
            "hub_numbers",
            numbers_id,
            "Numbers Lesson",
            1500,
            0,
        ),
        composite_node(
            "hub_colors",
            colors_id,
            "Colors Lesson",
            1500,
            180,
        ),
        msg_node(
            "hub_after_lesson",
            "Great job completing that lesson! Want to try another one?",
            1800,
            0,
        ),
        question_node(
            "hub_continue",
            "What would you like to do?",
            "temp.continue_choice",
            "choice",
            2100,
            0,
            options=[
                {"label": "Try another lesson", "value": "more"},
                {"label": "I'm done for now", "value": "done"},
            ],
        ),
        condition_node(
            "hub_continue_route",
            conditions=[
                {
                    "if": {"var": "temp.continue_choice", "eq": "more"},
                    "then": "option_0",
                }
            ],
            default_path="option_1",
            x=2400,
            y=0,
        ),
        msg_node(
            "hub_final",
            "Adios, {{temp.student_name}}! Keep practicing your Spanish. See you next time!",
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
        "name": "Spanish Basics: Learning Hub",
        "description": "A kid-friendly Spanish learning hub with multiple lessons.",
        "version": "1.0.0",
        "entry_node_id": "hub_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "spanish_basics",
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


def create_flow(
    token: str,
    flow_data: Dict[str, Any],
    api_base: str,
    school_id: Optional[str] = None,
    visibility: str = "public",
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Add school ownership and visibility
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
    parser = argparse.ArgumentParser(description="Create Spanish Basics flows via API.")
    parser.add_argument("token", help="JWT token for CMS API")
    parser.add_argument(
        "--school-id", dest="school_id", help="School ID to own these flows"
    )
    parser.add_argument(
        "--visibility",
        default="public",
        choices=["private", "school", "public", "wriveted"],
        help="Visibility level for the flows (default: public)",
    )
    parser.add_argument(
        "--theme-id", dest="theme_id", help="Optional theme ID to attach"
    )
    parser.add_argument(
        "--api-base", dest="api_base", default=API_BASE, help="API base URL"
    )
    args = parser.parse_args()

    # Create lesson sub-flows first
    greetings_flow = create_flow(
        args.token,
        build_greetings_flow(args.theme_id),
        args.api_base,
        args.school_id,
        args.visibility,
    )
    numbers_flow = create_flow(
        args.token,
        build_numbers_flow(args.theme_id),
        args.api_base,
        args.school_id,
        args.visibility,
    )
    colors_flow = create_flow(
        args.token,
        build_colors_flow(args.theme_id),
        args.api_base,
        args.school_id,
        args.visibility,
    )

    # Create hub flow that links to lessons
    hub_flow = create_flow(
        args.token,
        build_spanish_hub_flow(
            greetings_id=greetings_flow["id"],
            numbers_id=numbers_flow["id"],
            colors_id=colors_flow["id"],
            theme_id=args.theme_id,
        ),
        args.api_base,
        args.school_id,
        args.visibility,
    )

    print("Created Spanish Basics flows:")
    for flow in [hub_flow, greetings_flow, numbers_flow, colors_flow]:
        print(f"- {flow['name']} (ID: {flow['id']})")
        print(f"  Visibility: {args.visibility}, School: {args.school_id or 'None'}")

    print("\nTo embed these flows as composite nodes in other flows, use:")
    print(f"  Hub Flow ID: {hub_flow['id']}")
    print(f"  Greetings: {greetings_flow['id']}")
    print(f"  Numbers: {numbers_flow['id']}")
    print(f"  Colors: {colors_flow['id']}")


if __name__ == "__main__":
    main()
